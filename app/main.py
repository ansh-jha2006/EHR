from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
import pandas as pd
import os
import json
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
import requests
import openai
from openai import OpenAI
from fastapi.staticfiles import StaticFiles
from app.database import SessionLocal, engine, init_db, Patient as DBPatient
from app.stage2_bert_nlp import BERTClinicalAnalyzer

DATA_DIR = "data"
INDEX_DIR = os.path.join("app")
INDEX_FILE = os.path.join(INDEX_DIR, "index.faiss")
META_FILE = os.path.join(INDEX_DIR, "index_meta.json")
EMB_MODEL = "all-MiniLM-L6-v2"

app = FastAPI(title="EHR Retrieval Chatbot (Full-Stack)")

# Initialize DB (Stage 3)
init_db()

# Mount static files (Stage 3)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/")
def read_root():
    return {"message": "Welcome to EHR API. Access dashboard at /static/index.html"}

# --- Models ---

class CheckUserResponse(BaseModel):
    exists: bool
    message: str
    questions: Dict[str, Any] = {}

class SummaryResponse(BaseModel):
    hadm_id: Any
    diagnoses: List[str]
    note_snippets: List[str]
    recommendation: str
    bert_entities: List[Dict[str, Any]] = []

@app.get("/system_health")
def system_health():
    """Check the health and configuration of the system with detailed CUDA status."""
    import torch
    gpu_available = torch.cuda.is_available()
    cuda_error = ""
    if not gpu_available:
        try:
            torch.cuda.init()
        except Exception as e:
            cuda_error = str(e)

    return {
        "gpu_available": gpu_available,
        "cuda_error": cuda_error if cuda_error else "None",
        "device": str(BERT_ANALYZER.device),
        "model_weights": "LOCAL (app/model_weights)" if os.path.exists("app/model_weights") and os.path.exists("app/model_weights/config.json") else "BASE (HuggingFace)",
        "data_directory": DATA_DIR,
        "database_status": "Connected"
    }

class NoteAnalysisRequest(BaseModel):
    text: str

class NoteAnalysisResponse(BaseModel):
    entities: List[Dict[str, Any]]
    severity_score: float
    embedding_snippet: List[float]

class ChatRequest(BaseModel):
    query: str
    hadm_id: Optional[int] = None
    k: int = 5

# --- Helpers ---

def _load_csv(name: str) -> pd.DataFrame:
    path = os.path.join(DATA_DIR, name)
    if not os.path.exists(path):
        return pd.DataFrame()
    return pd.read_csv(path)

def _load_index():
    if not os.path.exists(INDEX_FILE) or not os.path.exists(META_FILE):
        return None, None, None
    index = faiss.read_index(INDEX_FILE)
    with open(META_FILE, "r", encoding="utf-8") as f:
        meta = json.load(f)
    model = SentenceTransformer(EMB_MODEL)
    return index, meta, model

# --- Global Initialization ---

# load index on startup if available
VECTOR_INDEX, INDEX_META, EMB_MODEL_OBJ = _load_index()

# Initialize BERT Clinical Analyzer (Stage 2)
BERT_ANALYZER = BERTClinicalAnalyzer()

# --- Endpoints ---

@app.get("/check_user", response_model=CheckUserResponse)
def check_user(hadm_id: int):
    """Check whether an admission (hadm_id) exists; if not, return questions to create new patient."""
    admissions = _load_csv("ADMISSIONS.csv")
    patients = _load_csv("PATIENTS.csv")

    if not admissions.empty and "HADM_ID" in admissions.columns:
        match = admissions[admissions["HADM_ID"] == hadm_id]
    else:
        match = pd.DataFrame()

    if not match.empty:
        return CheckUserResponse(exists=True, message="Found existing admission.")

    if patients.empty:
        questions = {"note": "No PATIENTS.csv found — please provide basic demographics"}
    else:
        cols = list(patients.columns)
        questions = {c: f"Please provide {c}" for c in cols}

    return CheckUserResponse(exists=False, message="Admission not found; create new user.", questions=questions)

@app.post("/create_user")
def create_user(data: Dict[str, Any]):
    """Append a new row to PATIENTS.csv and the database (Stage 3)."""
    patients_path = os.path.join(DATA_DIR, "PATIENTS.csv")
    df = _load_csv("PATIENTS.csv")

    row = data.copy()
    if "SUBJECT_ID" not in row:
        row["SUBJECT_ID"] = int(pd.Timestamp.now().timestamp())

    # 1. Save to CSV (Legacy)
    new_row_df = pd.DataFrame([row])
    if not df.empty:
        df = pd.concat([df, new_row_df], ignore_index=True)
    else:
        df = new_row_df
    df.to_csv(patients_path, index=False)

    # 2. Save to Database (Stage 3)
    db = SessionLocal()
    try:
        db_patient = DBPatient(
            subject_id=row.get("SUBJECT_ID"),
            gender=row.get("GENDER"),
        )
        db.add(db_patient)
        db.commit()
    except Exception as e:
        print(f"DB Error: {e}")
        db.rollback()
    finally:
        db.close()

    return {"status": "created", "row": row}

def _summarize_text(texts: List[str]) -> str:
    big = " \n ".join([t for t in texts if isinstance(t, str)])
    if not big:
        return "No textual notes available to summarize."

    summary = big[:800]
    rec = "Recommend clinical review and correlate with labs."
    if "sepsis" in big.lower():
        rec = "Concern for sepsis — consider blood cultures and empiric antibiotics."
    elif "myocardial" in big.lower() or "mi" in big.lower():
        rec = "Cardiology evaluation recommended; consider troponin and ECG correlation."

    return f"{summary}\n\nRecommendation: {rec}"

