class ReportAssembler:
    """
    Traduce l'output strutturato dell'AnalystEngine
    in un dizionario flat compatibile con PDFReporter.
    """

    def build(self, analysis: dict) -> dict:
        quality = analysis.get("quality", {})
        valuation = analysis.get("valuation", {})
        market = analysis.get("market", {})
        rating = analysis.get("rating", {})

        current_price = market.get("market_price")
        fair_value = valuation.get("fair_value")

        upside = None
        if self._is_finite(current_price) and self._is_finite(fair_value):
            upside = fair_value / current_price - 1.0

        return {
            # blocchi completi per PDF
            "quality": quality,
            "valuation": valuation,
            "market": market,

            # ==========================
            # Investment Snapshot
            # ==========================
            "current_price": current_price,
            "fair_value": fair_value,
            "upside": upside,
            "rating": rating.get("rating"),

            # ==========================
            # Valuation Summary
            # ==========================
            "dcf_value": valuation.get("dcf_value"),
            "buffett_value": valuation.get("buffett_value"),
            "multiples_value": valuation.get("multiples_value"),
            "valuation_confidence": valuation.get("valuation_confidence"),

            # ==========================
            # Quality Scores
            # ==========================
            "quality_score": quality.get("quality_score"),
            "profitability_score": quality.get("profitability_score"),
            "growth_score": quality.get("growth_quality_score"),
            "financial_strength_score": quality.get("financial_strength_score"),
            "stability_score": quality.get("stability_score"),
            "quality_confidence": quality.get("quality_confidence"),

            # ==========================
            # Rating Scores
            # ==========================
            "value_score": rating.get("value_score"),
            "market_score": rating.get("market_score"),
            "risk_score": rating.get("risk_score"),
            "total_score": rating.get("total_score"),
            "rating_confidence": rating.get("score_confidence"),
        }

    @staticmethod
    def _is_finite(value):
        try:
            return value is not None and float(value) == float(value)
        except Exception:
            return False
