import json
import os
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_OLLAMA_MODEL = "llama3"
MAX_WORDS = 120


def _fmt_number(value, decimals):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number:
        return None
    return f"{number:.{decimals}f}"


def _fmt_pct(value):
    if value is None:
        return None
    return _fmt_number(value * 100.0, 1)


def _build_allowed_numbers(info: dict, results: dict) -> set[str]:
    allowed = set()

    def add(value, decimals):
        num = _fmt_number(value, decimals)
        if num is not None:
            allowed.add(num)

    def add_pct(value):
        pct = _fmt_pct(value)
        if pct is not None:
            allowed.add(pct)

    add(results.get("current_price") or info.get("current_price"), 2)
    add(results.get("fair_value"), 2)
    add_pct(results.get("upside"))

    add(results.get("quality_score"), 1)
    add(results.get("growth_score"), 1)
    add(results.get("risk_score"), 1)
    add(results.get("value_score"), 1)

    return allowed


def _extract_numbers(text: str) -> list[str]:
    raw = re.findall(r"-?\d+(?:[.,]\d+)?", text)
    return [value.replace(",", ".") for value in raw]


def _word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))


def _build_prompt(info: dict, results: dict, allowed_numbers: set[str]) -> str:
    company = (
        info.get("company_name")
        or info.get("longName")
        or info.get("shortName")
        or results.get("ticker")
        or "La società"
    )
    rules = (
        "Sei un analista finanziario. Scrivi un parere in italiano, massimo 120 parole. "
        "Devi basarti SOLO sui dati forniti. "
        "Non inventare numeri, non stimare, non arrotondare diversamente. "
        "Se citi un numero, deve essere ESATTAMENTE uno di quelli permessi. "
        "Se un dato manca, ometti quel punto. "
        "Interpreta i punteggi così: 0-39 = bassa, 40-59 = media, 60-79 = buona, 80-100 = eccellente. "
        "Per il rischio: punteggio più alto = rischio minore."
    )
    allowed = ", ".join(sorted(allowed_numbers)) if allowed_numbers else "nessuno"
    payload = {
        "company": company,
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "country": info.get("country"),
        "current_price": results.get("current_price") or info.get("current_price"),
        "fair_value": results.get("fair_value"),
        "upside": results.get("upside"),
        "rating": results.get("rating"),
        "quality_score": results.get("quality_score"),
        "growth_score": results.get("growth_score"),
        "risk_score": results.get("risk_score"),
        "value_score": results.get("value_score"),
        "valuation_confidence": results.get("valuation_confidence"),
        "quality_confidence": results.get("quality_confidence"),
        "rating_confidence": results.get("rating_confidence"),
    }
    return (
        f"{rules}\n\n"
        f"Numeri permessi (usa solo questi): {allowed}\n\n"
        f"DATI:\n{json.dumps(payload, ensure_ascii=False)}\n"
    )


def _call_ollama(prompt: str, model: str) -> str:
    req = Request(
        "http://localhost:11434/api/generate",
        data=json.dumps({"model": model, "prompt": prompt, "stream": False}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urlopen(req, timeout=20) as response:
        raw = response.read().decode("utf-8")
    data = json.loads(raw)
    return (data.get("response") or "").strip()


def generate_llm_summary(info: dict, results: dict, model: str | None = None) -> str:
    allowed_numbers = _build_allowed_numbers(info, results)
    prompt = _build_prompt(info, results, allowed_numbers)
    model_name = (model or os.environ.get("OLLAMA_MODEL") or DEFAULT_OLLAMA_MODEL).strip()
    if not model_name:
        raise RuntimeError("Modello Ollama non configurato.")

    try:
        text = _call_ollama(prompt, model_name)
    except (HTTPError, URLError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Errore servizio Ollama: {exc}") from exc

    if not text:
        raise RuntimeError("Ollama non ha restituito testo.")

    if _word_count(text) > MAX_WORDS:
        raise RuntimeError("Resoconto troppo lungo.")

    numbers = _extract_numbers(text)
    if allowed_numbers and any(num not in allowed_numbers for num in numbers):
        retry_prompt = (
            "Il testo precedente conteneva numeri non permessi. "
            "Riscrivi rispettando ESATTAMENTE i numeri permessi.\n\n"
            + prompt
        )
        text = _call_ollama(retry_prompt, model_name).strip()
        if not text:
            raise RuntimeError("Ollama non ha restituito testo.")
        if _word_count(text) > MAX_WORDS:
            raise RuntimeError("Resoconto troppo lungo.")
        numbers = _extract_numbers(text)
        if allowed_numbers and any(num not in allowed_numbers for num in numbers):
            raise RuntimeError("Resoconto contiene numeri non permessi.")

    return text
