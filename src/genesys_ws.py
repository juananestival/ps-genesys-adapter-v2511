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
import json
import logging

from .ces_ws import CESWS
from .redaction import redact

logger = logging.getLogger(__name__)


class GenesysWS:
    def __init__(self, websocket):
        self.websocket = websocket
        self.ces_ws = None
        self.last_server_sequence_number = 0
        self.last_client_sequence_number = 0
        self.client_session_id = None
        self.conversation_id = None
        self.input_variables = None

    async def handle_connection(self):
        self.ces_ws = CESWS(self)

        async for message in self.websocket:
            if isinstance(message, str):
                await self.handle_text_message(message)
            elif isinstance(message, bytes):
                await self.handle_binary_message(message)

    async def handle_text_message(self, message):
        redacted_message = redact(message)
        logger.info(f"Received text message from Genesys: {redacted_message}")
        try:
            data = json.loads(message)
            self.last_client_sequence_number = data.get("seq")
            self.client_session_id = data.get("id")
            message_type = data.get("type")

            if message_type == "open":
                parameters = data.get("parameters", {})
                self.conversation_id = parameters.get("conversationId")
                self.input_variables = parameters.get("inputVariables")

                self.deployment_id = None
                self.agent_id = None

                if self.input_variables:
                    if "_deployment_id" in self.input_variables:
                        self.deployment_id = self.input_variables["_deployment_id"]
                        # Extract agent_id from deployment_id
                        # deployment_id format:
                        # projects/{project}/locations/{location}/apps/{app_id}/deployments/{deployment_id}
                        # agent_id format:
                        # projects/{project}/locations/{location}/apps/{app_id}
                        parts = self.deployment_id.split("/")
                        if len(parts) == 8 and parts[6] == "deployments":
                            self.agent_id = "/".join(parts[:6])
                        else:
                            logger.error(
                                f"Invalid _deployment_id format: {self.deployment_id}"
                            )
                            await self.send_disconnect(
                                "error", "Invalid _deployment_id format"
                            )
                            return
                    elif "_agent_id" in self.input_variables:
                        self.agent_id = self.input_variables["_agent_id"]

                    self.ces_input_variables = {
                        k: v
                        for k, v in self.input_variables.items()
                        if not k.startswith("_")
                    }

                if not self.agent_id:
                    logger.error(
                        "'_agent_id' or '_deployment_id'"
                        "not found in inputVariables from Genesys."
                    )
                    await self.send_disconnect(
                        "error",
                        "Missing required parameter: _agent_id or _deployment_id",
                    )
                    return

                await self.ces_ws.connect(self.agent_id, self.deployment_id)
                asyncio.create_task(self.ces_ws.listen())
                asyncio.create_task(self.ces_ws.pacer())

                logger.info(
                    "Genesys session opened for conversation ID: "
                    f"{self.conversation_id}"
                )

                custom_config_str = parameters.get("customConfig")
                if custom_config_str:
                    logger.info("Found customConfig from Genesys:")
                    try:
                        custom_config = json.loads(custom_config_str)
                        if isinstance(custom_config, dict):
                            for key, value in custom_config.items():
                                logger.info(f"  - {key}: {value}")
                        else:
                            logger.warning("CUSTOMCONFIG IS NOT A KEY-VALUE PAIR:")
                            logger.warning(f"  {custom_config}")
                    except json.JSONDecodeError:
                        logger.error(
                            f"Error decoding customConfig JSON: {custom_config_str}"
                        )

                offered_media = parameters.get("media", [])
                selected_media = None
                for media_option in offered_media:
                    if (
                        media_option.get("type") == "audio"
                        and media_option.get("format") == "PCMU"
                        and media_option.get("rate") == 8000
                    ):
                        selected_media = media_option
                        break

                if not selected_media:
                    await self.send_disconnect(
                        "error", "No compatible audio media offered."
                    )
                    return

                opened_message = {
                    "type": "opened",
                    "version": "2",
                    "id": self.client_session_id,
                    "seq": self.get_next_server_sequence_number(),
                    "clientseq": self.last_client_sequence_number,
                    "parameters": {"startPaused": False, "media": [selected_media]},
                }
                await self.send_message(opened_message)

            elif message_type == "ping":
                logger.warning("PONG")
                pong_message = {
                    "type": "pong",
                    "version": "2",
                    "id": self.client_session_id,
                    "seq": self.get_next_server_sequence_number(),
                    "clientseq": self.last_client_sequence_number,
                    "parameters": {}
                }
                await self.send_message(pong_message)

            elif message_type == "close":
                
                params = {
                    "Escalation_Reason":"UNMAPPED_UNSUPPORTED_INTENT",
                    "VBg_msg_KO":"",
                    "VBg_input_text":"Problemas con roaming en Francia",
                    "VBg_MSISDN":"622222222",
                    "VBg_PaA_summary_text":"Usuario reporta problemas con datos en roaming estando en Francia.",
                    "VBg_DocumentId":"87654321B",
                    "VBg_msg_OK":"Le paso con un agente para revisar su caso de roaming.",
                    "VBg_end_msg":"Gracias por llamar a MasMovil. Test dos completado.",
                    "VBg_SessionId":"MM_TEST_SESS_002",
                    "VBg_CustomerId":"CUST002",
                    "Data":"{\"test_scenario\": 2, \"status\": \"escalate\", \"country\": \"Francia\"}",
                }
                #params = '{"VBg_msg_KO":"el cliente cuelga"}'
                
               
                #await asyncio.sleep(3) 
                
                closed_message = {
                    "version": "2",
                    "type": "closed",
                    "id": self.client_session_id,
                    "seq": self.get_next_server_sequence_number(),
                    "clientseq": self.last_client_sequence_number
                }
                
                await self.send_message(closed_message)
                await self.send_disconnect("completed", params=params)
                # Wait for 5 seconds without blocking other connections. This avoid a racing condition that prevent genesys to receive the disconnect with params. 
                # await asyncio.sleep(1) 
                #await self.websocket.close()

            elif message_type == "update":
                logger.info(f"Received update message from Genesys: {data}")
                pass

        except json.JSONDecodeError:
            logger.error(f"Error decoding JSON from Genesys: {message}")
            await self.send_disconnect("error", "Invalid JSON received")

    async def send_disconnect(self, reason, params):
        logger.warning(f"Sending params message to Genesys: {params} type {type(params)}")
        output_variables = {}
        for key, value in params.items():
            logger.warning(f"  - {key}: {value}")
            output_variables[key] = value   
        
        logger.warning(f"Sending params 3 message to Genesys: {output_variables} type {type(output_variables)}")
        disconnect_message = {
            "version": "2",
            "type": "disconnect",
            "id": self.client_session_id,
            "seq": self.get_next_server_sequence_number(),
            "clientseq": self.last_client_sequence_number,
            "parameters": {
                "reason": reason,
                "outputVariables": {
                    "key1": params
                }
            }
        }
        disconnect_message['parameters']['outputVariables'] = output_variables
        logger.info(f"Sending disconnect message to Genesys: {disconnect_message}")
        await self.send_message(disconnect_message)
        #await self.websocket.close()

    def get_next_server_sequence_number(self):
        self.last_server_sequence_number += 1
        return self.last_server_sequence_number

    async def handle_binary_message(self, message):
        if self.ces_ws:
            await self.ces_ws.send_audio(message)

    async def send_message(self, message):
        await self.websocket.send(json.dumps(message))
