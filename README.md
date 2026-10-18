# Intelligent Customer Churn Prediction & RAG Analysis System

A full-stack research prototype that predicts churn risk from the Telco
Customer Churn dataset and provides a retrieval-augmented chat interface for
exploring customer records.

> **Important:** This is an educational prototype, not a production decision
> system. Its prediction is a probability estimate from a baseline model.
> SHAP explanations describe model contributions, not causes or guarantees.

## Project goals

- Seed PostgreSQL with original labeled customers and synthetic unlabeled profiles.
- Clean and normalize the original Telco Customer Churn CSV for model training.
- Train and evaluate a Random Forest binary classifier.
- Serve churn predictions and RAG-assisted customer-data Q&A through FastAPI.
- Offer a React dashboard for prediction, paginated customer CRUD, and data Q&A.
- Package the frontend, backend, and PostgreSQL with Docker Compose.

## Architecture

### Draw.io architecture diagram description

Create the diagram with these grouped containers and directional connectors:

```text
+----------------------+       HTTP / JSON        +------------------------+
| React + Vite         | -----------------------> | FastAPI backend         |
| ChurnIQ dashboard    |                          | /predict /chat /analytics|
|                      |                          | /customers              |
| Port 5173            | <----------------------- | Port 8000               |
+----------------------+      JSON responses      +-----------+------------+
                                                             |
                          +----------------------------------+------------------+
                          |                                  |                  |
                          v                                  v                  v
                +------------------+               +------------------+
                | ML service       |               | RAG + analytics  |
                | Random Forest    |               | exact stats +    |
                | SHAP contributions|              | top-4 retrieval  |
                +--------+---------+               +--------+---------+
                         ^                                  |
                         |                                  v
                +--------+---------+               +------------------+
                | Fitted model.pkl |               | Persistent       |
                +------------------+               | ChromaDB         |
                                                   +--------+---------+
                                                            |
                                                            v
                                                   +-------------------+
                                                   | Local HF embeddings|
                                                   | Ollama local LLM   |
                                                   +-------------------+

       React Customer Manager <-> FastAPI CRUD <-> PostgreSQL
       7,043 labeled Telco profiles + synthetic profiles with unknown outcome

  Docker Compose runs frontend, backend, and PostgreSQL containers. PostgreSQL
  uses a named volume; backend/data and backend/chroma_db are host-mounted.
```

Connector details:

- React calls FastAPI with JSON over HTTP; browser CORS allows the local Vite
  origin `http://localhost:5173`.
- `/predict` calls the ML service, which loads the serialized
  `backend/data/processed/model.pkl` pipeline.
- `/chat` calls the RAG service, which searches persistent ChromaDB, then sends
  the retrieved customer documents and question to the configured LLM.
- `/customers` creates, reads, updates, deletes, and paginates PostgreSQL
  records. It stores model predictions separately from actual churn outcomes.
- The backend container exposes port 8000; the frontend development container
  exposes port 5173.

### Draw.io data-flow diagram description

```text
MODEL TRAINING
Original CSV
  -> validate expected source columns and customer IDs
  -> convert TotalCharges to numeric
  -> fill blank TotalCharges with 0 only where tenure = 0
  -> normalize column names and payment-method labels
  -> map Churn Yes/No to 1/0
  -> select 19 profile features, excluding customer ID and churn label
  -> stratified 80/20 train/test split
  -> impute optional senior_citizen values and one-hot encode categories
  -> fit RandomForestClassifier
  -> compute local SHAP contributions for the predicted churn probability
  -> report accuracy, precision, recall, F1
  -> save fitted preprocessing + model pipeline as model.pkl

ONLINE PREDICTION
User form (all 19 customer profile features)
  -> React/Axios POST /predict
  -> Pydantic validates values; backend estimates total_charges if omitted
  -> fitted pipeline preprocesses and predicts churn class/probability
  -> JSON response
  -> dashboard displays class, probability, and grouped feature contributions

CUSTOMER DATABASE
Original Telco CSV + generated synthetic profiles
  -> seed 30,000+ uniquely identified PostgreSQL records once
  -> keep synthetic actual churn outcomes unknown
  -> create/read/update/delete individual profiles; list with pagination
  -> retrieve a customer by ID and run the existing trained model
  -> store predicted yes/no and probability separately from manually entered actual outcome

RAG INDEXING / QUESTION ANSWERING
Original Telco, manual, and synthetic PostgreSQL customer profiles
  -> one natural-language document per customer, with actual outcome or "unknown"
  -> local sentence-transformers/all-MiniLM-L6-v2 creates vectors
  -> persist vectors/documents in ChromaDB; startup fills missing customer records
  -> customer create/edit/delete immediately upserts/removes its Chroma document

User question
  -> React/Axios POST /chat
  -> LangChain embeds the question
  -> ChromaDB retrieves the 4 nearest customer documents
  -> configured local Ollama model forms a grounded response by default
  -> response and retrieved customer IDs return to the chat UI
```

