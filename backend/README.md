# Backend Setup

This directory contains the FastAPI service, the trained churn model, and the
local ChromaDB index.

## 1. Configure Python and dependencies

From PowerShell:

```powershell
Set-Location 'D:\New folder\churn_rag_project\backend'
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If PowerShell prevents activation, run
`Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that terminal,
then activate the environment again.

## 2. Configure the database and chat provider

Create the local environment file from the template:

```powershell
Copy-Item .env.example .env
notepad .env
```

The default chat provider is local Ollama; no chat API key is needed. Configure
the local PostgreSQL URL in `.env` (the example uses the project defaults).
You can run PostgreSQL with Docker Compose while running FastAPI directly:

```powershell
Set-Location 'D:\New folder\churn_rag_project'
docker compose up -d db
```

Install Ollama and download the configured model (`llama3.2:3b`). RAG embeddings use
`sentence-transformers/all-MiniLM-L6-v2` locally on the CPU, so building,
searching, and rebuilding the vector index do not call OpenAI. The first run
downloads the embedding model from Hugging Face. OpenAI and Groq remain
optional chat providers if their respective provider and API key are configured.

## 3. Train and index the original Telco dataset

Place the provided `WA_Fn-UseC_-Telco-Customer-Churn.csv` file in
`backend/data/raw/`. Training and RAG setup read this original source file
directly. The following commands train the model and build the original RAG
index:

Run these commands from the backend directory:

```powershell
python scripts\train_model.py
python scripts\setup_rag.py
```

Training normalizes the source columns, converts Yes/No churn labels to 1/0,
and fills blank `TotalCharges` values with zero only for zero-tenure customers.
It saves the scikit-learn pipeline to `data/processed/model.pkl`. The index
command embeds the customer records locally and saves them in `chroma_db`.
Each index build uses a fresh collection, which also avoids mixing older
OpenAI-embedded vectors with the new local embedding model.
The model uses all 19 profile predictors; `customer_id` and the churn outcome
are excluded. Retrain with this command before starting the API after updating
from an older five-feature model.

## 4. Run the API and seed PostgreSQL

```powershell
Set-Location 'D:\New folder\churn_rag_project\backend'
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

On the first API startup, the app creates the PostgreSQL table and seeds at
least 30,000 unique customer profiles: 7,043 original Telco profiles retain
their known outcomes; the additional synthetic profiles have unknown actual
outcomes. Seeding does not retrain the model. Later customer additions and
edits also do not trigger retraining.

Interactive API documentation is available at `http://127.0.0.1:8000/docs`.
The default CORS origin allows the Vite development server at
`http://localhost:5173`.

Start Ollama before running chat. In a separate PowerShell window:

```powershell
ollama pull llama3.2:3b
ollama serve
```

Ollama Desktop may already be serving the local API; if so, it can be left
running without manually starting `ollama serve`.

### Endpoints

- `GET /health` reports whether the API process is running.
- `POST /predict` accepts the 19 customer profile features, excluding customer
  ID and churn outcome, and returns a churn prediction and probability.
  `total_charges` is optional and defaults to tenure multiplied by monthly
  charges. Unknown demographic/service values are allowed. The response also
  contains SHAP impacts grouped to the original profile fields.
- `POST /chat` retrieves matching customer records and asks the configured LLM
  to answer a question. The RAG context combines those records with exact
  full-dataset churn counts and segment statistics. Responses cite retrieved
  customer IDs and computed dataset-wide statistics.
- `GET /customers?page=1&page_size=25&search=...` lists records with pagination
  and optional ID search.
- `GET /customers/{customer_id}` retrieves one profile.
- `POST /customers` creates one profile; optional `actual_churn` is an observed
  outcome and may be unknown (`null`).
- `PUT` and `PATCH /customers/{customer_id}` replace or partially update a
  profile; `DELETE /customers/{customer_id}` removes it.
