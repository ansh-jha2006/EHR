EHR Retrieval Chatbot (minimal)

Quick start

1. Create a Python virtualenv and install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Run the app from the workspace root (where the CSV files are located):

```powershell
uvicorn app.main:app --reload --port 8000
```

Endpoints

- `GET /check_user?hadm_id=123` — returns whether an admission exists; if not, returns questions to create a new user.
- `POST /create_user` — accepts a JSON object with patient fields and appends to `PATIENTS.csv` (minimal).
- `GET /summarize?hadm_id=123` — returns simple diagnoses, some note snippets, and a heuristic recommendation.

Indexing and LLM-driven chat

- Build FAISS index (one-time):

```powershell
python -m app.indexer
```

- Start server (from workspace root):

```powershell
uvicorn app.main:app --reload --port 8000
```

- Retrieval endpoint: `POST /retrieve` with JSON body `{"query":"...","hadm_id":123,"k":5}`
- Chat endpoint: `POST /chat` with JSON body `{"query":"...","hadm_id":123,"k":5}` — attempts to call Olama if you set `OLAMA_API_URL` in env, otherwise returns a fallback placeholder.

Olama / LLM notes

- To use a local Olama instance, set `OLAMA_API_URL` env var (e.g. `http://localhost:11434`) before running the server. The app will POST to `OLAMA_API_URL/v1/generate`.
- If Olama is unavailable, the server will return a simple fallback response. You can replace `_call_olama_or_fallback` in `app/main.py` to call another LLM.

Notes

- This is a minimal, local prototype. Summarization is heuristic and not clinically validated.
- The code writes to `PATIENTS.csv` if creating users — please back up data before using.
