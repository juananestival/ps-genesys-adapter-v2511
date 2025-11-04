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

    async def handle_connection(self):
        """
        Handles the WebSocket connection from Genesys.
        """
        # Create a Polysynth WebSocket connection
        self.polysynth_ws = PolysynthWS(self)
        await self.polysynth_ws.connect()

        # Forward messages from Polysynth to Genesys
        asyncio.create_task(self.forward_from_polysynth())

        # Handle incoming messages from Genesys
        async for message in self.websocket:
            if isinstance(message, str):
                await self.handle_text_message(message)
            elif isinstance(message, bytes):
                await self.handle_binary_message(message)

        async def handle_text_message(self, message):

            """

            Handles incoming text messages from Genesys.

            """

            logger.info(f"Received text message from Genesys: {message}")

            try:

                data = json.loads(message)

                self.last_client_sequence_number = data.get("seq")

                self.client_session_id = data.get("id")

                message_type = data.get("type")

    

                if message_type == "open":

                    # Handle the open message

                    parameters = data.get("parameters", {})

                    self.conversation_id = parameters.get("conversationId")

                    self.input_variables = parameters.get("inputVariables")

                    logger.info(f"Genesys session opened for conversation ID: {self.conversation_id}")

                                            # Send the opened message
                                            opened_message = {
                                                "type": "opened",
                                                "version": "2",
                                                "id": self.client_session_id,
                                                "seq": self.get_next_server_sequence_number(),
                                                "clientseq": self.last_client_sequence_number,
                                                "parameters": {
                                                    "startPaused": False,
                                                    "media": [
                                                        {
                                                            "type": "audio",
                                                            "format": "PCMU",
                                                            "channels": ["external", "internal"],
                                                            "rate": 8000
                                                        }
                                                    ]
                                                }
                                            }
                                            await self.send_message(opened_message)    

                    # Send the protocol message

                    protocol_message = {

                        "type": "protocol",

                        "version": "2",

                        "id": self.client_session_id,

                        "seq": self.get_next_server_sequence_number(),

                        "clientseq": self.last_client_sequence_number,

                        "parameters": {

                            "protocols": ["audio", "text"],

                            "media": {

                                "audio": {

                                    "codecs": ["g711ulaw"]

                                }

                            }

                        }

                    }

                    await self.send_message(protocol_message)

    

                            elif message_type == "ping":

    

                                # Respond with a pong message to keep the connection alive

    

                                pong_message = {

    

                                    "type": "pong",

    

                                    "id": self.client_session_id,

    

                                    "seq": self.get_next_server_sequence_number(),

    

                                    "clientseq": self.last_client_sequence_number

    

                                }

    

                                await self.send_message(pong_message)

                            elif message_type == "close":

                                # Acknowledge the close message and close the connection

                                closed_message = {

                                    "type": "closed",

                                    "id": self.client_session_id,

                                    "seq": self.get_next_server_sequence_number(),

                                    "clientseq": self.last_client_sequence_number

                                }

                                await self.send_message(closed_message)

                                await self.websocket.close()
                            elif message_type == "update":
                                # The client can send update messages, but we don't need to do anything with them
                                logger.info(f"Received update message from Genesys: {data}")
                                pass

    

                    except json.JSONDecodeError:

    

                        logger.error(f"Error decoding JSON from Genesys: {message}")

    

                        await self.send_disconnect("error", "Invalid JSON received")

    

            

    

                async def send_disconnect(self, reason, info):

    

                    """

    

                    Sends a disconnect message to Genesys.

    

                    """

    

                    disconnect_message = {

    

                        "type": "disconnect",

    

                        "id": self.client_session_id,

    

                        "seq": self.get_next_server_sequence_number(),

    

                        "clientseq": self.last_client_sequence_number,

    

                        "parameters": {

    

                            "reason": reason,

    

                            "info": info

    

                        }

    

                    }

    

                    await self.send_message(disconnect_message)

    

                    await self.websocket.close()

    

        def get_next_server_sequence_number(self):

            self.last_server_sequence_number += 1

            return self.last_server_sequence_number

    async def handle_binary_message(self, message):
        """
        Handles incoming binary messages (audio) from Genesys.
        """
        logger.info(f"Received binary message from Genesys of size {len(message)}")
        # Forward the audio to Polysynth
        if self.polysynth_ws:
            await self.polysynth_ws.send_audio(message)

    async def forward_from_polysynth(self):
        """
        Forwards messages from Polysynth to Genesys.
        """
        # This is a simplified example. In a real implementation, you would
        # need to handle different message types from Polysynth and format
        # them for Genesys.
        while True:
            if self.polysynth_ws and self.polysynth_ws.is_connected():
                message = await self.polysynth_ws.receive()
                if message:
                    # Assuming the message from Polysynth is audio data
                    await self.websocket.send(message)
            else:
                # Wait for the connection to be established
                await asyncio.sleep(0.1)

    async def send_message(self, message):
        """
        Sends a message to Genesys.
        """
        await self.websocket.send(json.dumps(message))
