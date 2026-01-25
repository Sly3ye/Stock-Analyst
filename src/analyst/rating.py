# src/analyst/rating.py

import numpy as np


class RatingEngine:
    """
    Sintesi analitica:
    trasforma analisi fondamentali, valuation e market
    in uno score e in un rating finale.
    """

    # -------------------------------------------------
    # SCORE HELPERS
    # -------------------------------------------------
    @staticmethod
    def clamp(x, low=0, high=100):
        return max(low, min(high, x))

    @staticmethod
    def _is_valid(x):
        return x is not None and np.isfinite(x)

    # -------------------------------------------------
    # VALUE SCORE
    # -------------------------------------------------
    def value_score(self, valuation: dict, market: dict):
        fair = valuation.get("fair_value")
        price = market.get("market_price")

        if not self._is_valid(fair) or not self._is_valid(price) or price <= 0:
            return 50

        upside = (fair / price) - 1

        score = 50 + upside * 100
        return self.clamp(score)

    # -------------------------------------------------
    # QUALITY SCORE
    # -------------------------------------------------
    def quality_score(self, quality: dict):
        """
        quality è già uno score aggregato
        (ROIC, margins, stability ecc.)
        """
        score = quality.get("quality_score")
        if not self._is_valid(score):
            return 50

        return self.clamp(score)

    # -------------------------------------------------
    # MARKET SCORE
    # -------------------------------------------------
    def market_score(self, market: dict):
        volatility = market.get("volatility")
        drawdown = market.get("max_drawdown")

        score = 100

        if self._is_valid(volatility):
            score -= volatility * 100

        if self._is_valid(drawdown):
            score += drawdown * 50  # drawdown è negativo

        return self.clamp(score)

    # -------------------------------------------------
    # RISK SCORE
    # -------------------------------------------------
    def risk_score(self, market: dict, valuation: dict):
        volatility = market.get("volatility")
        fair = valuation.get("fair_value")
        price = market.get("market_price")

        score = 100

        if self._is_valid(volatility):
            score -= volatility * 80

        if self._is_valid(fair) and self._is_valid(price) and price > fair:
            score -= 20  # sopravvalutazione

        return self.clamp(score)

    # -------------------------------------------------
    # FINAL RATING
    # -------------------------------------------------
    def final_rating(self, total_score):
        if total_score >= 75:
            return "BUY"
        elif total_score >= 55:
            return "HOLD"
        else:
            return "SELL"

    # -------------------------------------------------
    # ANALYZE
    # -------------------------------------------------
    def analyze(self, quality: dict, valuation: dict, market: dict):
        v_score = self.value_score(valuation, market)
        q_score = self.quality_score(quality)
        m_score = self.market_score(market)
        r_score = self.risk_score(market, valuation)

        v_conf = float(valuation.get("valuation_confidence", 0.0) or 0.0)
        q_conf = float(quality.get("quality_confidence", 0.0) or 0.0)

        market_inputs = [
            market.get("volatility"),
            market.get("max_drawdown"),
        ]
        m_conf = 1.0 if any(self._is_valid(x) for x in market_inputs) else 0.0

        vol = market.get("volatility")
        price = market.get("market_price")
        fair = valuation.get("fair_value")
        r_conf = 1.0 if (self._is_valid(vol) or (self._is_valid(price) and self._is_valid(fair))) else 0.0

        scores = [v_score, q_score, m_score, r_score]
        weights = [v_conf, q_conf, m_conf, r_conf]
        if sum(weights) > 0:
            total = float(np.average(scores, weights=weights))
        else:
            total = float(np.mean(scores))
        rating = self.final_rating(total)

        return {
            "value_score": round(v_score, 1),
            "quality_score": round(q_score, 1),
            "market_score": round(m_score, 1),
            "risk_score": round(r_score, 1),
            "total_score": round(total, 1),
            "score_confidence": round(float(np.mean([v_conf, q_conf, m_conf, r_conf])), 2),
            "rating": rating,
        }
