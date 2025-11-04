import os
from dotenv import load_dotenv

load_dotenv()

PORT = os.getenv("PORT", 8080)
AGENT_ID = os.getenv("AGENT_ID")
