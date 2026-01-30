import pandas as pd
from pathlib import Path


class FinancialCleaner:
    """
    Cleaner base per i bilanci scaricati con YFIngestor.

    Cosa fa:
    - legge i CSV in data/raw
    - normalizza i nomi delle colonne in snake_case
    - converte le colonne numeriche in float
    - converte la colonna 'date' in datetime
    - ordina i dati per data crescente
    - rimuove eventuali righe completamente vuote
    - salva i CSV puliti in data/processed
    """

    def __init__(self, raw_path: str = "data/raw", processed_path: str = "data/processed"):
        self.raw_path = Path(raw_path)
        self.processed_path = Path(processed_path)
        self.processed_path.mkdir(parents=True, exist_ok=True)

    # ------------ helper interni ------------ #

    @staticmethod
    def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
        """
        Converte tutti i nomi delle colonne in snake_case:
        es. 'Total Revenue' -> 'total_revenue'
        """
        new_cols = []
        for c in df.columns:
            c_str = str(c).strip()
            c_str = c_str.replace(" ", "_")
            c_str = c_str.replace("/", "_per_")
            c_str = c_str.replace("-", "_")
            c_str = c_str.lower()
            new_cols.append(c_str)
        df.columns = new_cols
        return df

    @staticmethod
    def _convert_numeric(df: pd.DataFrame) -> pd.DataFrame:
        """
        Converte tutte le colonne (eccetto 'date') in numeriche (float),
        forzando a NaN i valori non convertibili.
        """
        for col in df.columns:
            if col == "date":
                continue
            df[col] = pd.to_numeric(df[col], errors="coerce")
        return df

    @staticmethod
    def _clean_dates(df: pd.DataFrame) -> pd.DataFrame:
        """
        Converte 'date' in datetime, forza UTC e rimuove timezone
        per evitare mixed-timezone errors (pandas / Render).
        """
        if "date" in df.columns:
            df["date"] = (
                pd.to_datetime(df["date"], errors="coerce", utc=True)
                .dt.tz_convert(None)
            )
            df = df.sort_values("date").reset_index(drop=True)
        return df

    @staticmethod
    def _drop_empty_rows(df: pd.DataFrame) -> pd.DataFrame:
        """
        Rimuove eventuali righe completamente vuote (tutti NaN).
        """
        df = df.dropna(how="all")
        return df

    def _load_raw(self, filename: str) -> pd.DataFrame:
        path = self.raw_path / filename
        if not path.exists():
            raise FileNotFoundError(f"File non trovato: {path}")
        return pd.read_csv(path)

    def _save_processed(self, df: pd.DataFrame, filename: str) -> None:
        path = self.processed_path / filename
        df.to_csv(path, index=False)

    def _clean_generic(self, filename_in: str, filename_out: str) -> pd.DataFrame:
        """
        Pipeline di cleaning generica usata per tutti e tre i bilanci.
        """
        df = self._load_raw(filename_in)
        df = self._drop_empty_rows(df)
        df = self._normalize_columns(df)
        df = self._clean_dates(df)
        df = self._convert_numeric(df)
        self._save_processed(df, filename_out)
        return df

    # ------------ metodi pubblici ------------ #

    def clean_income_statement(self, ticker: str) -> pd.DataFrame:
        """
        Pulisce il CSV dell'Income Statement e lo salva in data/processed.
        """
        filename_in = f"{ticker}_income.csv"
        filename_out = f"{ticker}_income_clean.csv"
        return self._clean_generic(filename_in, filename_out)

    def clean_balance_sheet(self, ticker: str) -> pd.DataFrame:
        """
        Pulisce il CSV del Balance Sheet e lo salva in data/processed.
        """
        filename_in = f"{ticker}_balance.csv"
        filename_out = f"{ticker}_balance_clean.csv"
        return self._clean_generic(filename_in, filename_out)

    def clean_cash_flow(self, ticker: str) -> pd.DataFrame:
        """
        Pulisce il CSV del Cash Flow e lo salva in data/processed.
        """
        filename_in = f"{ticker}_cashflow.csv"
        filename_out = f"{ticker}_cashflow_clean.csv"
        return self._clean_generic(filename_in, filename_out)

    def clean_price_history(self, ticker: str) -> pd.DataFrame:
        """
        Pulisce il CSV dei prezzi storici e lo salva in data/processed.
        """
        filename_in = f"{ticker}_price.csv"
        filename_out = f"{ticker}_price_clean.csv"
        return self._clean_generic(filename_in, filename_out)

    def clean_all(self, ticker: str):
        """
        Esegue il cleaning di tutti e tre i bilanci per un ticker.
        """
        print(f"\n🧹 Pulizia bilanci per: {ticker}")

        is_df = self.clean_income_statement(ticker)
        print("   ✓ Income Statement pulito")

        bs_df = self.clean_balance_sheet(ticker)
        print("   ✓ Balance Sheet pulito")

        cf_df = self.clean_cash_flow(ticker)
        print("   ✓ Cash Flow pulito")

        try:
            price_df = self.clean_price_history(ticker)
            if not price_df.empty:
                print("   ✓ Price History pulito")
        except FileNotFoundError:
            price_df = None

        print("\n✔️ Cleaning completato.\n")

        return is_df, bs_df, cf_df
