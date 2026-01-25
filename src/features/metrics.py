import pandas as pd
import numpy as np
from pathlib import Path


class FinancialMetrics:
    """
    Calcolo delle metriche fondamentali:
    - Profitability
    - Margins
    - Growth
    - Cash Flow Strength
    - Leverage & Liquidity
    - Valuation ratios
    - Efficiency
    """

    def __init__(self, processed_path: str = "data/processed", features_path: str = "data/features"):
        self.processed_path = Path(processed_path)
        self.features_path = Path(features_path)
        self.features_path.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------
    # 1. CARICAMENTO E MERGE DEI TRE BILANCI
    # ---------------------------------------------------------

    def load_clean(self, ticker: str):
        """
        Carica i CSV puliti generati dal cleaner e li mergea in un unico DataFrame.
        """

        is_df = pd.read_csv(self.processed_path / f"{ticker}_income_clean.csv")
        bs_df = pd.read_csv(self.processed_path / f"{ticker}_balance_clean.csv")
        cf_df = pd.read_csv(self.processed_path / f"{ticker}_cashflow_clean.csv")

        df = is_df.merge(bs_df, on="date", suffixes=("_is", "_bs"), how="outer")
        df = df.merge(cf_df, on="date", suffixes=("", "_cf"), how="outer")

        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)

        return df

    # ---------------------------------------------------------
    # 2. CALCOLO METRICHE
    # ---------------------------------------------------------

    def compute_metrics(self, df: pd.DataFrame):
        """
        Calcola tutte le metriche fondamentali note.
        Usa field fallback perché Yahoo Finance cambia spesso nomenclatura.
        """

        def find_field(possible_names):
            for name in possible_names:
                if name in df.columns:
                    return df[name]
            return pd.Series([np.nan] * len(df))

        # Normalizzazione campi
        equity = find_field([
            "total_stockholder_equity",
            "stockholders_equity",
            "total_equity",
            "total_shareholder_equity",
            "total_equity_gross",
            "common_stock_equity",
            "total_equity_gross_minority_interest",
        ])

        debt = find_field([
            "total_debt",
            "short_long_term_debt",
            "short_long_term_debt_total",
            "total_debt_bs",
            "long_term_debt",
        ])

        cash = find_field([
            "cash",
            "cash_and_cash_equivalents",
            "cash_cash_equivalents_and_short_term_investments",
            "cash_and_cash_equivalents_and_short_term_investments",
        ])

        short_term_investments = find_field([
            "other_short_term_investments",
            "short_term_investments",
            "short_term_investment",
        ])

        current_assets = find_field(["total_current_assets", "current_assets"])
        current_liabilities = find_field(["total_current_liabilities", "current_liabilities"])
        total_assets = find_field(["total_assets"])

        operating_income = find_field(["operating_income", "ebit"])
        gross_profit = find_field(["gross_profit"])
        revenue = find_field(["total_revenue"])
        net_income = find_field(["net_income"])

        fcf = find_field(["free_cash_flow"])
        depreciation = find_field(["depreciation_and_amortization"])
        capex = find_field(["capital_expenditure"])

        receivables = find_field([
            "net_receivables",
            "accounts_receivable",
            "receivables",
            "gross_accounts_receivable",
        ])
        inventory = find_field(["inventory"])

        # ------------------ PROFITABILITY ------------------ #
        eps = 1e-6

        df["roe"] = np.where(
            equity > eps,
            net_income / equity,
            np.nan
        )
        df["roic"] = np.where(
            (equity + debt) > eps,
            operating_income / (equity + debt),
            np.nan
        )
        df["debt_to_equity"] = np.where(
            equity > eps,
            debt / equity,
            np.nan
        )
        raw_net_debt = find_field(["net_debt"])
        cash_total = np.where(
            cash.notna() | short_term_investments.notna(),
            cash.fillna(0) + short_term_investments.fillna(0),
            np.nan
        )
        computed_net_debt = np.where(
            debt.notna() & ~np.isnan(cash_total),
            debt - cash_total,
            np.nan
        )
        df["net_debt"] = np.where(
            raw_net_debt.notna(),
            raw_net_debt,
            computed_net_debt
        )

        # ------------------ MARGINS ------------------ #
        df["gross_margin"] = gross_profit / revenue
        df["operating_margin"] = operating_income / revenue
        df["net_margin"] = net_income / revenue

        # ------------------ CASH FLOW ------------------ #
        df["fcf_margin"] = fcf / revenue
        df["fcf_to_net_income"] = np.where(
            np.abs(net_income) > eps,
            fcf / net_income,
            np.nan
        )

        # ------------------ GROWTH ------------------ #
        df["revenue_growth"] = revenue.pct_change()
        df["net_income_growth"] = net_income.pct_change()
        df["fcf_growth"] = fcf.pct_change()


        def safe_cagr(series, years=3):
            prev = series.shift(years)
            return np.where(
                (series > 0) & (prev > 0),
                (series / prev) ** (1 / years) - 1,
                np.nan
            )

        df["revenue_cagr_3y"] = safe_cagr(revenue)
        df["net_income_cagr_3y"] = safe_cagr(net_income)
        df["fcf_cagr_3y"] = safe_cagr(fcf)

        # ------------------ LEVERAGE ------------------ #
        df["debt_to_assets"] = np.where(
            total_assets > eps,
            debt / total_assets,
            np.nan
        )

        # ------------------ LIQUIDITY ------------------ #
        df["current_ratio"] = np.where(
            current_liabilities > eps,
            current_assets / current_liabilities,
            np.nan
        )
        df["quick_ratio"] = np.where(
            current_liabilities > eps,
            (cash + receivables) / current_liabilities,
            np.nan
        )

        # ------------------ VALUATION ------------------ #
        shares = find_field(["ordinary_shares_number"])

        df["book_value_per_share"] = np.where(
            (equity > eps) & (shares > eps),
            equity / shares,
            np.nan
        )
        df["earnings_per_share"] = np.where(
            shares > eps,
            net_income / shares,
            np.nan
        )
        df["fcf_per_share"] = np.where(
            shares > eps,
            fcf / shares,
            np.nan
        )


        # ------------------ EFFICIENCY ------------------ #
        df["asset_turnover"] = revenue / df["total_assets"]
        df["inventory_turnover"] = np.where(
            inventory > eps,
            df["cost_of_revenue"] / inventory,
            np.nan
        )

        df["receivables_turnover"] = np.where(
            receivables > eps,
            revenue / receivables,
            np.nan
        )

        return df

    # ---------------------------------------------------------
    # 3. SALVATAGGIO
    # ---------------------------------------------------------

    def save_features(self, df: pd.DataFrame, ticker: str):
        path = self.features_path / f"{ticker}_features.csv"
        df.to_csv(path, index=False)

    # ---------------------------------------------------------
    # 4. ENTRY POINT PRINCIPALE
    # ---------------------------------------------------------

    def generate_features(self, ticker: str):
        print(f"\n📊 Calcolo metriche finanziarie per: {ticker}")

        df = self.load_clean(ticker)
        df = self.compute_metrics(df)
        self.save_features(df, ticker)

        print("✔️ Feature engineering completato.\n")
        return df