## Implementation / modules

- **Data Preprocessing Module**
  - `backend/app/utils/data_loader.py` validates the original CSV columns,
    normalizes values, checks customer ID uniqueness, and handles the 11 blank
    `TotalCharges` values only when tenure is zero.
  - The raw CSV is retained; loading and cleaning happen when training and
    indexing run.
- **Machine Learning Prediction Module**
  - `backend/scripts/train_model.py` performs a stratified train/test split and
    fits one-hot encoding plus a Random Forest in one scikit-learn pipeline.
  - `backend/app/services/ml_service.py` loads that pipeline and returns the
    churn class, class-1 probability, and grouped local SHAP contributions.
- **Customer Database Module**
  - PostgreSQL stores real and explicitly synthetic customer profiles with
    unique IDs, model predictions, and nullable manually observed outcomes.
  - `/customers` provides paginated list, ID lookup, create, replace, patch,
    delete, and stored-customer prediction endpoints.
  - Synthetic profiles never receive fabricated actual churn labels; summary
    rates use only known outcomes.
- **RAG Chat Module**
  - `backend/scripts/setup_rag.py` can rebuild a base index from the original
    Telco source. API startup fills missing customer profiles, including
    explicitly labeled synthetic examples, from PostgreSQL; CRUD changes
    immediately sync to ChromaDB.
  - `backend/app/services/rag_service.py` retrieves four matching documents
    and uses the configured LLM to formulate a response with customer IDs as
    source references.
- **Frontend Dashboard Module**
  - `frontend/src/pages/Predictor.jsx` submits a customer profile and displays
    the churn result and probability.
  - `frontend/src/pages/ChatAssistant.jsx` submits user questions and displays
    answers, errors, and retrieved customer IDs.
  - Reusable UI and API code lives under `frontend/src/components/` and
    `frontend/src/services/`.
- **Containerization Module**
  - `backend/Dockerfile` and `frontend/Dockerfile` define the Python and Node
    containers.
  - `docker-compose.yml` builds/runs both services and mounts backend data and
    ChromaDB so those assets persist outside container lifetimes.

## What the current prediction does—and does not explain

The predictor now shows **grouped SHAP contributions** for the fitted Random
Forest. The baseline probability plus the displayed feature impacts sum to the
model's churn probability (within floating-point tolerance). Positive impacts
push the model estimate toward churn; negative impacts push it away.

SHAP explains the model's behavior; it does not show causal effects, guarantee
the estimate is correct, or make this baseline model “perfect.” Correlated
features can share attribution. The interface labels the values as model
contributions rather than causes.

The Random Forest is trained on all 19 customer profile features:

1. `tenure`
2. `monthly_charges`
3. `total_charges`
4. `senior_citizen`
5. `gender`
6. `partner`
7. `dependents`
8. `phone_service`
9. `multiple_lines`
10. `internet_service`
11. `online_security`
12. `online_backup`
13. `device_protection`
14. `tech_support`
15. `streaming_tv`
16. `streaming_movies`
17. `contract_type`
18. `paperless_billing`
19. `payment_method`

