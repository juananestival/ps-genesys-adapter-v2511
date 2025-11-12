#!/bin/bash

# Copyright 2025 Google LLC. The ces-genesys-adapter is made available as "Software"
# under the agreement governing your use of Google Cloud Platform, including the
# Service Specific Terms available at https://cloud.google.com/terms/service-terms.

source $(dirname "$0")/values.sh

gcloud run deploy $SERVICE_NAME \
    --source="." \
    --platform=managed \
    --region=$LOCATION \
    --cpu=1 \
    --memory=1Gi \
    --min-instances=1 \
    --max-instances=10 \
    --service-account=$SERVICE_ACCOUNT \
    --allow-unauthenticated \
    --project=$PROJECT_ID  \
    --timeout=$TIMEOUT \
    --concurrency=$CONCURRENCY \
    --set-env-vars=AGENT_ID="$AGENT_ID",AUTH_TOKEN_SECRET_PATH="$AUTH_TOKEN_SECRET_PATH",NUMBERS_COLLECTION_ID="$NUMBERS_COLLECTION_ID" \
    --set-secrets=API_KEY="$API_KEY_SECRET_PATH" \
    --allow-unauthenticated \
    --startup-probe=httpGet.path=/health,httpGet.port=8080
