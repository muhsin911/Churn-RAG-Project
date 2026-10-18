# ChurnIQ Frontend

The React 19 and Vite single-page app provides the browser interface for the
FastAPI churn-analysis backend. The frontend does not train models or upload
customer CSV files; it sends profile and question requests to the backend API.

## Features

- **Predict risk:** submit a customer profile with all 19 model features, view
	the churn probability, and inspect SHAP contributions grouped by profile
	field. Look up an existing customer by ID to run and save a prediction.
- **Customers:** browse and search paginated PostgreSQL records, add a profile,
	edit a profile by ID, and delete a record. Observed churn is separate from
	the model prediction and may remain unknown.
- **Explore data:** view live counts and rates for known outcomes, ask questions
	about churn patterns, and review retrieved customer IDs. Synthetic examples
	are identified as simulated; unknown outcomes are excluded from exact rates.
- **Workspace navigation:** move among prediction, customer management, and
	data-assistant views without leaving the app.

## Requirements

- Node.js 20 or a compatible current LTS release
- The backend API running at `http://localhost:8000` by default
- A trained backend model for prediction requests
- PostgreSQL and a populated Chroma index for customer and assistant workflows

The backend README documents environment setup, model training, database
seeding, RAG indexing, and chat-provider configuration.

## Install and configure

Run these commands in PowerShell:

```powershell
Set-Location 'D:\New folder\churn_rag_project\frontend'
npm ci
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

The `.env.example` sets `VITE_API_BASE_URL=http://localhost:8000`. Change this
value if the API is hosted elsewhere. Vite reads this setting when it starts or
builds the app; restart the development server after changing it.

## Development

```powershell
npm run dev
```

Open `http://localhost:5173`. The API must allow this origin through its
`CORS_ORIGINS` setting. The Vite server binds to `0.0.0.0` and uses port 5173.

## Production build

```powershell
npm run build
npm run preview
```

The optimized static bundle is written to `dist/`. `npm run preview` serves the
build locally for a production-style check; it is not a production web server.

## Docker Compose

From the project root, configure `backend/.env`, train the model, and prepare
the RAG index before starting the stack:

```powershell
Set-Location 'D:\New folder\churn_rag_project'
docker compose up --build
```

The frontend is available at `http://localhost:5173` and calls the backend at
`http://localhost:8000`. Compose also starts PostgreSQL. Stop the stack with
`Ctrl+C` when running in the foreground, or use `docker compose down` from
another terminal.

## Troubleshooting

- A "Cannot reach the API" message usually means the backend is stopped or
	`VITE_API_BASE_URL` is incorrect.
- Browser CORS errors mean the frontend origin is missing from the backend's
	`CORS_ORIGINS` setting.
- Prediction errors can indicate that `backend/data/processed/model.pkl` has
	not been generated with `python scripts/train_model.py`.
- Assistant errors can indicate that Chroma has not been indexed or the
	backend's configured LLM provider is unavailable.