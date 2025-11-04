import asyncio
import audioop
import base64
import json
import logging
import uuid
import websockets
import google.auth
from google.auth.transport import requests as google_auth_requests
import config

logger = logging.getLogger(__name__)

class PolysynthWS:
    def __init__(self, genesys_ws):
        self.genesys_ws = genesys_ws
        self.websocket = None
        self.session_id = None
        self.ratecv_state_to_va = None

    def is_connected(self):
        return self.websocket and self.websocket.open

    async def connect(self):
        """
        Connects to the Polysynth bidiRunSession WebSocket endpoint.
        """
        self.session_id = f"{config.AGENT_ID}/sessions/{uuid.uuid4()}"
        
        # Get Google Cloud credentials
        creds, project_id = google.auth.default()
        auth_req = google_auth_requests.Request()
        creds.refresh(auth_req)
        token = creds.token

        # Construct the WebSocket URL
        # Note: This is a simplified URL. You may need to adjust it based on your environment.
        ws_url = f"wss://ces.googleapis.com/ws/google.cloud.ces.v1.SessionService/BidiRunSession/locations/global"

        # Connect to the WebSocket endpoint
        logger.info(f"Connecting to Polysynth at {ws_url}")
        self.websocket = await websockets.connect(
            ws_url,
            extra_headers={
                "Authorization": f"Bearer {token}",
                "X-Goog-User-Project": project_id,
            }
        )
        logger.info("Connected to Polysynth")

        # Send the initial configuration message
        await self.send_config_message()

    async def send_config_message(self):
        """
        Sends the initial configuration message to Polysynth.
        """
        config_message = {
            "config": {
                "session": self.session_id,
                "inputAudioConfig": {
                    "audioEncoding": "LINEAR16",
                    "sampleRateHertz": 8000, # Genesys uses 8000Hz
                },
                "outputAudioConfig": {
                    "audioEncoding": "LINEAR16",
                    "sampleRateHertz": 8000,
                },
            }
        }
        await self.websocket.send(json.dumps(config_message))
        logger.info(f"Sent config message to Polysynth: {config_message}")

    async def send_audio(self, audio_chunk):
        """
        Sends audio data to Polysynth.
        """
        # Convert audio from µ-law to linear16
        linear_audio = audioop.ulaw2lin(audio_chunk, 2)
        
        # Polysynth might expect a different sample rate, so we might need to resample
        # For now, we assume the sample rate is the same (8000Hz)

        base64_pcm_payload = base64.b64encode(linear_audio).decode("utf-8")
        va_input = {"realtimeInput": {"audio": base64_pcm_payload}}
        await self.websocket.send(json.dumps(va_input))

    async def receive(self):
        """
        Receives messages from Polysynth.
        """
        message = await self.websocket.recv()
        data = json.loads(message)

        if "sessionOutput" in data:
                    if "audio" in data["sessionOutput"]:
                        va_audio = base64.b64decode(data["sessionOutput"]["audio"])
                        # Convert audio from linear16 to µ-law
                        mulaw_audio = audioop.lin2ulaw(va_audio, 2)
                        return mulaw_audio
                    elif "text" in data["sessionOutput"]:
                        # TODO: Handle text messages from Polysynth
                        logger.info(f"Received text from Polysynth: {data['sessionOutput']['text']}")        
        return None
