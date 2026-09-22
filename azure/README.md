# 🚀 Deploying AI B-Roll Autopilot Studio to Azure

This directory contains the production infrastructure and 1-click deployment scripts to run the **Next.js Web MVP**, **FastAPI Backend**, and **AI B-Roll Autopilot** fully online in the cloud on **Microsoft Azure**.

---

## 🏗️ Cloud Architecture

```
                    ┌──────────────────────────────────────────────┐
                    │               Azure Cloud                    │
                    │                                              │
 Internet ─────────►│  Azure Container Apps Ingress (HTTPS)        │
                    │   ├── Port 3000: Next.js Studio Dashboard    │
                    │   └── Port 8000: FastAPI Backend Bridge      │
                    │                                              │
                    │   Workers:                                   │
                    │   ├── Whisper Subtitles & Transcriptions     │
                    │   ├── Gemini 3.5 Flash AI Director           │
                    │   ├── Watermark-Free Montage Engine          │
                    │   └── Continuous Feedback Learning Engine    │
                    └──────────────────────────────────────────────┘
                                  ▲                │
                                  │ (Sync Inbound) │ (Upload Outbound)
                                  │                ▼
                    ┌──────────────────────────────────────────────┐
                    │               Google Drive                   │
                    │   ├── Input Folder: Raw Video Drops          │
                    │   └── Output Folder: Master 9:16 Deliverables│
                    └──────────────────────────────────────────────┘
```

---

## 📋 Prerequisites

1. **Azure Account** & [Azure CLI (`az`)](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli) installed.
2. Logged into Azure CLI:
   ```bash
   az login
   ```
3. Your `GEMINI_API_KEY` configured in `.env`.

---

## ⚡ 1-Click Automated Deployment

### On Windows (PowerShell):
```powershell
.\azure\deploy.ps1
```

### On Linux / macOS / Azure Cloud Shell (Bash):
```bash
chmod +x azure/deploy.sh
./azure/deploy.sh
```

The script will automatically:
1. Create a Resource Group (`rg-aibroll-autopilot`) in Azure.
2. Provision an Azure Container Registry (ACR).
3. Build the multi-stage container (`Dockerfile.azure`) in the cloud with system FFmpeg and Node.js.
4. Deploy to **Azure Container Apps** with 2.0 vCPU and 4.0 GB RAM.
5. Output your live public HTTPS domain: `https://aibroll-studio.<region>.azurecontainerapps.io`.

---

## 🐳 Local Container Testing (Docker Compose)

Before deploying to Azure, you can test the exact production cloud container locally:

```bash
docker compose up --build
```
- Web Dashboard: `http://localhost:3000`
- REST API: `http://localhost:8000/api/health`

---

## 🔄 Google Drive Inbound & Outbound Sync

To enable 24/7 cloud sync with Google Drive:
1. Provide `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`.
2. Set `GOOGLE_DRIVE_INPUT_FOLDER_ID` (where you drop raw videos).
3. Set `GOOGLE_DRIVE_OUTPUT_FOLDER_ID` (where master edits are delivered).
4. For headless cloud execution, set `GOOGLE_DRIVE_REFRESH_TOKEN` so the container syncs continuously without requiring interactive browser logins.
