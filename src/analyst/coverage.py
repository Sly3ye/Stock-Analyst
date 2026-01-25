# src/analyst/coverage.py

from dataclasses import dataclass
import numpy as np


@dataclass
class MetricResult:
    value: float | None
    years_used: int
    years_required: int
    confidence: float  # 0.0 – 1.0


def compute_with_fallback(
    series,
    preferred_years: int = 5,
    minimum_years: int = 3,
    reducer=np.mean
) -> MetricResult:
    if series is None:
        return MetricResult(None, 0, preferred_years, 0.0)

    clean = series.dropna()

    if len(clean) < minimum_years:
        return MetricResult(
            value=None,
            years_used=len(clean),
            years_required=preferred_years,
            confidence=0.0
        )

    used = min(len(clean), preferred_years)
    subset = clean.tail(used)

    return MetricResult(
        value=float(reducer(subset)),
        years_used=used,
        years_required=preferred_years,
        confidence=used / preferred_years
    )


def aggregate_metric_results(results, min_valid: int = 2):
    """
    Aggrega risultati metrici.
    Accetta:
    - MetricResult
    - dict con chiavi: value, confidence
    """

    extracted = []

    for r in results:
        if r is None:
            continue

        # Caso 1: MetricResult
        if isinstance(r, MetricResult):
            if r.value is not None:
                extracted.append((r.value, r.confidence))

        # Caso 2: dict {value, confidence}
        elif isinstance(r, dict):
            value = r.get("value")
            confidence = r.get("confidence", 0.0)
            if value is not None:
                extracted.append((value, confidence))

    if len(extracted) < min_valid:
        return {
            "value": None,
            "used": len(extracted),
            "total": len(results),
            "confidence": 0.0
        }

    values = [v for v, _ in extracted]
    confidences = [c for _, c in extracted]

    return {
        "value": float(np.mean(values)),
        "used": len(extracted),
        "total": len(results),
        "confidence": float(np.mean(confidences))
    }


