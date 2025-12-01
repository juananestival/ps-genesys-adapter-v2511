# Copyright 2025 Google LLC

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     https://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import asyncio
import audioop
import base64
import json
import logging
import uuid

import google.auth
import websockets
from websockets.connection import State

from .auth import auth_provider
from .redaction import redact

logger = logging.getLogger(__name__)

_BASE_WS_URL = (
    "wss://ces.googleapis.com/ws/google.cloud.ces.v1.SessionService/"
    "BidiRunSession/locations/"
)


class CESWS:
    def __init__(self, genesys_ws):
        self.genesys_ws = genesys_ws
        self.websocket = None
        self.session_id = None
        self.deployment_id = None
        self.ratecv_state_to_va = None
        self.ratecv_state_to_genesys = None
        self.audio_out_queue = asyncio.Queue()

    def is_connected(self):
        return self.websocket and self.websocket.state == State.OPEN

    async def connect(self, agent_id, deployment_id=None):
        self.session_id = f"{agent_id}/sessions/{uuid.uuid4()}"
        self.deployment_id = deployment_id

        _, project_id = google.auth.default()

        try:
            parts = agent_id.split("/")
            location_index = parts.index("locations")
            location = parts[location_index + 1]
        except (ValueError, IndexError):
            logger.error(f"Could not extract location from agent_id: {agent_id}")
            return

        token = await auth_provider.get_token()

        ws_url = f"{_BASE_WS_URL}{location}"

        logger.info(f"Connecting to CES at {ws_url}")
        self.websocket = await websockets.connect(
            ws_url,
            additional_headers={
                "Authorization": f"Bearer {token}",
                "X-Goog-User-Project": project_id,
            },
        )
        logger.info("Connected to CES")
        await self.send_config_message()

    async def send_config_message(self):
        config_message = {
            "config": {
                "session": self.session_id,
                "inputAudioConfig": {
                    "audioEncoding": "LINEAR16",
                    "sampleRateHertz": 16000,
                },
                "outputAudioConfig": {
                    "audioEncoding": "LINEAR16",
                    "sampleRateHertz": 16000,
                },
            }
        }
        if self.deployment_id:
            config_message["config"]["deployment"] = self.deployment_id
        await self.websocket.send(json.dumps(config_message))
        logger.info(f"Sent config message to CES: {config_message}")

        kickstart_message = {"realtimeInput": {"text": "Hello"}}
        await self.websocket.send(json.dumps(kickstart_message))
        logger.info(f"Sent kickstart message to CES: {kickstart_message}")

        if self.genesys_ws.ces_input_variables:
            variables_message = {
                "realtimeInput": {"variables": self.genesys_ws.ces_input_variables}
            }
            await self.websocket.send(json.dumps(variables_message))
            redacted_variables_message = redact(variables_message)
            logger.info(f"Sent variables to CES: {redacted_variables_message}")

    async def send_audio(self, audio_chunk):
        linear_audio_8k = audioop.ulaw2lin(audio_chunk, 2)
        linear_audio_16k, self.ratecv_state_to_va = audioop.ratecv(
            linear_audio_8k, 2, 1, 8000, 16000, self.ratecv_state_to_va
        )
        base64_pcm_payload = base64.b64encode(linear_audio_16k).decode("utf-8")
        va_input = {"realtimeInput": {"audio": base64_pcm_payload}}
        if self.is_connected():
            await self.websocket.send(json.dumps(va_input))

    async def listen(self):
        try:
   
            while self.is_connected():
                message = await self.websocket.recv()
                data = json.loads(message)

                if "sessionOutput" in data and "audio" in data["sessionOutput"]:
                    linear_audio_16k = base64.b64decode(data["sessionOutput"]["audio"])
                    linear_audio_8k, self.ratecv_state_to_genesys = audioop.ratecv(
                        linear_audio_16k,
                        2,
                        1,
                        16000,
                        8000,
                        self.ratecv_state_to_genesys,
                    )
                    mulaw_audio = audioop.lin2ulaw(linear_audio_8k, 2)
                    await self.audio_out_queue.put(mulaw_audio)

                elif "sessionOutput" in data and "text" in data["sessionOutput"]:
                    text = data['sessionOutput']['text']
                    redacted_text = redact(text)
                    logger.info(
                        f"Received text from CES: {redacted_text}"
                    )
                    if "end_session" in text.lower():
                        logger.error(f"End Session as text in sessionOutput. Received text from CES text: {text}It shouldn't be here as this is text to be reat to the customer. Calling disconnect in Genesys with error returned")
                        await self.genesys_ws.send_disconnect("completed", info="no_params_error_1")

                elif "sessionOutput" in data and "diagnosticInfo" in data["sessionOutput"]:
                    if "messages" in data["sessionOutput"]["diagnosticInfo"]:
                        for message in data["sessionOutput"]["diagnosticInfo"]["messages"]:
                            if "end_session" in message["chunks"][0]:
                                logger.error(f"End Session in turn complete. It shouldn't be here  Received text from CES text: {text}It shouldn't be here as this is text to be reat to the customer. Calling disconnect in Genesys with error returned")
                                await self.genesys_ws.send_disconnect("completed", info="no_params_error_2")                  
            
                elif "recognitionResult" in data:
                    pass
                # Implement your own logic here
                elif "endSession" in data:
                    logger.info(f"Received endSession from CES: {data}")
                    if "params" in data['endSession']['metadata'] and "conversation_summary" in data['endSession']['metadata']['params']:
                        params = data['endSession']['metadata']['params']['conversation_summary']
                    else:
                        params = None
                        
                    await self.genesys_ws.send_disconnect("completed", info=params)
                else: 
                    logger.warning(f"Received unknown message from CES: {data}")

                # end custom logic

        except Exception as e:
            logger.error(f"Error in CES listener: {e}")

    async def pacer(self):
        logger.info("Starting audio pacer for Genesys")
        try:
            while True:
                audio_chunk = await self.audio_out_queue.get()
                await self.genesys_ws.websocket.send(audio_chunk)
                self.audio_out_queue.task_done()
                # Dynamically sleep based on the size of the audio chunk to ensure
                # real-time pacing. The audio is 8000Hz PCMU, which is 1 byte per
                # sample.
                duration_in_seconds = len(audio_chunk) / 8000.0
                await asyncio.sleep(duration_in_seconds)
        except websockets.exceptions.ConnectionClosed:
            logger.info("Genesys websocket connection closed, pacer stopped.")
        except Exception as e:
            logger.error(f"Unexpected error in pacer: {e}", exc_info=True)
        logger.info("Audio pacer for Genesys stopped")
