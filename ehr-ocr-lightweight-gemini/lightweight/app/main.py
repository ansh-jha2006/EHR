from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
import pandas as pd
import os
import json
import re

from google import genai
from google.genai import types

from app.database import SessionLocal, engine, init_db, Patient as DBPatient

DATA_DIR = "data"
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

app = FastAPI(title="EHR Lightweight API (Gemini-powered)")

# Allow the Vercel-hosted frontend to call this API.
# Set FRONTEND_ORIGIN on Render to your Vercel URL, e.g. https://your-app.vercel.app
FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN] if FRONTEND_ORIGIN != "*" else ["*"],
    allow_credentials=False if FRONTEND_ORIGIN == "*" else True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize DB
init_db()

_gemini_client = None


def get_gemini_client():
    global _gemini_client
    if _gemini_client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="GEMINI_API_KEY not configured on server.")
        _gemini_client = genai.Client(api_key=api_key)
    return _gemini_client


@app.get("/")
def read_root():
    return {"message": "EHR Lightweight API is running.", "docs": "/docs"}


@app.get("/system_health")
def system_health():
    return {
        "status": "ok",
        "gemini_configured": bool(os.environ.get("GEMINI_API_KEY")),
        "gemini_model": GEMINI_MODEL,
        "data_directory": DATA_DIR,
        "database_status": "Connected",
    }


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


class ReportAnalysisResponse(BaseModel):
    extracted_text: str
    summary: str
    entities: List[Dict[str, Any]] = []
    severity: str
    recommendation: str


# --- Helpers ---

def _load_csv(name: str) -> pd.DataFrame:
    path = os.path.join(DATA_DIR, name)
    if not os.path.exists(path):
        return pd.DataFrame()
    df = pd.read_csv(path)
    df.columns = [c.upper() for c in df.columns]
    return df


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


def _extract_json(text: str) -> dict:
    """Defensive parsing in case the model wraps JSON in markdown fences."""
    cleaned = re.sub(r"^```json\s*|^```\s*|```$", "", text.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


# --- Demo CSV-backed endpoints (unchanged behavior, lightweight) ---

@app.get("/check_user", response_model=CheckUserResponse)
def check_user(hadm_id: int):
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
        questions = {c: f"Please provide {c}" for c in patients.columns}

    return CheckUserResponse(exists=False, message="Admission not found; create new user.", questions=questions)


@app.post("/create_user")
def create_user(data: Dict[str, Any]):
    patients_path = os.path.join(DATA_DIR, "PATIENTS.csv")
    df = _load_csv("PATIENTS.csv")

    row = data.copy()
    if "SUBJECT_ID" not in row:
        row["SUBJECT_ID"] = int(pd.Timestamp.now().timestamp())

    new_row_df = pd.DataFrame([row])
    df = pd.concat([df, new_row_df], ignore_index=True) if not df.empty else new_row_df
    df.to_csv(patients_path, index=False)

    db = SessionLocal()
    try:
        db.add(DBPatient(subject_id=row.get("SUBJECT_ID"), gender=row.get("GENDER")))
        db.commit()
    except Exception as e:
        print(f"DB Error: {e}")
        db.rollback()
    finally:
        db.close()

    return {"status": "created", "row": row}


@app.get("/summarize", response_model=SummaryResponse)
def summarize(hadm_id: int):
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
        if not note_rows.empty and "TEXT" in note_rows.columns:
            note_texts = note_rows["TEXT"].dropna().astype(str).tolist()[:5]

    recommendation = _summarize_text(note_texts)

    return SummaryResponse(
        hadm_id=hadm_id,
        diagnoses=diag_list,
        note_snippets=note_texts,
        recommendation=recommendation,
    )


# --- NEW: Gemini-powered report OCR + medical analysis ---

ANALYSIS_PROMPT = """You are a clinical assistant analyzing a medical report image or PDF.
1. Perform OCR and transcribe all readable text from the document exactly as written.
2. Provide a brief clinical summary (2-4 sentences).
3. List key medical entities found (lab values, diagnoses, medications, vitals) as objects with "label" and "value".
4. Give an overall severity rating: one of "low", "moderate", "high".
5. Give a short recommendation for next clinical steps.

Respond with ONLY a JSON object in this exact shape:
{
  "extracted_text": "...",
  "summary": "...",
  "entities": [{"label": "...", "value": "..."}],
  "severity": "low|moderate|high",
  "recommendation": "..."
}
"""

ALLOWED_REPORT_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/webp",
}


@app.post("/analyze_report", response_model=ReportAnalysisResponse)
async def analyze_report(file: UploadFile = File(...)):
    """Upload a medical report (image or PDF). Gemini performs OCR + clinical analysis in one call."""
    if file.content_type not in ALLOWED_REPORT_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type}")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    client = get_gemini_client()
    part = types.Part.from_bytes(data=file_bytes, mime_type=file.content_type)

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[ANALYSIS_PROMPT, part],
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Gemini API error: {e}")

    try:
        parsed = _extract_json(response.text)
    except Exception:
        return ReportAnalysisResponse(
            extracted_text=response.text or "",
            summary="Could not parse structured analysis; showing raw model output.",
            entities=[],
            severity="moderate",
            recommendation="Review the extracted text manually.",
        )

    return ReportAnalysisResponse(
        extracted_text=parsed.get("extracted_text", ""),
        summary=parsed.get("summary", ""),
        entities=parsed.get("entities", []),
        severity=parsed.get("severity", "moderate"),
        recommendation=parsed.get("recommendation", ""),
    )