@app.get("/summarize", response_model=SummaryResponse)
def summarize(hadm_id: int):
    """Return a summarized diagnosis and recommendation, enhanced with BERT entities."""
    diagnoses = _load_csv("DIAGNOSES_ICD.csv")
    notes = _load_csv("NOTEEVENTS.csv")

    diag_list = []
    if not diagnoses.empty and "HADM_ID" in diagnoses.columns:
        diag_rows = diagnoses[diagnoses["HADM_ID"] == hadm_id]
        if not diag_rows.empty:
            if "SHORT_TITLE" in diag_rows.columns:
                diag_list = diag_rows["SHORT_TITLE"].dropna().astype(str).tolist()
            elif "ICD9_CODE" in diag_rows.columns:
                diag_list = diag_rows["ICD9_CODE"].dropna().astype(str).tolist()

    note_texts = []
    if not notes.empty and "HADM_ID" in notes.columns:
        note_rows = notes[notes["HADM_ID"] == hadm_id]
        if not note_rows.empty:
            if "TEXT" in note_rows.columns:
                note_texts = note_rows["TEXT"].dropna().astype(str).tolist()[:5]

    recommendation = _summarize_text(note_texts)
    
    # Stage 2: Enhance with BERT entities
    all_notes_text = " ".join(note_texts)
    bert_entities = []
    if all_notes_text:
        bert_entities = BERT_ANALYZER.extract_entities(all_notes_text[:1000])

    return SummaryResponse(
        hadm_id=hadm_id, 
        diagnoses=diag_list, 
        note_snippets=note_texts, 
        recommendation=recommendation,
        bert_entities=bert_entities
    )

@app.post("/analyze_note", response_model=NoteAnalysisResponse)
def analyze_note(req: NoteAnalysisRequest):
    """Analyze a clinical note using BERT for entities, severity, and embeddings."""
    entities = BERT_ANALYZER.extract_entities(req.text)
    embedding = BERT_ANALYZER.encode_text(req.text)
    
    # Restored heuristic severity
    lower_text = req.text.lower()
    severity = 0.2
    if any(w in lower_text for w in ["critical", "severe", "acute", "emergency"]):
        severity = 0.9
    elif any(w in lower_text for w in ["moderate", "stable", "improving"]):
        severity = 0.5
        
    return NoteAnalysisResponse(
        entities=entities,
        severity_score=severity,
        embedding_snippet=embedding[:10]
    )

@app.post("/retrieve")
def retrieve(req: ChatRequest):
    """Retrieve top-k passages for a query and optional hadm_id."""
    if VECTOR_INDEX is None or INDEX_META is None or EMB_MODEL_OBJ is None:
        raise HTTPException(status_code=500, detail="Vector index not built.")

    q_emb = EMB_MODEL_OBJ.encode([req.query]).astype("float32")
    D, I = VECTOR_INDEX.search(q_emb, req.k)
    results = []
    for idx in I[0]:
        meta = INDEX_META[idx]
        if req.hadm_id is not None and meta.get("hadm_id") != req.hadm_id:
            continue
        results.append({"hadm_id": meta.get("hadm_id"), "source": meta.get("source"), "text": meta.get("text")})

    return {"query": req.query, "results": results}

def _call_olama_or_fallback(prompt: str) -> str:
    # 1. Try Local Ollama
    olama_url = os.environ.get("OLAMA_API_URL")
    if olama_url:
        try:
            resp = requests.post(f"{olama_url}/v1/generate", json={"prompt": prompt}, timeout=60)
            if resp.status_code == 200:
                data = resp.json()
                if "text" in data: return data["text"]
                if "choices" in data and len(data["choices"])>0: return data["choices"][0].get("text", str(data))
        except Exception:
            pass

    # 2. Try OpenAI Fallback
    openai_key = os.environ.get("OPENAI_API_KEY")
    if openai_key:
        try:
            client = OpenAI(api_key=openai_key)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "system", "content": "You are a clinical assistant."},
                          {"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"OpenAI Fallback failed: {e}")

    return "[LLM unavailable] " + prompt[:1000]

@app.post("/chat")
def chat(req: ChatRequest):
    """Retrieve context and send to LLM (Ollama or OpenAI fallback) to produce an answer."""
    if VECTOR_INDEX is None or INDEX_META is None or EMB_MODEL_OBJ is None:
        raise HTTPException(status_code=500, detail="Vector index not built.")

    context_texts = []
    if req.hadm_id is not None:
        for meta in INDEX_META:
            if meta.get("hadm_id") == req.hadm_id:
                context_texts.append(meta.get("text"))

    q_emb = EMB_MODEL_OBJ.encode([req.query]).astype("float32")
    D, I = VECTOR_INDEX.search(q_emb, req.k)
    for idx in I[0]:
        meta = INDEX_META[idx]
        context_texts.append(meta.get("text"))

    context = "\n---\n".join(list(dict.fromkeys(context_texts)))
    prompt = f"You are a clinical assistant. Use the following context to answer the question. Context:\n{context}\n\nQuestion: {req.query}\nAnswer concisely."

    resp = _call_olama_or_fallback(prompt)
    return {"answer": resp, "used_context_count": len(context_texts)}
wer the question. Context:\n{context}\n\nQuestion: {req.query}\nAnswer concisely."

    resp = _call_olama_or_fallback(prompt)
    return {"answer": resp, "used_context_count": len(context_texts)}
