# src/analyst/market.py

import pandas as pd
import numpy as np


class MarketAnalyzer:
    """
    Analisi di mercato:
    - prezzo
    - ritorni storici
    - volatilità
    - drawdown
    - multipli di mercato
    """

    # -------------------------------------------------
    # Utility
    # -------------------------------------------------
    @staticmethod
    def find_field(df, possible_names):
        for name in possible_names:
            if name in df.columns:
                return df[name]
        return None

    # -------------------------------------------------
    # 1. MARKET PRICE
    # -------------------------------------------------
    def market_price(self, df: pd.DataFrame, override_price=None, price_df: pd.DataFrame = None):
        if override_price is not None and np.isfinite(override_price):
            return float(override_price)
        source = price_df if price_df is not None else df
        price = self.find_field(source, ["close", "adj_close", "price"])
        if price is None:
            return np.nan
        return float(price.iloc[-1])

    # -------------------------------------------------
    # 2. RETURNS
    # -------------------------------------------------
    def returns(self, df: pd.DataFrame, price_df: pd.DataFrame = None):
        source = price_df if price_df is not None else df
        price = self.find_field(source, ["close", "adj_close"])
        if price is None or len(price) < 252:
            return {}

        returns = price.pct_change()

        return {
            "1Y": float((price.iloc[-1] / price.iloc[-252]) - 1),
            "3Y": float((price.iloc[-1] / price.iloc[-756]) - 1) if len(price) > 756 else np.nan,
            "5Y": float((price.iloc[-1] / price.iloc[-1260]) - 1) if len(price) > 1260 else np.nan,
        }

    # -------------------------------------------------
    # 3. VOLATILITY
    # -------------------------------------------------
    def volatility(self, df: pd.DataFrame, price_df: pd.DataFrame = None):
        source = price_df if price_df is not None else df
        price = self.find_field(source, ["close", "adj_close"])
        if price is None:
            return np.nan

        returns = price.pct_change().dropna()
        return float(returns.std() * np.sqrt(252))

    # -------------------------------------------------
    # 4. MAX DRAWDOWN
    # -------------------------------------------------
    def max_drawdown(self, df: pd.DataFrame, price_df: pd.DataFrame = None):
        source = price_df if price_df is not None else df
        price = self.find_field(source, ["close", "adj_close"])
        if price is None:
            return np.nan

        cumulative = price / price.iloc[0]
        peak = cumulative.cummax()
        drawdown = (cumulative - peak) / peak

        return float(drawdown.min())

    # -------------------------------------------------
    # 5. MARKET MULTIPLES
    # -------------------------------------------------
    def market_multiples(self, df: pd.DataFrame, market_price_override=None, price_df: pd.DataFrame = None):
        price = self.market_price(
            df,
            override_price=market_price_override,
            price_df=price_df
        )

        net_income = self.find_field(df, ["net_income"])
        fcf = self.find_field(df, ["free_cash_flow"])
        shares = self.find_field(df, ["ordinary_shares_number"])

        pe = np.nan
        p_fcf = np.nan

        if net_income is not None and shares is not None:
            ni = net_income.iloc[-1]
            sh = shares.iloc[-1]
            if ni > 0 and sh > 0:
                pe = price / (ni / sh)

        if fcf is not None and shares is not None:
            f = fcf.iloc[-1]
            sh = shares.iloc[-1]
            if f > 0 and sh > 0:
                p_fcf = price / (f / sh)

        return {
            "PE": float(pe) if np.isfinite(pe) else np.nan,
            "P_FCF": float(p_fcf) if np.isfinite(p_fcf) else np.nan,
        }

    # -------------------------------------------------
    # 6. SYNTHESIS
    # -------------------------------------------------
    def analyze(self, df: pd.DataFrame, market_price_override=None, price_df: pd.DataFrame = None):
        return {
            "market_price": self.market_price(
                df,
                override_price=market_price_override,
                price_df=price_df
            ),
            "returns": self.returns(df, price_df=price_df),
            "volatility": self.volatility(df, price_df=price_df),
            "max_drawdown": self.max_drawdown(df, price_df=price_df),
            "multiples": self.market_multiples(
                df,
                market_price_override=market_price_override,
                price_df=price_df
            ),
        }
