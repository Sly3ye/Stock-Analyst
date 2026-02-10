from pathlib import Path
import json
import os
import subprocess
import sys
import time
import ssl
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request as UrlRequest, urlopen

import certifi
from src.reporting.ai_summary import generate_llm_summary

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse


ROOT = Path(__file__).resolve().parent
FRONTEND_DIR = ROOT / "frontend"
REPORTS_DIR = ROOT / "reports"

FRONTEND_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Asset Analyst")


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": f"Internal Server Error: {exc}"})

COMPANY_CACHE_TTL_SECONDS = 3600
COMPANY_CACHE = {}
DEFAULT_ALPHA_VANTAGE_KEY = "YGOFJB3SR4JB2EG0"
AI_SUMMARY_CACHE_TTL_SECONDS = 3600
AI_SUMMARY_CACHE = {}

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


@app.get("/companies")
def companies(query: str = Query(..., min_length=1, max_length=100)):
    api_key = (
        os.environ.get("ALPHAVANTAGE_API_KEY")
        or os.environ.get("ALPHA_VANTAGE_API_KEY")
        or DEFAULT_ALPHA_VANTAGE_KEY
        or ""
    ).strip()
    if not api_key:
        raise HTTPException(status_code=500, detail="API key Alpha Vantage non configurata.")

    normalized = query.strip().lower()
    now = time.time()
    cached = COMPANY_CACHE.get(normalized)
    if cached and now - cached["ts"] < COMPANY_CACHE_TTL_SECONDS:
        return {"results": cached["results"]}

    params = urlencode({"function": "SYMBOL_SEARCH", "keywords": query, "apikey": api_key})
    url = f"https://www.alphavantage.co/query?{params}"
    try:
        req = UrlRequest(url, headers={"User-Agent": "AssetAnalyst/1.0"})
        ssl_ctx = ssl.create_default_context(cafile=certifi.where())
        with urlopen(req, timeout=8, context=ssl_ctx) as response:
            payload = response.read().decode("utf-8")
    except (HTTPError, URLError) as exc:
        raise HTTPException(status_code=502, detail=f"Errore servizio Alpha Vantage: {exc}") from exc

    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail="Risposta non valida da Alpha Vantage.") from exc

    if "Error Message" in data or "Information" in data or "Note" in data:
        message = data.get("Error Message") or data.get("Information") or data.get("Note")
        raise HTTPException(status_code=502, detail=message or "Errore servizio Alpha Vantage.")

    matches = data.get("bestMatches", [])
    results = []
    for item in matches:
        name = (item.get("2. name") or "").strip()
        symbol = (item.get("1. symbol") or "").strip()
        if not name or not symbol:
            continue
        results.append(
            {
                "name": name,
                "ticker": symbol,
                "region": (item.get("4. region") or "").strip(),
                "currency": (item.get("8. currency") or "").strip(),
                "match_score": item.get("9. matchScore"),
            }
        )

    query_lc = query.strip().lower()

    def score_value(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def is_us_listing(item):
        region = (item.get("region") or "").lower()
        currency = (item.get("currency") or "").upper()
        return ("united states" in region or region == "usa") and currency == "USD"

    def is_primary_ticker(item):
        ticker = (item.get("ticker") or "")
        return "." not in ticker and "-" not in ticker

    def relevance_key(item):
        name_lc = (item.get("name") or "").lower()
        ticker_lc = (item.get("ticker") or "").lower()
        starts_name = name_lc.startswith(query_lc)
        starts_ticker = ticker_lc.startswith(query_lc)
        exact_ticker = ticker_lc == query_lc
        word_start = False
        if query_lc:
            word_start = any(part.startswith(query_lc) for part in name_lc.split())
        return (
            1 if is_us_listing(item) else 0,
            1 if exact_ticker else 0,
            1 if starts_ticker else 0,
            1 if word_start else 0,
            1 if starts_name else 0,
            score_value(item.get("match_score")),
            1 if is_primary_ticker(item) else 0,
        )

    pool = list(results)
    pool.sort(key=relevance_key, reverse=True)

    seen = set()
    deduped = []
    for item in pool:
        key = (item["name"].lower(), item["ticker"].lower())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    trimmed = deduped[:10]
    COMPANY_CACHE[normalized] = {"ts": now, "results": trimmed}
    return {"results": trimmed}


@app.get("/ai-summary")
def ai_summary(ticker: str = Query(..., min_length=1, max_length=10)):
    clean = ticker.strip().upper()
    now = time.time()
    cached = AI_SUMMARY_CACHE.get(clean)
    if cached and now - cached["ts"] < AI_SUMMARY_CACHE_TTL_SECONDS:
        return {"summary": cached["summary"]}

    json_path = REPORTS_DIR / f"{clean}_report.json"
    if not json_path.exists():
        raise HTTPException(status_code=404, detail="Report JSON non trovato. Esegui prima l'analisi.")

    try:
        payload = json.loads(json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail="Report JSON non valido.") from exc

    info = payload.get("info", {}) or {}
    results = payload.get("results", {}) or {}
    try:
        summary = generate_llm_summary(info, results)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if not summary:
        raise HTTPException(status_code=502, detail="Resoconto non disponibile.")

    AI_SUMMARY_CACHE[clean] = {"ts": now, "summary": summary}
    return {"summary": summary}
