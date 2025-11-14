# Copyright 2025 Google LLC. The ces-genesys-adapter is made available as "Software"
# under the agreement governing your use of Google Cloud Platform, including the
# Service Specific Terms available at https://cloud.google.com/terms/service-terms.

import os
from dotenv import load_dotenv

load_dotenv()

PORT = os.getenv("PORT", 8080)
GENESYS_API_KEY = os.getenv("GENESYS_API_KEY")
AUTH_TOKEN_SECRET_PATH = os.getenv("AUTH_TOKEN_SECRET_PATH")
GENESYS_CLIENT_SECRET = os.getenv("GENESYS_CLIENT_SECRET")
