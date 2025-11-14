# Copyright 2025 Google LLC. The ces-genesys-adapter is made available as "Software"
# under the agreement governing your use of Google Cloud Platform, including the
# Service Specific Terms available at https://cloud.google.com/terms/service-terms.

import asyncio
import logging
import http
import sys
import websockets
from genesys_ws import GenesysWS
import config
from auth import auth_provider

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def process_request(connection, request):
    """
    This function is called before the WebSocket connection is established.
    It handles /health checks and authenticates WebSocket upgrade requests
    using the modern `websockets` API.
    """
    # Handle /health check endpoint
    if request.path == "/health":
        return connection.respond(http.HTTPStatus.OK, "OK\n")

    # For all other paths, proceed with WebSocket authentication.
    if not auth_provider.verify_request(request):
        logger.info(f"Request came in with path: {request.path}")
        logger.warning(f"WebSocket connection rejected: invalid API key or signature.")
        return connection.respond(http.HTTPStatus.UNAUTHORIZED, "Unauthorized\n")

    # If authentication is successful, return None to proceed with the handshake.
    logger.info("WebSocket connection authenticated successfully.")
    return None


async def handler(websocket):
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
    if not config.GENESYS_API_KEY:
        logger.error("GENESYS_API_KEY environment variable not set.")
        sys.exit(1)

    if config.AUTH_TOKEN_SECRET_PATH:
        logger.info(f"Authenticating to CES using token-based auth from secret: {config.AUTH_TOKEN_SECRET_PATH}")
    else:
        logger.info("Authenticating to CES using Application Default Credentials (ADC).")

    if config.GENESYS_CLIENT_SECRET:
        logger.info(f"Genesys signature verification is enabled.")

    logger.info(f"Starting WebSocket server on port {config.PORT}")
    
    # For older versions of `websockets`, we must catch the exception
    # raised by plain HTTP requests (like health checks) to prevent crashes.
    async with websockets.serve(
        handler,
        "0.0.0.0",
        config.PORT,
        process_request=process_request
    ) as server:
        await server.serve_forever()
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped manually.")