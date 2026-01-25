import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from pathlib import Path


class ChartGenerator:
    """
    Genera grafici professionali in stile minimal da includere nel PDF.
    """

    def __init__(self, output_path="reports/charts"):
        self.output_path = Path(output_path)
        self.output_path.mkdir(parents=True, exist_ok=True)

        # Stile minimal professionale (senza usare seaborn)
        plt.rcParams["axes.edgecolor"] = "black"
        plt.rcParams["axes.linewidth"] = 0.6
        plt.rcParams["axes.labelcolor"] = "black"
        plt.rcParams["text.color"] = "black"
        plt.rcParams["xtick.color"] = "black"
        plt.rcParams["ytick.color"] = "black"
        plt.rcParams["grid.color"] = "#DDDDDD"
        plt.rcParams["grid.linestyle"] = "-"
        plt.rcParams["grid.linewidth"] = 0.5

    # ------------------- TOOL INTERNO ------------------- #

    def _save_fig(self, fig, filename):
        path = self.output_path / filename
        fig.savefig(path, dpi=200, bbox_inches="tight")
        plt.close(fig)
        return str(path)

    def _placeholder_fig(self, title):
        fig, ax = plt.subplots(figsize=(6, 3))
        ax.set_title(title, fontsize=12)
        ax.axis("off")
        ax.text(0.5, 0.5, "Dati non disponibili", ha="center", va="center")
        return fig

    def _has_series(self, df: pd.DataFrame, column: str):
        return column in df.columns and df[column].dropna().shape[0] > 0

    # ------------------- 1. FCF Chart ------------------- #

    def plot_fcf(self, df: pd.DataFrame, ticker: str):
        title = f"{ticker} – Free Cash Flow"
        if not self._has_series(df, "free_cash_flow"):
            fig = self._placeholder_fig(title)
            return self._save_fig(fig, f"{ticker}_fcf.png")

        fig, ax = plt.subplots(figsize=(6, 3))
        ax.plot(df["date"], df["free_cash_flow"], linewidth=2)
        ax.set_title(title, fontsize=12)
        ax.set_xlabel("Anno")
        ax.set_ylabel("FCF")
        ax.tick_params(axis="x", rotation=45)
        ax.grid(True)

        return self._save_fig(fig, f"{ticker}_fcf.png")

    # ------------------- 2. Margins ------------------- #

    def plot_margins(self, df: pd.DataFrame, ticker: str):
        title = f"{ticker} – Margini"
        has_any = any(
            self._has_series(df, col)
            for col in ["gross_margin", "operating_margin", "net_margin"]
        )
        if not has_any:
            fig = self._placeholder_fig(title)
            return self._save_fig(fig, f"{ticker}_margins.png")

        fig, ax = plt.subplots(figsize=(6, 3))

        if self._has_series(df, "gross_margin"):
            ax.plot(df["date"], df["gross_margin"], label="Gross", linewidth=2)
        if self._has_series(df, "operating_margin"):
            ax.plot(df["date"], df["operating_margin"], label="Operating", linewidth=2)
        if self._has_series(df, "net_margin"):
            ax.plot(df["date"], df["net_margin"], label="Net", linewidth=2)

        ax.set_title(title, fontsize=12)
        ax.set_xlabel("Anno")
        ax.set_ylabel("Margine")
        ax.legend(frameon=False)
        ax.tick_params(axis="x", rotation=45)
        ax.grid(True)

        return self._save_fig(fig, f"{ticker}_margins.png")

    # ------------------- 3. Leverage ------------------- #

    def plot_leverage(self, df: pd.DataFrame, ticker: str):
        title = f"{ticker} – Debt/Equity"
        if not self._has_series(df, "debt_to_equity"):
            fig = self._placeholder_fig(title)
            return self._save_fig(fig, f"{ticker}_leverage.png")

        fig, ax = plt.subplots(figsize=(6, 3))
        ax.plot(df["date"], df["debt_to_equity"], linewidth=2)
        ax.set_title(title, fontsize=12)
        ax.set_xlabel("Anno")
        ax.set_ylabel("D/E")
        ax.tick_params(axis="x", rotation=45)
        ax.grid(True)

        return self._save_fig(fig, f"{ticker}_leverage.png")

    # ------------------- 4. Growth ------------------- #

    def plot_growth(self, df: pd.DataFrame, ticker: str):
        title = f"{ticker} – Crescita Ricavi & Utile"
        has_any = any(
            self._has_series(df, col) for col in ["total_revenue", "net_income"]
        )
        if not has_any:
            fig = self._placeholder_fig(title)
            return self._save_fig(fig, f"{ticker}_growth.png")

        fig, ax = plt.subplots(figsize=(6, 3))

        if self._has_series(df, "total_revenue"):
            ax.plot(df["date"], df["total_revenue"], linewidth=2, label="Revenue")
        if self._has_series(df, "net_income"):
            ax.plot(df["date"], df["net_income"], linewidth=2, label="Net Income")

        ax.set_title(title, fontsize=12)
        ax.set_xlabel("Anno")
        ax.set_ylabel("Valore")
        ax.legend(frameon=False)
        ax.tick_params(axis="x", rotation=45)
        ax.grid(True)

        return self._save_fig(fig, f"{ticker}_growth.png")

    # ------------------- 5. Radar Chart Scores ------------------- #

    def plot_scores(self, scores: dict, ticker: str):
        labels = list(scores.keys())
        values = list(scores.values())

        angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
        values += values[:1]
        angles += angles[:1]

        fig = plt.figure(figsize=(5, 5))
        ax = plt.subplot(111, polar=True)

        ax.plot(angles, values, linewidth=2)
        ax.fill(angles, values, alpha=0.15)

        ax.set_yticklabels([])
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(labels)

        ax.set_title(f"{ticker} – Scores Radar", fontsize=12)

        return self._save_fig(fig, f"{ticker}_scores.png")
