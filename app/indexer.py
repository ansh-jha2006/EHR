import os
import json
from sentence_transformers import SentenceTransformer
import pandas as pd
import numpy as np
import faiss

DATA_DIR = "data"
OUT_DIR = "app"
EMB_MODEL = "all-MiniLM-L6-v2"


def load_notes():
    notes_path = os.path.join(DATA_DIR, "NOTEEVENTS.csv")
    diags_path = os.path.join(DATA_DIR, "DIAGNOSES_ICD.csv")

    notes = pd.DataFrame()
    if os.path.exists(notes_path):
        notes = pd.read_csv(notes_path)

    diags = pd.DataFrame()
    if os.path.exists(diags_path):
        diags = pd.read_csv(diags_path)

    items = []

    # collect notes
    if not notes.empty and "HADM_ID" in notes.columns:
        for _, r in notes.iterrows():
            text = None
            if "TEXT" in r:
                text = r.get("TEXT")
            else:
                text = " ".join([str(x) for x in r.values if pd.notna(x)])
            if pd.isna(text) or not isinstance(text, str) or not text.strip():
                continue
            items.append({"hadm_id": int(r.get("HADM_ID")) if pd.notna(r.get("HADM_ID")) else None,
                          "source": "note",
                          "text": text})

    # collect diagnoses
    if not diags.empty and "HADM_ID" in diags.columns:
        for _, r in diags.iterrows():
            text = None
            if "SHORT_TITLE" in r and pd.notna(r.get("SHORT_TITLE")):
                text = r.get("SHORT_TITLE")
            elif "ICD9_CODE" in r and pd.notna(r.get("ICD9_CODE")):
                text = str(r.get("ICD9_CODE"))
            else:
                text = " ".join([str(x) for x in r.values if pd.notna(x)])
            if pd.isna(text) or not isinstance(text, str) or not text.strip():
                continue
            items.append({"hadm_id": int(r.get("HADM_ID")) if pd.notna(r.get("HADM_ID")) else None,
                          "source": "diag",
                          "text": text})

    return items


def build_index(out_dir=OUT_DIR, model_name=EMB_MODEL):
    os.makedirs(out_dir, exist_ok=True)
    items = load_notes()
    texts = [it["text"] for it in items]

    model = SentenceTransformer(model_name)
    embeddings = model.encode(texts, show_progress_bar=True, batch_size=64)
    embeddings = np.array(embeddings).astype("float32")

    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)

    faiss.write_index(index, os.path.join(out_dir, "index.faiss"))

    # save metadata
    with open(os.path.join(out_dir, "index_meta.json"), "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False)

    print(f"Built index with {len(items)} items, dim={dim}")


if __name__ == "__main__":
    build_index()
