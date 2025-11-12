# Copyright 2025 Google LLC. The ces-genesys-adapter is made available as "Software"
# under the agreement governing your use of Google Cloud Platform, including the
# Service Specific Terms available at https://cloud.google.com/terms/service-terms.

import asyncio
import json
import logging
from polysynth_ws import PolysynthWS

logger = logging.getLogger(__name__)

class GenesysWS:
    def __init__(self, websocket):
        self.websocket = websocket
        self.polysynth_ws = None
        self.last_server_sequence_number = 0
        self.last_client_sequence_number = 0
        self.client_session_id = None
        self.conversation_id = None
        self.input_variables = None

    async def handle_connection(self):
        self.polysynth_ws = PolysynthWS(self)
        await self.polysynth_ws.connect()

        asyncio.create_task(self.polysynth_ws.listen())
        asyncio.create_task(self.polysynth_ws.pacer())

        async for message in self.websocket:
            if isinstance(message, str):
                await self.handle_text_message(message)
            elif isinstance(message, bytes):
                await self.handle_binary_message(message)

    async def handle_text_message(self, message):
        logger.info(f"Received text message from Genesys: {message}")
        try:
            data = json.loads(message)
            self.last_client_sequence_number = data.get("seq")
            self.client_session_id = data.get("id")
            message_type = data.get("type")

            if message_type == "open":
                parameters = data.get("parameters", {})
                self.conversation_id = parameters.get("conversationId")
                self.input_variables = parameters.get("inputVariables")
                logger.info(f"Genesys session opened for conversation ID: {self.conversation_id}")

                offered_media = parameters.get("media", [])
                selected_media = None
                for media_option in offered_media:
                    if (media_option.get("type") == "audio" and 
                        media_option.get("format") == "PCMU" and 
                        media_option.get("rate") == 8000):
                        selected_media = media_option
                        break

                if not selected_media:
                    await self.send_disconnect("error", "No compatible audio media offered.")
                    return

                opened_message = {
                    "type": "opened",
                    "version": "2",
                    "id": self.client_session_id,
                    "seq": self.get_next_server_sequence_number(),
                    "clientseq": self.last_client_sequence_number,
                    "parameters": {"startPaused": False, "media": [selected_media]}
                }
                await self.send_message(opened_message)

            elif message_type == "ping":
                pong_message = {
                    "type": "pong",
                    "version": "2",
                    "id": self.client_session_id,
                    "seq": self.get_next_server_sequence_number(),
                    "clientseq": self.last_client_sequence_number
                }
                await self.send_message(pong_message)

            elif message_type == "close":
                closed_message = {
                    "type": "closed",
                    "id": self.client_session_id,
                    "seq": self.get_next_server_sequence_number(),
                    "clientseq": self.last_client_sequence_number
                }
                await self.send_message(closed_message)
                await self.websocket.close()

            elif message_type == "update":
                logger.info(f"Received update message from Genesys: {data}")
                pass

        except json.JSONDecodeError:
            logger.error(f"Error decoding JSON from Genesys: {message}")
            await self.send_disconnect("error", "Invalid JSON received")

    async def send_disconnect(self, reason, info):
        disconnect_message = {
            "type": "disconnect",
            "id": self.client_session_id,
            "seq": self.get_next_server_sequence_number(),
            "clientseq": self.last_client_sequence_number,
            "parameters": {"reason": reason, "info": info}
        }
        await self.send_message(disconnect_message)
        await self.websocket.close()

    def get_next_server_sequence_number(self):
        self.last_server_sequence_number += 1
        return self.last_server_sequence_number

    async def handle_binary_message(self, message):
        if self.polysynth_ws:
            await self.polysynth_ws.send_audio(message)

    async def send_message(self, message):
        await self.websocket.send(json.dumps(message))
