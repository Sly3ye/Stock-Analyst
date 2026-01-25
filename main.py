from src.ingestion.yf_ingestor import YFIngestor
from src.processing.cleaner import FinancialCleaner
from src.features.metrics import FinancialMetrics
from src.analyst.analyst_engine import AnalystEngine
from src.reporting.pdf_reporter import PDFReporter
from src.reporting.assembler import ReportAssembler

import yfinance as yf
import pandas as pd
from pathlib import Path

def main():
    print("\n=== ASSET ANALYST — ANALISI COMPLETA ===\n")

    # 1️⃣ Input ticker
    ticker = input("Inserisci il ticker (es. AAPL): ").upper()

    # 2️⃣ Ingestion
    print("\n➡️  Scarico i bilanci...")
    ingestor = YFIngestor()
    ingestor.ingest_all(ticker)
    report_data = ingestor.get_report_metadata(ticker)
    
    # 3️⃣ Cleaning
    print("➡️  Pulizia bilanci...")
    cleaner = FinancialCleaner()
    cleaner.clean_all(ticker)

    price_df = None
    price_path = f"data/processed/{ticker}_price_clean.csv"
    if Path(price_path).exists():
        price_df = pd.read_csv(price_path)

    # 4️⃣ Feature Engineering
    print("➡️  Calcolo metriche finanziarie...")
    fm = FinancialMetrics()
    df_features = fm.generate_features(ticker)

    # 5️⃣ Analyst Engine (Analisi modulare)
    print("➡️  Analisi finanziaria avanzata...")
    analyst = AnalystEngine()
    analysis = analyst.analyze(
        df_features,
        ticker,
        market_price=report_data.get("current_price"),
        price_df=price_df
    )

    # 5️⃣ bis — Assembler report
    assembler = ReportAssembler()
    results = assembler.build(analysis)

    # prezzo corrente dal metadata (se non già presente)
    results["current_price"] = report_data.get("current_price")
    if (
        results.get("current_price") is not None
        and results.get("fair_value") is not None
        and results.get("current_price") == results.get("current_price")
        and results.get("fair_value") == results.get("fair_value")
        and results["current_price"] > 0
    ):
        results["upside"] = results["fair_value"] / results["current_price"] - 1.0

    # 6️⃣ Report PDF
    print("➡️  Generazione report PDF professionale...")
    reporter = PDFReporter()
    reporter.generate_report(
        ticker=ticker,
        df=df_features,
        info=report_data,
        results=results
    )
    print("\n=== ANALISI COMPLETATA ===")
    print(f"Report PDF salvato in: reports/{ticker}_report.pdf\n")


if __name__ == "__main__":
    main()
