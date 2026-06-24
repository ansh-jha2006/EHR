# EHR Lightweight (Gemini-powered) — Deployment Guide

This package contains the full lightweight version of the project:
- **Backend**: FastAPI, deploy to **Render**
- **Frontend**: static HTML/JS, deploy to **Vercel**
- **OCR + medical analysis**: powered entirely by the **Gemini API** (no local ML models)

## What's in this zip

```
.
├── app/
│   ├── main.py            # FastAPI backend (all endpoints, Gemini integration)
│   ├── database.py        # SQLite models (patients/events/predictions)
│   └── static/
│       └── index.html     # Frontend dashboard + report upload UI
├── data/
│   ├── ADMISSIONS.csv     # Demo data used by /check_user and /summarize
│   ├── PATIENTS.csv
│   ├── DIAGNOSES_ICD.csv
│   └── NOTEEVENTS.csv
├── requirements.txt
├── Procfile
├── .gitignore
├── .env.example
└── DEPLOYMENT.md          # this file
```

## 1. Push to GitHub

1. Create a new repo on GitHub (or reuse your existing one).
2. Upload/commit everything in this zip to the repo root, preserving the folder structure above.

## 2. Get a Gemini API key

1. Go to https://aistudio.google.com/apikey
2. Create an API key (free tier available).
3. Keep it handy — you'll paste it into Render as an environment variable, never into code or the frontend.

## 3. Deploy the backend on Render

1. Render dashboard → **New** → **Web Service** → connect your GitHub repo.
2. Settings:
   - **Root Directory:** leave blank (repo root)
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
     (Render will also auto-detect the included `Procfile`, so this is set automatically in most cases)
3. **Environment Variables** (Render dashboard → Environment):
   - `GEMINI_API_KEY` = *(your key from step 2)*
   - `GEMINI_MODEL` = `gemini-2.5-flash` *(optional — this is the default if omitted)*
   - `FRONTEND_ORIGIN` = `*` *(leave as `*` for now — you'll lock this down in step 6)*
4. Deploy. Once live, copy your backend URL, e.g. `https://ehr-backend-xxxx.onrender.com`.
5. Sanity check: open `https://ehr-backend-xxxx.onrender.com/system_health` in a browser. You should see:
   ```json
   {"status": "ok", "gemini_configured": true, "gemini_model": "gemini-2.5-flash", ...}
   ```
   If `gemini_configured` is `false`, double check the `GEMINI_API_KEY` env var was saved.

## 4. Point the frontend at your backend

1. In your GitHub repo, open `app/static/index.html`.
2. Find this line near the top of the `<script>` block:
   ```js
   const API_BASE = "https://YOUR-RENDER-BACKEND.onrender.com";
   ```
3. Replace it with your real Render URL from step 3, e.g.:
   ```js
   const API_BASE = "https://ehr-backend-xxxx.onrender.com";
   ```
4. Commit the change.

## 5. Deploy the frontend on Vercel

1. Vercel dashboard → **Add New** → **Project** → import the same GitHub repo.
2. Settings:
   - **Root Directory:** `app/static`
   - **Framework Preset:** Other
   - **Build Command:** *(leave empty)*
   - **Output Directory:** `.`
3. Deploy. You'll get a URL like `https://your-app.vercel.app`.

## 6. Lock down CORS (recommended, after both are live)

1. Go back to Render → your backend service → Environment.
2. Set `FRONTEND_ORIGIN` to your real Vercel URL, e.g. `https://your-app.vercel.app`.
3. Save — this triggers a redeploy. Now only your frontend domain can call the API (instead of `*`).

## 7. Test it end-to-end

1. Open your Vercel URL.
2. The header indicator should say **"Gemini Ready"** (green) — confirms the backend is reachable and the API key is configured.
3. Upload a medical report image or PDF under "Upload Medical Report" → click **Analyze Report**.
   - Gemini OCRs the document and returns a summary, severity rating, entities, and the raw extracted text.
4. Try "Patient Search (Demo Data)" with HADM_ID `142345` — pulls real demo diagnoses from `data/`.

## Notes & troubleshooting

- **Free Render tier sleeps when idle** — the first request after inactivity can take ~30-60s to wake up. This is normal, not a bug.
- **"Gemini API error" on upload** — usually means the `GEMINI_API_KEY` is missing/invalid, or you've hit a free-tier rate limit. Check Render logs.
- **CORS errors in browser console** — means `FRONTEND_ORIGIN` on Render doesn't match your Vercel URL exactly (including `https://`, no trailing slash).
- **File size limits** — Gemini accepts inline file data up to ~20MB per request comfortably; very large PDFs may need the Files API (not included here, ask if you need it).
- **Supported upload types**: PDF, PNG, JPEG, WEBP. Anything else is rejected with a 400 error.
