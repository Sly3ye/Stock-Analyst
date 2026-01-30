# Asset Analyst

Analisi finanziaria automatizzata con report PDF professionale basato su dati pubblici
(Yahoo Finance). Il progetto scarica i bilanci, pulisce i dati, calcola metriche,
applica modelli di valutazione e genera un report leggibile anche per non esperti,
con grafici e descrizioni dettagliate.

## Funzionalita
- Ingestion dei bilanci (income, balance, cash flow) e storico prezzi
- Cleaning e normalizzazione dei campi
- Calcolo metriche fondamentali (margini, crescita, leverage, liquidita)
- Analisi quality/growth/financial strength/stability
- Valutazione per-share (DCF, Buffett-style, Multipli) con scenari bear/base/bull
- Rating finale basato su valore, qualita e rischio
- Report PDF con tabelle, grafici e spiegazioni metriche

## Struttura del progetto
```
data/
  raw/          # dati grezzi scaricati da Yahoo Finance
  processed/    # dati puliti e normalizzati
  features/     # dataset arricchito con metriche
reports/
  charts/       # grafici generati per il PDF
src/
  ingestion/    # download dati (Yahoo Finance)
  processing/   # cleaning e normalizzazione
  features/     # calcolo metriche
  analyst/      # analisi e valutazione
  reporting/    # generazione report PDF
main.py
```

## Requisiti
- Python 3.10+
- Dipendenze principali: `yfinance`, `pandas`, `numpy`, `reportlab`, `matplotlib`

## Come eseguire
1) Installa le dipendenze
```
pip install -r requirements.txt
```

2) Avvia l'analisi
```
python main.py
```

3) Inserisci il ticker quando richiesto (es. `AAPL`, `SBUX`)

Il report sara salvato in `reports/<TICKER>_report.pdf`.

## Frontend + API (FastAPI)
Avvia il backend FastAPI per collegare la pagina frontend alla pipeline:
```
uvicorn server:app --reload
```

Poi apri:
```
http://127.0.0.1:8000/
```

Inserisci il ticker e premi "Analizza". Il server esegue `main.py` e il PDF
viene mostrato nella pagina con opzioni per scaricarlo o aprirlo in una nuova finestra.

## Note su metriche e assunzioni
- Le valutazioni sono per-share e dipendono da assunzioni conservative su crescita,
  tasso di sconto e multipli.
- Gli scenari (bear/base/bull) mostrano come cambia il fair value al variare
  delle ipotesi.
- Alcune metriche possono risultare N/D quando i dati non sono disponibili o
  non sono applicabili (es. ROE con equity negativo).

## Output principali
- Report PDF completo con descrizioni metriche
- Grafici di FCF, margini, leverage e crescita
- Scorecard sintetica con value/quality/growth/risk
