import yfinance as yf
import pandas as pd
from pathlib import Path

class YFIngestor:
    """
    Ingestione automatica dei bilanci tramite Yahoo Finance (yfinance).
    Nessuna API key richiesta.
    """

    def __init__(self, save_path: str = "data/raw"):
        self.save_path = Path(save_path)
        self.save_path.mkdir(parents=True, exist_ok=True)

    def get_income_statement(self, ticker: str):
        t = yf.Ticker(ticker)
        df = t.income_stmt.transpose()
        df.reset_index(names="date", inplace=True)
        df.to_csv(self.save_path / f"{ticker}_income.csv", index=False)
        return df

    def get_balance_sheet(self, ticker: str):
        t = yf.Ticker(ticker)
        df = t.balance_sheet.transpose()
        df.reset_index(names="date", inplace=True)
        df.to_csv(self.save_path / f"{ticker}_balance.csv", index=False)
        return df

    def get_cash_flow(self, ticker: str):
        t = yf.Ticker(ticker)
        df = t.cashflow.transpose()
        df.reset_index(names="date", inplace=True)
        df.to_csv(self.save_path / f"{ticker}_cashflow.csv", index=False)
        return df

    def get_price_history(self, ticker: str, period: str = "5y", interval: str = "1d"):
        t = yf.Ticker(ticker)
        df = t.history(period=period, interval=interval, auto_adjust=False)
        if df.empty:
            return df
        df.reset_index(inplace=True)
        df.to_csv(self.save_path / f"{ticker}_price.csv", index=False)
        return df

    def ingest_all(self, ticker: str):
        print(f"\n📥 Scarico bilanci per: {ticker} da Yahoo Finance")

        is_df = self.get_income_statement(ticker)
        print("   ✓ Income Statement OK")

        bs_df = self.get_balance_sheet(ticker)
        print("   ✓ Balance Sheet OK")

        cf_df = self.get_cash_flow(ticker)
        print("   ✓ Cash Flow OK")

        price_df = self.get_price_history(ticker)
        if price_df is not None and not price_df.empty:
            print("   ✓ Price History OK")

        print("\n✔️ Ingestion completata.\n")

        return is_df, bs_df, cf_df
    
    def get_report_metadata(self, ticker: str) -> dict:
        t = yf.Ticker(ticker)
        info = t.info

        current_price = (
            info.get("currentPrice")
            or info.get("regularMarketPrice")
            or info.get("previousClose")
        )

        company_name = (
            info.get("longName")
            or info.get("shortName")
            or ticker
        )

        return {
            "company_name": company_name,
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "country": info.get("country"),
            "market_cap": info.get("marketCap"),
            # fallback: revenue TTM dai financials se manca
            "revenue_ttm": info.get("totalRevenue"),
            "current_price": current_price,
        }