`customer_id` is an identifier and `churn_label` is the training target; neither
is a model input. The RAG chat is a separate feature:
it retrieves similar text records to answer dataset questions and does not
explain, validate, or alter a specific `/predict` result.

### What RAG is for here

RAG (Retrieval-Augmented Generation) finds relevant customer records before
asking a language model to answer a question using those records. In this
project it complements prediction by making customer examples searchable and
summarizable; it does not train the churn classifier.

The assistant combines four semantically retrieved customer examples with
computed whole-dataset counts, churn rates, and higher-churn segments. This
makes questions about total churn and observed segment differences more
grounded. Exact counts and rates come from Pandas aggregation, not from vector
similarity. Churn-rate differences remain observational associations, not
proof of causes. Retention suggestions are experiment ideas whose effects must
be measured.

ChromaDB semantic retrieval includes original, manually entered, and generated
synthetic PostgreSQL customer profiles. Synthetic records are identified as
simulated examples and their unknown outcomes are not treated as observed
evidence. Customer records created or edited through the Customers screen sync
to the index immediately. RAG's exact counts and segment rates use live
PostgreSQL data and count only records with known actual outcomes; predictions
and unknown outcomes are never treated as actual churn labels.
When using the local Ollama model, RAG answers can take longer than ordinary
API requests; the frontend allows up to three minutes for chat responses.

### Is there project logic?

Yes. Data validation and cleaning, feature/label conversion, stratified
evaluation, the fitted prediction pipeline, grouped local SHAP explanations,
PostgreSQL customer CRUD, exact descriptive statistics, vector retrieval, LLM
response generation, and frontend-to-backend API calls are implemented.
Customer edits never retrain the model; only explicitly rerunning the training
script changes it. The model and retention advice remain a research baseline
and do not establish causality or guaranteed business benefit.

## Dataset and model

Place the original file here:

```text
backend/data/raw/WA_Fn-UseC_-Telco-Customer-Churn.csv
```

The supplied dataset has 7,043 customer rows and 21 source columns. Its churn
labels are imbalanced: about 26.5% of the supplied rows are churned. The cleaning
code converts the target from Yes/No to 1/0 and maps automatic payment-method
suffixes to the shorter API labels.

This original Telco CSV is the source for training, the initial PostgreSQL
seed, and the Chroma RAG index. The old 1,000-row mock CSV and its generator
were removed because the application did not read them.

The current baseline uses a stratified 80/20 split, a
`RandomForestClassifier(n_estimators=300, class_weight="balanced_subsample")`,
and a scikit-learn preprocessing pipeline. The recorded evaluation from the
current dataset and code was:

| Metric | Holdout result |
|---|---:|
| Accuracy | 0.771 |
| Precision | 0.580 |
| Recall | 0.495 |
| F1-score | 0.534 |

These are a single seeded holdout result for this baseline. They are not
guaranteed to represent future customers or establish business value.

## Requirements

- Python 3.11 or a compatible Python version for the backend dependencies.
- Node.js 20+ and npm for the frontend.
- Docker Desktop with Docker Compose for containerized startup.
- Ollama installed and running with the `llama3.2:3b` model downloaded.
- Internet access for the first local embedding-model download.

## Local development setup

### 1. Prepare and train the backend

PowerShell commands:

```powershell
Set-Location 'D:\New folder\churn_rag_project\backend'
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If PowerShell prevents script activation, allow it for the current terminal
only:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Create the local environment file:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
notepad .env
```

Start PostgreSQL from the project root before launching FastAPI directly:

```powershell
Set-Location 'D:\New folder\churn_rag_project'
docker compose up -d db
```

Example local model settings:

```dotenv
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b
CORS_ORIGINS=["http://localhost:5173"]
```

Train the model and build its RAG index:

```powershell
python scripts\train_model.py
python scripts\setup_rag.py
ollama pull llama3.2:3b
```

