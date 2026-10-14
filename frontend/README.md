# Frontend Setup

This Vite + React application provides a churn prediction form and a customer
data chat interface for the FastAPI backend. The predictor displays SHAP
feature impacts. The assistant shows exact dataset summary counts and allows a
validated customer CSV upload that retrains the model and refreshes RAG.

## Install and configure

From PowerShell:

```powershell
Set-Location 'D:\New folder\churn_rag_project\frontend'
npm install
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

The default API address is `http://localhost:8000`. Change
`VITE_API_BASE_URL` in `.env` if your backend uses a different address.

CSV uploads must use the original 21-column Telco dataset schema and are limited
to 20 MB. The upload rebuilds the full local RAG index and requires a configured
OpenAI key on the backend.

## Start the development server

```powershell
npm run dev
```

Open `http://localhost:5173`. Start the backend separately from its own
terminal. The backend's CORS configuration must allow this origin.

## Build for production

```powershell
npm run build
npm run preview
```

## Run with Docker Compose

From the project root:

```powershell
docker compose build frontend
docker compose up -d frontend
```

The Compose frontend is available at `http://localhost:5173` and uses the
backend at `http://localhost:8000`. See the backend README for the full
two-service startup and shutdown commands.