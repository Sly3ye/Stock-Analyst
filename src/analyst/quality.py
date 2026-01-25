# src/analyst/quality.py

import numpy as np
import pandas as pd


class QualityAnalyzer:
    """
    Business Quality Analyzer (FINAL).

    Valuta la qualità intrinseca del business, indipendentemente dal prezzo.

    Dimensioni:
    - Profitability
    - Growth Quality
    - Financial Strength
    - Stability & Predictability

    Output:
    - Quality Score sempre prodotto se >= 2 dimensioni valide
    - Confidence esplicita
    """

    # ======================================================
    # UTILS
    # ======================================================
    @staticmethod
    def _is_finite(x):
        return x is not None and np.isfinite(x)

    @staticmethod
    def _mean_ignore_nan(values):
        clean = [v for v in values if np.isfinite(v)]
        return float(np.mean(clean)) if clean else np.nan

    @staticmethod
    def _score_range(value, low, high):
        """
        Converte un valore continuo in score 0–100.
        """
        if not np.isfinite(value):
            return np.nan
        score = 100 * (value - low) / (high - low)
        return float(np.clip(score, 0, 100))

    @staticmethod
    def _safe_cagr_endpoints(series: pd.Series, periods: int):
        clean = series.dropna()
        if len(clean) < periods + 1:
            return np.nan
        start = clean.iloc[-(periods + 1)]
        end = clean.iloc[-1]
        if start <= 0 or end <= 0:
            return np.nan
        return float((end / start) ** (1 / periods) - 1)

    @staticmethod
    def _confidence(years_used, years_required):
        if years_required <= 0:
            return 0.0
        return float(min(1.0, years_used / years_required))

    # ======================================================
    # PROFITABILITY
    # ======================================================
    def _profitability(self, df: pd.DataFrame):
        metrics = {}
        scores = []

        years_required = 5

        op_margin = df.get("operating_margin")
        net_margin = df.get("net_margin")

        years_used = 0

        if op_margin is not None:
            clean = op_margin.dropna()
            if len(clean) >= 3:
                avg = clean.tail(years_required).mean()
                metrics["operating_margin_avg"] = avg
                scores.append(self._score_range(avg, 0.05, 0.30))
                years_used = max(years_used, len(clean.tail(years_required)))

        if net_margin is not None:
            clean = net_margin.dropna()
            if len(clean) >= 3:
                avg = clean.tail(years_required).mean()
                metrics["net_margin_avg"] = avg
                scores.append(self._score_range(avg, 0.03, 0.20))
                years_used = max(years_used, len(clean.tail(years_required)))

        score = self._mean_ignore_nan(scores)
        confidence = self._confidence(years_used, years_required)

        return score, confidence, metrics

    # ======================================================
    # GROWTH QUALITY
    # ======================================================
    def _growth_quality(self, df: pd.DataFrame):
        metrics = {}
        scores = []

        years_required = 5
        years_used = 0

        rev = df.get("total_revenue")
        ni = df.get("net_income")
        fcf = df.get("free_cash_flow")

        # Revenue growth
        if rev is not None:
            clean = rev.dropna()
            if len(clean) >= 3:
                g = self._safe_cagr_endpoints(clean, 2)
                metrics["revenue_growth"] = g
                scores.append(self._score_range(g, 0.00, 0.15))
                years_used = max(years_used, len(clean.tail(years_required)))

        # Earnings or FCF growth (prefer FCF)
        growth_base = None

        if fcf is not None and fcf.dropna().shape[0] >= 3:
            clean = fcf.dropna()
            growth_base = "fcf"
            g = self._safe_cagr_endpoints(clean, 2)
            metrics["fcf_growth"] = g
            scores.append(self._score_range(g, 0.00, 0.15))
            years_used = max(years_used, len(clean.tail(years_required)))

        elif ni is not None and ni.dropna().shape[0] >= 3:
            clean = ni.dropna()
            growth_base = "net_income"
            g = self._safe_cagr_endpoints(clean, 2)
            metrics["net_income_growth"] = g
            scores.append(self._score_range(g, 0.00, 0.15))
            years_used = max(years_used, len(clean.tail(years_required)))

        # Penalità: crescita ricavi senza conversione in FCF
        if (
            growth_base == "fcf"
            and "revenue_growth" in metrics
            and metrics["revenue_growth"] > 0.05
            and metrics.get("fcf_growth", 0) < 0.02
        ):
            scores.append(20)

        score = self._mean_ignore_nan(scores)
        confidence = self._confidence(years_used, years_required)

        return score, confidence, metrics

    # ======================================================
    # FINANCIAL STRENGTH
    # ======================================================
    def _financial_strength(self, df: pd.DataFrame):
        metrics = {}
        scores = []

        years_required = 3
        years_used = 0

        dte = df.get("debt_to_equity")
        dta = df.get("debt_to_assets")
        current_ratio = df.get("current_ratio")
        quick_ratio = df.get("quick_ratio")

        dte_used = False
        if dte is not None:
            clean = dte.dropna()
            if not clean.empty:
                v = clean.iloc[-1]
                metrics["debt_to_equity"] = v
                scores.append(self._score_range(-v, -2.5, 0.0))
                years_used = 1
                dte_used = True

        if not dte_used and dta is not None:
            clean = dta.dropna()
            if not clean.empty:
                v = clean.iloc[-1]
                metrics["debt_to_assets"] = v
                scores.append(self._score_range(-v, -1.0, 0.0))
                years_used = 1

        if current_ratio is not None:
            clean = current_ratio.dropna()
            if not clean.empty:
                v = clean.iloc[-1]
                metrics["current_ratio"] = v
                scores.append(self._score_range(v, 1.0, 3.0))
                years_used = max(years_used, 1)

        if quick_ratio is not None:
            clean = quick_ratio.dropna()
            if not clean.empty:
                v = clean.iloc[-1]
                metrics["quick_ratio"] = v
                scores.append(self._score_range(v, 0.7, 2.0))
                years_used = max(years_used, 1)


        score = self._mean_ignore_nan(scores)
        confidence = self._confidence(years_used, years_required)

        return score, confidence, metrics

    # ======================================================
    # STABILITY & PREDICTABILITY
    # ======================================================
    def _stability(self, df: pd.DataFrame):
        metrics = {}
        scores = []

        years_required = 5
        years_used = 0

        ni = df.get("net_income")
        fcf = df.get("free_cash_flow")
        op_margin = df.get("operating_margin")

        if ni is not None and ni.dropna().shape[0] >= 3:
            clean = ni.dropna().tail(years_required)
            vol = clean.std() / (abs(clean.mean()) + 1e-6)
            metrics["net_income_volatility"] = vol
            scores.append(self._score_range(-vol, -1.0, 0.0))
            years_used = max(years_used, len(clean))

        if fcf is not None and fcf.dropna().shape[0] >= 3:
            clean = fcf.dropna().tail(years_required)
            vol = clean.std() / (abs(clean.mean()) + 1e-6)
            metrics["fcf_volatility"] = vol
            scores.append(self._score_range(-vol, -1.0, 0.0))
            years_used = max(years_used, len(clean))

        if op_margin is not None and op_margin.dropna().shape[0] >= 3:
            clean = op_margin.dropna().tail(years_required)
            vol = clean.std()
            metrics["operating_margin_volatility"] = vol
            scores.append(self._score_range(-vol, -0.15, 0.0))
            years_used = max(years_used, len(clean))

        score = self._mean_ignore_nan(scores)
        confidence = self._confidence(years_used, years_required)

        return score, confidence, metrics

    # ======================================================
    # PUBLIC API
    # ======================================================
    def analyze(self, df: pd.DataFrame):
        p_score, p_conf, p_metrics = self._profitability(df)
        g_score, g_conf, g_metrics = self._growth_quality(df)
        f_score, f_conf, f_metrics = self._financial_strength(df)
        s_score, s_conf, s_metrics = self._stability(df)

        scores = [p_score, g_score, f_score, s_score]
        confidences = [p_conf, g_conf, f_conf, s_conf]

        valid_scores = [s for s in scores if np.isfinite(s)]

        quality_score = (
            float(np.mean(valid_scores)) if len(valid_scores) >= 2 else np.nan
        )

        quality_confidence = (
            float(np.mean([c for c in confidences if c > 0]))
            if len(valid_scores) >= 2
            else 0.0
        )

        return {
            "quality_score": quality_score,
            "quality_confidence": quality_confidence,

            "profitability_score": p_score,
            "profitability_confidence": p_conf,
            "growth_quality_score": g_score,
            "growth_confidence": g_conf,
            "financial_strength_score": f_score,
            "financial_strength_confidence": f_conf,
            "stability_score": s_score,
            "stability_confidence": s_conf,

            "details": {
                "profitability": p_metrics,
                "growth": g_metrics,
                "financial_strength": f_metrics,
                "stability": s_metrics,
            },
        }