`setup_rag.py` downloads and runs the sentence-transformers embedding model
locally. It does not require an OpenAI key or send customer rows to an
embedding API. The first run needs internet access to download the model.

### 2. Start FastAPI

From `backend\`:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- API health: `http://localhost:8000/health`
- Interactive API docs: `http://localhost:8000/docs`

### 3. Start React + Vite

In a second PowerShell terminal:

```powershell
Set-Location 'D:\New folder\churn_rag_project\frontend'
npm install
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
npm run dev
```

Open `http://localhost:5173`. The API URL is configured by
`VITE_API_BASE_URL` in `frontend/.env`; the default is
`http://localhost:8000`.

## API endpoints

### `GET /health`

Returns the API process status:

```json
{"status": "ok"}
```

### `POST /predict`

Example request:

```json
{
  "tenure": 12,
  "monthly_charges": 70.0,
  "total_charges": 840.0,
  "contract_type": "Month-to-month",
  "payment_method": "Electronic check"
}
```

`total_charges` is optional and defaults to `tenure * monthly_charges`. The UI
asks for actual total charges to avoid this approximation when known. The
response includes grouped local SHAP impacts. Valid
contract values are `Month-to-month`, `One year`, and `Two year`; payment values
are `Electronic check`, `Mailed check`, `Bank transfer`, and `Credit card`.

Response shape:

```json
{
  "churn_prediction": false,
  "churn_probability": 0.32,
  "message": "This customer is predicted to stay.",
  "baseline_probability": 0.5,
  "explanations": [
    {
      "feature": "Tenure",
      "value": "12 months",
      "impact": -0.08
    }
  ]
}
```

`explanations` contains grouped SHAP contributions in probability units.
Multiply each impact by 100 to display percentage points. Positive values push
toward churn; negative values push away. They are model attributions, not
causal explanations.

### `POST /chat`

Example request:

```json
{
  "question": "What customer records have month-to-month contracts?"
}
```

The answer includes a list of customer IDs retrieved from ChromaDB as source
references plus a dataset-wide computed-statistics citation. RAG requests
require a configured LLM provider and an existing `backend/chroma_db` index.

### `GET /customers`

Lists customers with `page`, `page_size` (maximum 100), and optional `search`
query parameters. The response includes the result page, total count, and
pagination metadata.

### `GET /customers/{customer_id}`

Retrieves one saved customer profile by its unique customer ID.

### `POST /customers`

Creates one customer profile. The body accepts the model features, contact /
service context fields, and optional `actual_churn` (`true`, `false`, or `null`
for not yet known). New customer records do not retrain the model.

### `PUT /customers/{customer_id}` and `PATCH /customers/{customer_id}`

Replace the editable profile fields or update only the supplied fields. A
known actual outcome is preserved by `PUT` if the request omits it; explicit
`null` can reset it to unknown. Profile edits clear stale saved predictions.

### `DELETE /customers/{customer_id}`

Deletes one record by ID.

### `POST /customers/{customer_id}/predict`

Runs the existing trained model for a saved profile and stores `predicted_churn`
and `churn_probability`. These prediction fields are distinct from
`actual_churn`, which records an observed/manual outcome.

### `GET /analytics/summary`

Returns total database rows, count of known actual outcomes, count of
unlabeled records, actual churned/retained counts and rates based only on known
outcomes, and observed churn rates for sufficiently large labeled segments.
The initial database contains the original 7,043 labeled Telco records plus
synthetic profiles with unknown actual outcomes.

## Debugging and learning the request flow

Open the project root folder in VS Code and select the backend virtual
environment (`backend\.venv\Scripts\python.exe`) as the Python interpreter.
The shared `.vscode/launch.json` provides Run and Debug profiles:

- **Python: FastAPI (local)** starts the API under the debugger.
- **Python: Attach to Docker backend** attaches to the FastAPI process running
  in the Compose backend container.
- **Python: Debug API tests** runs the API tests under the debugger.
- **Frontend: Chrome (Vite)** opens the frontend in a browser debugger; start
  Vite first with `npm run dev` from `frontend`.

