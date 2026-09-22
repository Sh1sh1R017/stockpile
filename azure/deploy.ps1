# Azure Container Apps 1-Click Deployment Script (PowerShell)
# Requirements: Azure CLI installed and logged in (az login)

Param(
    [string]$ResourceGroup = "rg-aibroll-autopilot",
    [string]$Location = "eastus",
    [string]$AcrName = "acraibroll" + (Get-Random -Minimum 1000 -Maximum 9999),
    [string]$AppName = "aibroll-studio",
    [string]$EnvName = "env-aibroll-autopilot"
)

Write-Host "=== Deploying AI B-Roll Studio to Azure Container Apps ===" -ForegroundColor Cyan

# 1. Check Azure CLI
if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    Write-Error "Azure CLI ('az') is not installed. Please install it from https://aka.ms/installazurecliwindows"
    exit 1
}

# 2. Load .env file
if (Test-Path ".env") {
    Write-Host "Loading environment variables from .env..." -ForegroundColor Yellow
    Get-Content .env | ForEach-Object {
        if ($_ -match "^([^#=]+)=(.*)$") {
            [System.Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim())
        }
    }
}

$GeminiKey = [System.Environment]::GetEnvironmentVariable("GEMINI_API_KEY")
if (-not $GeminiKey) {
    Write-Error "GEMINI_API_KEY is not set. Please set it in .env before deploying."
    exit 1
}

# 3. Create Resource Group
Write-Host "Creating Resource Group: $ResourceGroup in $Location..." -ForegroundColor Yellow
az group create --name $ResourceGroup --location $Location

# 4. Create Azure Container Registry (ACR)
Write-Host "Creating Azure Container Registry: $AcrName..." -ForegroundColor Yellow
az acr create --resource-group $ResourceGroup --name $AcrName --sku Basic --admin-enabled true

$AcrLoginServer = (az acr show --name $AcrName --query loginServer --output tsv)
$AcrPassword = (az acr credential show --name $AcrName --query "passwords[0].value" --output tsv)

# 5. Build and Push Container Image to ACR
Write-Host "Building and pushing container image to ACR ($AcrLoginServer)..." -ForegroundColor Yellow
az acr build --registry $AcrName --image "${AppName}:latest" --file Dockerfile.azure .

# 6. Create Azure Container Apps Environment
Write-Host "Creating Container Apps Environment: $EnvName..." -ForegroundColor Yellow
az containerapp env create --name $EnvName --resource-group $ResourceGroup --location $Location

# 7. Deploy Container App
Write-Host "Deploying Container App: $AppName..." -ForegroundColor Yellow
az containerapp create `
    --name $AppName `
    --resource-group $ResourceGroup `
    --environment $EnvName `
    --image "${AcrLoginServer}/${AppName}:latest" `
    --target-port 3000 `
    --ingress external `
    --registry-server $AcrLoginServer `
    --registry-username $AcrName `
    --registry-password $AcrPassword `
    --cpu 2.0 --memory 4.0Gi `
    --min-replicas 1 --max-replicas 3 `
    --env-vars `
        GEMINI_API_KEY="$GeminiKey" `
        GEMINI_MODEL="gemini-3.5-flash" `
        WHISPER_MODEL="base" `
        GOOGLE_CLIENT_ID="$([System.Environment]::GetEnvironmentVariable('GOOGLE_CLIENT_ID'))" `
        GOOGLE_CLIENT_SECRET="$([System.Environment]::GetEnvironmentVariable('GOOGLE_CLIENT_SECRET'))" `
        GOOGLE_DRIVE_INPUT_FOLDER_ID="$([System.Environment]::GetEnvironmentVariable('GOOGLE_DRIVE_INPUT_FOLDER_ID'))" `
        GOOGLE_DRIVE_OUTPUT_FOLDER_ID="$([System.Environment]::GetEnvironmentVariable('GOOGLE_DRIVE_OUTPUT_FOLDER_ID'))"

$Fqdn = (az containerapp show --name $AppName --resource-group $ResourceGroup --query properties.configuration.ingress.fqdn --output tsv)

Write-Host "`n=== DEPLOYMENT SUCCESSFUL ===" -ForegroundColor Green
Write-Host "Your AI B-Roll Autopilot Studio is live online at:" -ForegroundColor Green
Write-Host "https://$Fqdn" -ForegroundColor Cyan
