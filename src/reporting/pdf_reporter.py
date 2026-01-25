from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Image,
    PageBreak,
    Table,
    TableStyle
)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from pathlib import Path
from .charts import ChartGenerator
import math
import numpy as np


class PDFReporter:
    """
    Equity Research Report – Full version
    Semantically correct handling of NaN, confidence and non-applicable models.
    """

    def __init__(self, output_path="reports"):
        self.output_path = Path(output_path)
        self.output_path.mkdir(parents=True, exist_ok=True)
        self.charts = ChartGenerator()

    # ==========================
    # API PUBBLICA
    # ==========================
    def generate_report(self, ticker, df, info, results):
        pdf_path = self.output_path / f"{ticker}_report.pdf"
        doc = SimpleDocTemplate(str(pdf_path), pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        self._add_title(story, styles, ticker)
        self._add_investment_snapshot(story, styles, info, results)
        self._add_scores_section(story, styles, results, ticker)

        self._add_company_profile(story, styles, info)
        self._add_business_quality_section(story, styles, results)
        self._add_financial_snapshot(story, styles, df)

        self._add_valuation_summary(story, styles, results)
        self._add_valuation_scenarios(story, styles, results)
        self._add_market_expectations_section(story, styles, results)
        self._add_risk_analysis_section(story, styles, results)

        self._add_rating_rationale(story, styles, results)
        self._add_charts_section(story, styles, df, ticker)
        self._add_methods_explained(story, styles, results)
        self._add_disclaimer(story, styles)

        doc.build(story)
        print(f"📄 Report PDF generato: {pdf_path}")

    # ==========================
    # SEZIONI (INVARIATE)
    # ==========================
    def _add_title(self, story, styles, ticker):
        story.append(Paragraph(f"<b>{ticker} – Equity Research Report</b>", styles["Title"]))
        story.append(Paragraph("<font color='#4A4A4A'>Sintesi professionale basata su dati pubblici</font>", styles["Normal"]))
        story.append(Spacer(1, 0.3 * inch))

    def _add_investment_snapshot(self, story, styles, info, results):
        company = (
            info.get("longName")
            or info.get("shortName")
            or info.get("company_name")
            or "N/D"
        )

        q = results.get("quality", {})
        v = results.get("valuation", {})

        story.append(Paragraph("<b>Investment Snapshot</b>", styles["Heading2"]))
        story.append(Spacer(1, 0.1 * inch))

        summary_data = [
            ["Azienda", company],
            ["Settore", info.get("sector", "N/D")],
            ["Industria", info.get("industry", "N/D")],
            ["Prezzo attuale", self._fmt(results.get("current_price"))],
            ["Fair Value stimato", self._fmt(v.get("fair_value"), v.get("valuation_confidence"))],
            ["Upside / Downside", self._fmt_pct(results.get("upside"))],
            ["Rating", results.get("rating", "N/A")],
        ]
        table = Table(summary_data, hAlign="LEFT", colWidths=[2.1 * inch, 3.6 * inch])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F2F2F2")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#222222")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#FAFAFA")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(table)
        story.append(Spacer(1, 0.2 * inch))

        text = """
        Il Fair Value rappresenta una stima del valore intrinseco basata sui
        fondamentali finanziari nel medio-lungo periodo.<br/><br/>

        <b>Cosa significa:</b><br/>
        Prezzo attuale = ultimo prezzo di mercato disponibile.<br/>
        Fair Value = valore per azione stimato dai modelli (DCF, multipli, owner earnings).<br/>
        Upside/Downside = potenziale differenza percentuale tra Fair Value e prezzo attuale.<br/>
        Rating = sintesi qualitativa (BUY/HOLD/SELL) basata su valore, qualita e rischio.
        """
        story.append(Paragraph(text, styles["Normal"]))
        story.append(Spacer(1, 0.35 * inch))

    def _add_scores_section(self, story, styles, results, ticker):
        story.append(Paragraph("<b>Profilo Sintetico – Scorecard</b>", styles["Heading2"]))
        story.append(Spacer(1, 0.2 * inch))

        radar_path = self.charts.plot_scores(
            {
                "Value": results.get("value_score"),
                "Quality": results.get("quality_score"),
                "Growth": results.get("growth_score"),
                "Risk": results.get("risk_score"),
            },
            ticker
        )

        story.append(Image(radar_path, width=5 * inch, height=5 * inch))
        story.append(Spacer(1, 0.3 * inch))
        text = """
        <b>Come leggere la scorecard</b><br/><br/>
        Ogni asse va da 0 a 100: piu alto e meglio.<br/>
        Value riflette la convenienza rispetto al fair value, Quality la qualita del business,<br/>
        Growth la solidita della crescita, Risk il profilo di rischio complessivo.
        """
        story.append(Paragraph(text, styles["Normal"]))
        story.append(Spacer(1, 0.3 * inch))

    def _add_company_profile(self, story, styles, info):
        text = f"""
        <b>Company Overview</b><br/><br/>
        La società opera nel settore {info.get('sector', 'N/A')},
        all’interno dell’industria {info.get('industry', 'N/A')},
        ed è domiciliata in {info.get('country', 'N/A')}.<br/><br/>

        <b>Capitalizzazione di mercato:</b> {self._fmt(info.get('market_cap') or info.get('marketCap'))}<br/>
        <b>Ricavi (TTM):</b> {self._fmt(info.get('revenue_ttm') or info.get('totalRevenue'))}<br/>
        """
        story.append(Paragraph(text, styles["Normal"]))
        story.append(Spacer(1, 0.3 * inch))

    def _add_business_quality_section(self, story, styles, results):
        q = results.get("quality", {})

        story.append(Paragraph("<b>Business Quality Analysis</b>", styles["Heading2"]))
        story.append(Spacer(1, 0.1 * inch))

        quality_rows = [
            ["Indicatore", "Score"],
            ["Quality Score", self._fmt_score(q.get("quality_score"), q.get("quality_confidence"))],
            ["Profitability", self._fmt_score(q.get("profitability_score"), q.get("profitability_confidence"))],
            ["Growth", self._fmt_score(q.get("growth_quality_score"), q.get("growth_confidence"))],
            ["Financial Strength", self._fmt_score(q.get("financial_strength_score"), q.get("financial_strength_confidence"))],
            ["Stability", self._fmt_score(q.get("stability_score"), q.get("stability_confidence"))],
        ]
        table = Table(quality_rows, hAlign="LEFT", colWidths=[2.4 * inch, 3.3 * inch])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F2F6FF")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1F3A6F")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#FFFFFF")),
        ]))
        story.append(table)
        story.append(Spacer(1, 0.2 * inch))

        text = """
        <b>Descrizioni semplici</b><br/>
        Quality Score = media delle dimensioni sotto (serve per un giudizio complessivo).<br/>
        Profitability = margini e redditivita: quanto guadagna l'azienda sui ricavi.<br/>
        Growth = crescita di ricavi e utili/cash flow nel tempo.<br/>
        Financial Strength = leva e liquidita: quanto l'azienda e solida finanziariamente.<br/>
        Stability = regolarita degli utili e dei margini nel tempo.
        """
        story.append(Paragraph(text, styles["Normal"]))
        story.append(Spacer(1, 0.3 * inch))

    def _add_financial_snapshot(self, story, styles, df):
        latest = df.iloc[-1]
        dte = latest.get("debt_to_equity")
        dta = latest.get("debt_to_assets")
        if dte is not None and isinstance(dte, float) and math.isnan(dte):
            dte = None
        if dta is not None and isinstance(dta, float) and math.isnan(dta):
            dta = None
        if dte is not None:
            leverage_label = "Debt / Equity"
            leverage_value = self._fmt(dte)
        elif dta is not None:
            leverage_label = "Debt / Assets"
            leverage_value = self._fmt(dta)
        else:
            leverage_label = "Debt / Equity"
            leverage_value = "N/D"

        story.append(Paragraph("<b>Financial Performance</b>", styles["Heading2"]))
        story.append(Spacer(1, 0.1 * inch))

        perf_rows = [
            ["Metrica", "Valore"],
            ["Ricavi", self._fmt(latest.get("total_revenue"))],
            ["Margine operativo", self._fmt_pct(latest.get("operating_margin"))],
            ["Margine netto", self._fmt_pct(latest.get("net_margin"))],
            ["Free Cash Flow", self._fmt(latest.get("free_cash_flow"))],
            ["ROE", self._fmt_pct(latest.get("roe"))],
            [leverage_label, leverage_value],
        ]
        table = Table(perf_rows, hAlign="LEFT", colWidths=[2.4 * inch, 3.3 * inch])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F7F7F7")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#333333")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#FFFFFF")),
        ]))
        story.append(table)
        story.append(Spacer(1, 0.2 * inch))

        text = f"""
        <b>Descrizioni semplici</b><br/>
        Ricavi = vendite totali dell'azienda.<br/>
        Margine operativo = profitto operativo / ricavi (efficienza del core business).<br/>
        Margine netto = utile netto / ricavi (profitto finale).<br/>
        Free Cash Flow = cassa generata dopo investimenti; base per la valutazione DCF.<br/>
        ROE = utile netto / patrimonio netto (non applicabile se equity negativo).<br/>
        {leverage_label} = misura della leva finanziaria (debito rispetto a equity o asset).
        """
        story.append(Paragraph(text, styles["Normal"]))
        story.append(Spacer(1, 0.3 * inch))

    def _add_valuation_summary(self, story, styles, results):
        v = results.get("valuation", {})

        story.append(Paragraph("<b>Valuation Analysis</b>", styles["Heading2"]))
        story.append(Spacer(1, 0.1 * inch))

        val_rows = [
            ["Modello", "Valore per azione"],
            ["DCF", self._fmt(v.get("dcf_value"), v.get("valuation_confidence"))],
            ["Multipli", self._fmt(v.get("multiples_value"), v.get("valuation_confidence"))],
            ["Buffett-style", self._fmt(v.get("buffett_value"), v.get("valuation_confidence"))],
        ]
        table = Table(val_rows, hAlign="LEFT", colWidths=[2.4 * inch, 3.3 * inch])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F2F6FF")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1F3A6F")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#FFFFFF")),
        ]))
        story.append(table)
        story.append(Spacer(1, 0.2 * inch))

        text = """
        <b>Descrizioni semplici</b><br/>
        DCF = valore basato sui flussi di cassa futuri scontati a oggi.<br/>
        Multipli = valore per azione ottenuto applicando un P/E "fair" agli utili.<br/>
        Buffett-style = owner earnings perpetui (variante semplificata del DCF).
        """
        story.append(Paragraph(text, styles["Normal"]))
        story.append(Spacer(1, 0.3 * inch))

    def _add_valuation_scenarios(self, story, styles, results):
        scenarios = results.get("valuation", {}).get("scenarios", {})
        if not scenarios:
            return

        def fmt_assumptions(s):
            a = s.get("assumptions", {})
            return (
                f"g={self._fmt_pct(a.get('g'))}, "
                f"r={self._fmt_pct(a.get('r'))}, "
                f"gT={self._fmt_pct(a.get('terminal_g'))}, "
                f"PE={a.get('pe', 'N/D')}"
            )

        rows = []
        for key in ["bear", "base", "bull"]:
            s = scenarios.get(key)
            if not s:
                continue
            fv = self._fmt(s.get("fair_value"), s.get("confidence"))
            rows.append(f"<b>{key.title()}:</b> {fv}<br/>{fmt_assumptions(s)}<br/>")

        text = """
        <b>Valuation Scenarios</b><br/><br/>
        """
        text += "<br/>".join(rows)
        text += """
        <br/><br/><b>Come leggere gli scenari</b><br/>
        Bear = ipotesi piu conservative, Base = ipotesi centrali, Bull = ipotesi piu ottimistiche.
        """

        story.append(Paragraph(text, styles["Normal"]))
        story.append(Spacer(1, 0.3 * inch))

    def _add_market_expectations_section(self, story, styles, results):
        market = results.get("market", {})
        returns = market.get("returns", {}) or {}
        story.append(Paragraph("<b>Market Snapshot</b>", styles["Heading2"]))
        story.append(Spacer(1, 0.1 * inch))

        market_rows = [
            ["Indicatore", "Valore"],
            ["Volatilita (ann.)", self._fmt_pct(market.get("volatility"))],
            ["Max Drawdown", self._fmt_pct(market.get("max_drawdown"))],
            ["Rendimento 1Y", self._fmt_pct(returns.get("1Y"))],
            ["Rendimento 3Y", self._fmt_pct(returns.get("3Y"))],
            ["Rendimento 5Y", self._fmt_pct(returns.get("5Y"))],
        ]
        table = Table(market_rows, hAlign="LEFT", colWidths=[2.4 * inch, 3.3 * inch])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F7F7F7")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#333333")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#FFFFFF")),
        ]))
        story.append(table)
        story.append(Spacer(1, 0.2 * inch))

        text = """
        <b>Descrizioni semplici</b><br/>
        Volatilita = quanto il prezzo oscilla nel tempo (piu alto = piu rischio).<br/>
        Max Drawdown = peggior calo dal massimo al minimo (misura i periodi difficili).<br/>
        Rendimenti = performance storica a 1/3/5 anni.
        """
        story.append(Paragraph(text, styles["Normal"]))
        story.append(Spacer(1, 0.3 * inch))

    def _add_risk_analysis_section(self, story, styles, results):
        text = f"""
        <b>Risk Analysis</b><br/><br/>
        <b>Risk Score:</b> {self._fmt_score(results.get("risk_score"))}<br/>

        <br/><b>Descrizione</b><br/>
        Il Risk Score considera volatilita storica e sopravvalutazione: piu alto = rischio minore.
        """
        story.append(Paragraph(text, styles["Normal"]))
        story.append(Spacer(1, 0.3 * inch))

    def _add_rating_rationale(self, story, styles, results):
        text = f"""
        <b>Final Rating & Investment Thesis</b><br/><br/>
        Il rating (<b>{results.get("rating", "N/A")}</b>) deriva da una
        valutazione combinata di valore, qualità e rischio.<br/><br/>
        <b>Interpretazione semplice:</b><br/>
        BUY = titolo appare sottovalutato con buona qualita.<br/>
        HOLD = valutazione in linea con i fondamentali.<br/>
        SELL = titolo appare sopravvalutato o con rischio elevato.
        """
        story.append(Paragraph(text, styles["Normal"]))
        story.append(Spacer(1, 0.4 * inch))

    def _add_charts_section(self, story, styles, df, ticker):
        story.append(PageBreak())
        story.append(Paragraph("<b>Grafici Finanziari</b>", styles["Title"]))
        story.append(Spacer(1, 0.3 * inch))

        charts = [
            (self.charts.plot_fcf(df, ticker),
             "Free Cash Flow: misura la cassa generata dopo investimenti."),
            (self.charts.plot_margins(df, ticker),
             "Margini: confronto tra margine lordo, operativo e netto nel tempo."),
            (self.charts.plot_leverage(df, ticker),
             "Leverage: rapporto debito/equity (o debito/assets) nel tempo."),
            (self.charts.plot_growth(df, ticker),
             "Crescita: andamento di ricavi e utile netto."),
        ]

        for chart, caption in charts:
            story.append(Image(chart, width=6 * inch, height=3 * inch))
            story.append(Spacer(1, 0.05 * inch))
            story.append(Paragraph(f"<font color='#4A4A4A'>{caption}</font>", styles["Normal"]))
            story.append(Spacer(1, 0.25 * inch))

    def _add_methods_explained(self, story, styles, results):
        q_conf = results.get("quality", {}).get("quality_confidence")
        v_conf = results.get("valuation", {}).get("valuation_confidence")
        r_conf = results.get("rating_confidence")
        scenarios = results.get("valuation", {}).get("scenarios", {})
        base_assumptions = scenarios.get("base", {}).get("assumptions", {})

        def fmt_conf(value):
            if value is None or (isinstance(value, float) and math.isnan(value)):
                return "N/D"
            return f"{value * 100:.0f}%"

        text = """
        <b>Metodologia</b><br/><br/>
        Le valutazioni si basano su modelli finanziari standard
        applicati a dati storici pubblici.
        """
        if base_assumptions:
            text += f"""
            <br/><b>Assunzioni base (valuation)</b><br/>
            g={self._fmt_pct(base_assumptions.get('g'))},
            r={self._fmt_pct(base_assumptions.get('r'))},
            gT={self._fmt_pct(base_assumptions.get('terminal_g'))},
            PE={base_assumptions.get('pe', 'N/D')}<br/>
            """
        text += f"""
        <br/><b>Data Coverage</b><br/>
        Qualità: {fmt_conf(q_conf)}<br/>
        Valuation: {fmt_conf(v_conf)}<br/>
        Rating: {fmt_conf(r_conf)}<br/>
        """
        story.append(Paragraph(text, styles["Normal"]))
        story.append(Spacer(1, 0.3 * inch))

    def _add_disclaimer(self, story, styles):
        text = """
        <b>Disclaimer</b><br/><br/>
        Questa analisi ha esclusivamente finalità informative.
        """
        story.append(Paragraph(text, styles["Normal"]))

    # ==========================
    # FORMAT UTILS (CORRETTE)
    # ==========================
    @staticmethod
    def _fmt(value, confidence=None, applicable=True):
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return "N/A (not applicable)" if not applicable else "N/D"
        txt = f"{value:,.2f}"
        if confidence is not None and confidence < 0.4:
            txt += " ⚠ low confidence"
        return txt

    @staticmethod
    def _fmt_pct(value, confidence=None, applicable=True):
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return "N/A (not applicable)" if not applicable else "N/D"
        txt = f"{value * 100:.1f}%"
        if confidence is not None and confidence < 0.4:
            txt += " ⚠ low confidence"
        return txt

    @staticmethod
    def _fmt_score(value, confidence=None):
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return "N/D"
        txt = f"{value:.0f} / 100"
        if confidence is not None and confidence < 0.4:
            txt += " ⚠ low confidence"
        return txt
