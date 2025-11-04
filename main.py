import asyncio
import logging
import websockets
from genesys_ws import GenesysWS
import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def handler(websocket, path):
    """
    This function is called for each incoming WebSocket connection.
    """
    logger.info(f"New connection from {websocket.remote_address}")
    genesys_ws = GenesysWS(websocket)
    await genesys_ws.handle_connection()

async def main():
    """
    This is the main entry point of the application.
    """
    logger.info(f"Starting WebSocket server on port {config.PORT}")
    async with websockets.serve(handler, "0.0.0.0", config.PORT):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
