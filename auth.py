# Copyright 2025 Google LLC. The ces-genesys-adapter is made available as "Software"
# under the agreement governing your use of Google Cloud Platform, including the
# Service Specific Terms available at https://cloud.google.com/terms/service-terms.

import asyncio
import json
import logging
import time
from google.cloud import secretmanager
import google.auth
from google.auth.transport import requests as google_auth_requests
import config

logger = logging.getLogger(__name__)


class Auth:
    def __init__(self):
        self._token_info = {}
        self._lock = asyncio.Lock()
        self._sm_client = None

    async def get_token(self):
        async with self._lock:
            if config.AUTH_TOKEN_SECRET_PATH:
                # Token-based auth
                now_ms = int(time.time() * 1000)
                if not self._token_info or self._token_info.get("expiry", 0) <= now_ms:
                    logger.info("Auth token is missing or expired, fetching new token.")
                    await self._fetch_token_from_secret_manager()
                return self._token_info["access_token"]
            else:
                # ADC-based auth
                creds, _ = google.auth.default()
                auth_req = google_auth_requests.Request()
                creds.refresh(auth_req)
                return creds.token

    async def _fetch_token_from_secret_manager(self):
        if not self._sm_client:
            self._sm_client = secretmanager.SecretManagerServiceClient()

        secret_path = config.AUTH_TOKEN_SECRET_PATH
        if "/versions/" not in secret_path:
            secret_path = f"{secret_path}/versions/latest"

        try:
            logger.info(f"Fetching auth token from secret manager: {secret_path}")
            response = self._sm_client.access_secret_version(name=secret_path)
            payload = response.payload.data.decode("UTF-8")
            token_data = json.loads(payload)

            if "access_token" not in token_data or "expiry" not in token_data:
                raise ValueError("Secret payload is missing 'access_token' or 'expiry'")

            self._token_info = {
                "access_token": token_data["access_token"],
                "expiry": token_data["expiry"]
            }
            logger.info("Successfully loaded auth token from Secret Manager.")
        except Exception as e:
            logger.error(f"Failed to load auth token from Secret Manager: {e}", exc_info=True)
            # If we fail, clear the token info to force a retry on the next call.
            self._token_info = {}
            raise

auth_provider = Auth()