- `POST /customers/{customer_id}/predict` predicts from a saved profile and
  persists `predicted_churn` and `churn_probability`.
- `GET /analytics/summary` reports total rows and actual churn rates computed
  only from profiles with a known actual outcome.

The original actual label, optional manually recorded outcomes, and model
predictions are separate. Synthetic profiles remain unlabeled until an actual
outcome is entered. This educational API has no authentication; do not expose
customer management publicly without authentication, authorization, and audit
logging.

On API startup, missing PostgreSQL customer profiles, including generated
synthetic profiles, are added to ChromaDB in batches. Retrieved synthetic
records are identified as simulated examples, not observed customers.
Customer create/edit/delete requests sync the corresponding Chroma document
immediately. RAG's exact counts and segment comparisons use current PostgreSQL
records with known actual outcomes only. Predictions and unknown outcomes are
not counted as actual churn.

## Debug in VS Code

### Debug the Docker backend

The Compose backend runs `debugpy` on port 5678, bound to localhost on the host.
Start the services and rebuild the image if dependencies changed:

```powershell
Set-Location 'D:\New folder\churn_rag_project'
docker compose up -d --build
docker compose ps
```

Open the project root in VS Code, select
`backend\.venv\Scripts\python.exe` as the Python interpreter, and choose
**Python: Attach to Docker backend** under **Run and Debug** (`Ctrl+Shift+D`).
Press `F5` to attach. Set breakpoints in `backend/app/routes/predict.py`,
`backend/app/services/ml_service.py`, or the customer route/service files. Make
a matching request in the running browser app to stop at a breakpoint. The
launch profile maps local `backend` files to the container's `/app` directory.

Keep port 5678 private. A debugger connection can execute code in the backend
container, so do not bind or forward this port to an untrusted network.

### Debug a local backend instead

For a locally launched API, PostgreSQL must be running and the Compose backend
must be stopped to free port 8000:

```powershell
Set-Location 'D:\New folder\churn_rag_project'
docker compose up -d db
docker compose stop backend frontend
```

Choose **Python: FastAPI (local)**. The **Python: Debug API tests** profile
steps through the backend tests. For the frontend, start Vite with
`npm run dev` from `frontend`, then choose **Frontend: Chrome (Vite)**.

Prediction request example:

```json
{
  "tenure": 12,
  "monthly_charges": 70.0,
  "total_charges": 840.0,
  "senior_citizen": 0,
  "gender": "Female",
  "partner": "No",
  "dependents": "No",
  "phone_service": "Yes",
  "multiple_lines": "No",
  "internet_service": "Fiber optic",
  "online_security": "No",
  "online_backup": "No",
  "device_protection": "No",
  "tech_support": "No",
  "streaming_tv": "No",
  "streaming_movies": "No",
  "contract_type": "Month-to-month",
  "paperless_billing": "Yes",
  "payment_method": "Electronic check"
}
```

Chat request example:

```json
{
  "question": "Which contract type has the most churn in the indexed data?"
}
```

## Tests

Ensure PostgreSQL is running and the model has been trained before running the
API tests. From the project root:

```powershell
docker compose up -d db
```

Then run from the backend directory:

```powershell
python -m pytest
```

## Run with Docker Compose

From the project root, ensure `backend/.env`, the trained model, and the RAG
index are present, then build and start all three services:

```powershell
Set-Location 'D:\New folder\churn_rag_project'
docker compose build
docker compose up -d
docker compose ps
docker compose logs -f backend frontend
```

Compose starts PostgreSQL and waits for its health check before starting the
API. On first startup the API seeds the database. The trained model, original
data, Chroma index, Hugging Face model cache, and PostgreSQL use persistent
storage. The Docker image installs CPU-only PyTorch for local embeddings
rather than CUDA libraries. Keep the Windows Ollama server running; Compose
connects to it through `host.docker.internal:11434`.

Stop the services with:

```powershell
docker compose down
```