from pathlib import Path
import subprocess
import sys

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


ROOT = Path(__file__).resolve().parent
FRONTEND_DIR = ROOT / "frontend"
REPORTS_DIR = ROOT / "reports"

app = FastAPI(title="Asset Analyst")

app.mount("/reports", StaticFiles(directory=REPORTS_DIR), name="reports")
app.mount("/frontend", StaticFiles(directory=FRONTEND_DIR), name="frontend")


@app.get("/")
def index():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.post("/analyze")
def analyze(ticker: str = Query(..., min_length=1, max_length=10)):
    clean = ticker.strip().upper()
    if not clean.replace(".", "").replace("-", "").isalnum():
        raise HTTPException(status_code=400, detail="Ticker non valido.")

    cmd = [sys.executable, str(ROOT / "main.py"), "--ticker", clean]
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=result.stderr or "Analisi fallita.")

    pdf_path = REPORTS_DIR / f"{clean}_report.pdf"
    if not pdf_path.exists():
        raise HTTPException(status_code=500, detail="Report PDF non trovato.")

    return {"report_url": f"/reports/{clean}_report.pdf"}
