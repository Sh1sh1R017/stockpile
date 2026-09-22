#!/usr/bin/env bash
# Azure Container Apps 1-Click Deployment Script (Bash)
set -e

RESOURCE_GROUP="rg-aibroll-autopilot"
LOCATION="eastus"
ACR_NAME="acraibroll$RANDOM"
APP_NAME="aibroll-studio"
ENV_NAME="env-aibroll-autopilot"

echo "=== Deploying AI B-Roll Studio to Azure Container Apps ==="

# Check az CLI
if ! command -v az &> /dev/null; then
    echo "Error: Azure CLI ('az') is not installed."
    exit 1
fi

# Load .env
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

if [ -z "$GEMINI_API_KEY" ]; then
    echo "Error: GEMINI_API_KEY is not set in environment or .env"
    exit 1
fi

echo "1. Creating Resource Group: $RESOURCE_GROUP ($LOCATION)..."
az group create --name "$RESOURCE_GROUP" --location "$LOCATION"

echo "2. Creating Azure Container Registry: $ACR_NAME..."
az acr create --resource-group "$RESOURCE_GROUP" --name "$ACR_NAME" --sku Basic --admin-enabled true

ACR_LOGIN_SERVER=$(az acr show --name "$ACR_NAME" --query loginServer --output tsv)
ACR_PASSWORD=$(az acr credential show --name "$ACR_NAME" --query "passwords[0].value" --output tsv)

echo "3. Building and pushing container image to ACR ($ACR_LOGIN_SERVER)..."
az acr build --registry "$ACR_NAME" --image "${APP_NAME}:latest" --file Dockerfile.azure .

echo "4. Creating Container Apps Environment: $ENV_NAME..."
az containerapp env create --name "$ENV_NAME" --resource-group "$RESOURCE_GROUP" --location "$LOCATION"

echo "5. Deploying Container App: $APP_NAME..."
az containerapp create \
    --name "$APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --environment "$ENV_NAME" \
    --image "${ACR_LOGIN_SERVER}/${APP_NAME}:latest" \
    --target-port 3000 \
    --ingress external \
    --registry-server "$ACR_LOGIN_SERVER" \
    --registry-username "$ACR_NAME" \
    --registry-password "$ACR_PASSWORD" \
    --cpu 2.0 --memory 4.0Gi \
    --min-replicas 1 --max-replicas 3 \
    --env-vars \
        GEMINI_API_KEY="$GEMINI_API_KEY" \
        GEMINI_MODEL="gemini-3.5-flash" \
        WHISPER_MODEL="base" \
        GOOGLE_CLIENT_ID="$GOOGLE_CLIENT_ID" \
        GOOGLE_CLIENT_SECRET="$GOOGLE_CLIENT_SECRET" \
        GOOGLE_DRIVE_INPUT_FOLDER_ID="$GOOGLE_DRIVE_INPUT_FOLDER_ID" \
        GOOGLE_DRIVE_OUTPUT_FOLDER_ID="$GOOGLE_DRIVE_OUTPUT_FOLDER_ID"

FQDN=$(az containerapp show --name "$APP_NAME" --resource-group "$RESOURCE_GROUP" --query properties.configuration.ingress.fqdn --output tsv)

echo ""
echo "=== DEPLOYMENT SUCCESSFUL ==="
echo "Your AI B-Roll Autopilot Studio is live online at: https://$FQDN"
