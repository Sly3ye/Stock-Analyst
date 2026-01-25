# src/analyst/analyst_engine.py

from src.analyst.quality import QualityAnalyzer
from src.analyst.valuation import ValuationEngine
from src.analyst.market import MarketAnalyzer
from src.analyst.rating import RatingEngine


class AnalystEngine:
    """
    Orchestratore dell'analisi finanziaria.
    Non contiene logica di business.
    """

    def analyze(self, df, ticker: str, market_price=None, price_df=None):
        # 1. Analisi fondamentali
        quality = QualityAnalyzer().analyze(df)

        # 2. Valutazione intrinseca
        valuation = ValuationEngine().analyze(df)

        # 3. Analisi di mercato
        market = MarketAnalyzer().analyze(
            df,
            market_price_override=market_price,
            price_df=price_df
        )

        # 4. Rating analitico
        rating = RatingEngine().analyze(
            quality=quality,
            valuation=valuation,
            market=market
        )

        return {
            # blocchi completi
            "quality": quality,
            "valuation": valuation,
            "market": market,
            "rating": rating,

            # --- FLAT API (per PDF / charts / UI) ---
            "quality_score": quality.get("quality_score"),
            "growth_score": quality.get("growth_quality_score"),
            "profitability_score": quality.get("profitability_score"),
            "financial_strength_score": quality.get("financial_strength_score"),
            "stability_score": quality.get("stability_score"),
            "quality_confidence": quality.get("quality_confidence"),

            "fair_value": valuation.get("fair_value"),
            "valuation_confidence": valuation.get("valuation_confidence"),
            "dcf_value": valuation.get("dcf_value"),
            "buffett_value": valuation.get("buffett_value"),
            "multiples_value": valuation.get("multiples_value"),

            "market_price": market.get("market_price"),

            "value_score": rating.get("value_score"),
            "risk_score": rating.get("risk_score"),
            "market_score": rating.get("market_score"),
            "total_score": rating.get("total_score"),
            "rating_label": rating.get("rating"),
        }