### Debug the backend inside Docker

The normal Compose backend starts `debugpy` on port 5678 without waiting for an
IDE connection, so the API and frontend still start normally. Compose binds
that port to localhost only. Do not change it to a public interface or expose
it through a public firewall: an attached debugger can execute code in the
backend container.

```powershell
Set-Location 'D:\New folder\churn_rag_project'
docker compose up -d --build
docker compose ps
```

With the containers running, open **Run and Debug** (`Ctrl+Shift+D`), choose
**Python: Attach to Docker backend**, and press `F5`. Set breakpoints in
`backend/app/routes/predict.py` and
`backend/app/services/ml_service.py`, then submit a prediction from the browser.
The debugger maps local `backend` source files to `/app` inside the container.
Use **Step Over** (`F10`), **Step Into** (`F11`), and the Variables panel to
follow the request.

Use **Python: FastAPI (local)** only when intentionally debugging a locally
launched API; stop the Compose backend first to free port 8000. For the
frontend profile, start Vite in a terminal first:

```powershell
Set-Location 'D:\New folder\churn_rag_project\frontend'
npm run dev
```

To study database lookups and saved predictions, set breakpoints in
`backend/app/routes/customers.py` and
`backend/app/services/customer_service.py`.

## Docker

Train the model and create the RAG index locally first. The backend container
mounts `backend/data`, `backend/chroma_db`, and the Hugging Face model cache
from the host, so generated assets and the downloaded embedding model persist
across restarts.

Keep Ollama Desktop running on Windows. Docker Compose reaches its local API
through `host.docker.internal:11434`.

From the project root:

```powershell
Set-Location 'D:\New folder\churn_rag_project'
docker compose build
docker compose up -d
docker compose ps
docker compose logs -f backend frontend
```

Visit `http://localhost:5173` and `http://localhost:8000/docs`. Stop containers
without deleting persistent project data:

```powershell
docker compose down
```

## Tests and frontend production build

Backend tests:

```powershell
Set-Location 'D:\New folder\churn_rag_project'
docker compose up -d db
Set-Location 'D:\New folder\churn_rag_project\backend'
.\.venv\Scripts\Activate.ps1
python scripts\train_model.py
Set-Location 'D:\New folder\churn_rag_project'
docker compose up -d backend
Set-Location 'D:\New folder\churn_rag_project\backend'
.\.venv\Scripts\Activate.ps1
python -m pytest -q
```

Frontend:

```powershell
Set-Location 'D:\New folder\churn_rag_project\frontend'
npm run build
npm audit
```

## Conclusion

This project delivers an end-to-end churn analytics prototype: it cleans an
original customer dataset, trains and evaluates a Random Forest pipeline,
serves predictions and PostgreSQL customer management through FastAPI,
retrieves customer records for LLM-assisted Q&A, and presents these functions
in a React dashboard. Docker Compose runs the frontend, backend, and database.

## Future enhancements

- Train and compare models using more of the original customer/service fields;
  tune decision thresholds and evaluate with cross-validation, ROC-AUC,
  PR-AUC, calibration, and business-cost analysis.
- Add exact Pandas/SQL aggregate tools alongside RAG for questions requiring
  precise counts, percentages, and rankings.
- Add authentication, authorization, audit logging, and backup/rollback
  controls before exposing customer CRUD publicly.
- Deploy the containers to AWS with secrets management, observability,
  authenticated APIs, and managed storage.
- Add real-time customer event ingestion and drift monitoring.
- Audit for fairness and validate performance on newer, representative data.

## Simple explanation

The ML model estimates churn using all 19 customer profile features, excluding
the customer ID and churn outcome. The predictor shows grouped SHAP
contributions to explain the model's estimate, not causes. The RAG assistant
searches original, manual, and explicitly labeled synthetic examples; synthetic
unknown outcomes do not count toward actual churn rates. Embeddings and, by
default, chat generation run locally through Ollama. PostgreSQL keeps known
outcomes separate from model predictions, and customer updates do not retrain
the fitted model.
