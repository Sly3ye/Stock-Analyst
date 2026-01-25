import numpy as np
import pandas as pd


class ValuationEngine:
    """
    Valutazione intrinseca basata su:
    - DCF semplificato
    - Owner Earnings (Buffett-style)
    - Multipli fondamentali

    Regola fondamentale:
    - I modelli possono essere NaN
    - Lo score di valutazione NON può mai essere NaN
    """

    NEUTRAL_SCORE = 50.0

    # -------------------------------------------------
    # UTILS
    # -------------------------------------------------
    @staticmethod
    def _is_valid(x):
        return x is not None and np.isfinite(x)

    @staticmethod
    def _latest_value(series: pd.Series):
        if series is None:
            return np.nan
        clean = series.dropna()
        if clean.empty:
            return np.nan
        return float(clean.iloc[-1])

    def _equity_value_from_enterprise(self, enterprise_value, df: pd.DataFrame):
        if not self._is_valid(enterprise_value):
            return np.nan
        net_debt = self._latest_value(df.get("net_debt"))
        if self._is_valid(net_debt):
            return float(enterprise_value - net_debt)
        return float(enterprise_value)

    def _to_per_share(self, total_value, df: pd.DataFrame):
        shares = self._latest_value(df.get("ordinary_shares_number"))
        if not self._is_valid(total_value) or not self._is_valid(shares) or shares <= 0:
            return np.nan
        return float(total_value / shares)

    def _safe_score(self, values):
        """
        Aggrega valori di valutazione:
        - se nessuno valido → NaN + confidence 0
        - altrimenti media + confidence proporzionale
        """
        valid = [v for v in values if self._is_valid(v)]

        if not valid:
            return np.nan, 0.0

        confidence = len(valid) / len(values)
        return float(np.mean(valid)), confidence

    # -------------------------------------------------
    # 1. NORMALIZED FCF
    # -------------------------------------------------
    def normalized_fcf(self, df: pd.DataFrame):
        fcf = df.get("free_cash_flow")
        if fcf is None:
            return np.nan

        recent = fcf.tail(5)
        if recent.isna().all():
            return np.nan

        return float(recent.mean())

    # -------------------------------------------------
    # 2. GROWTH RATE
    # -------------------------------------------------
    def growth_rate(self, df: pd.DataFrame):
        rev_g = df.get("revenue_cagr_3y")
        fcf_g = df.get("fcf_cagr_3y")

        g_vals = []

        if rev_g is not None and self._is_valid(rev_g.iloc[-1]):
            g_vals.append(rev_g.iloc[-1])

        if fcf_g is not None and self._is_valid(fcf_g.iloc[-1]):
            g_vals.append(fcf_g.iloc[-1])

        if not g_vals:
            return np.nan

        g = float(np.mean(g_vals))
        return float(np.clip(g, 0.02, 0.10))

    # -------------------------------------------------
    # 3. DISCOUNT RATE
    # -------------------------------------------------
    def discount_rate(self, df: pd.DataFrame):
        dta = df.get("debt_to_assets")
        if dta is None or not self._is_valid(dta.iloc[-1]):
            return 0.10  # fallback conservativo

        r = 0.08 + 0.04 * dta.iloc[-1]
        return float(np.clip(r, 0.07, 0.12))

    # -------------------------------------------------
    # 4. DCF MODEL
    # -------------------------------------------------
    def dcf_value(self, df: pd.DataFrame, g=None, r=None, terminal_g=0.02):
        fcf0 = self.normalized_fcf(df)
        g = self.growth_rate(df) if g is None else g
        r = self.discount_rate(df) if r is None else r

        if not self._is_valid(fcf0) or not self._is_valid(g) or r <= g:
            return np.nan

        value = 0.0
        fcf = fcf0

        for t in range(1, 6):
            fcf *= (1 + g)
            value += fcf / ((1 + r) ** t)

        terminal = (fcf * (1 + terminal_g)) / (r - terminal_g)
        value += terminal / ((1 + r) ** 5)

        return float(value)

    # -------------------------------------------------
    # 5. BUFFETT / OWNER EARNINGS
    # -------------------------------------------------
    def buffett_value(self, df: pd.DataFrame, g=None, r=None):
        fcf0 = self.normalized_fcf(df)
        g = self.growth_rate(df) if g is None else g
        r = self.discount_rate(df) if r is None else r

        if not self._is_valid(fcf0) or not self._is_valid(g) or r <= g:
            return np.nan

        return float(fcf0 * (1 + g) / (r - g))

    # -------------------------------------------------
    # 6. MULTIPLES
    # -------------------------------------------------
    def multiples_value(self, df: pd.DataFrame, pe_fair=15):
        ni = df.get("net_income")
        shares = df.get("ordinary_shares_number")

        if ni is None or shares is None:
            return np.nan

        ni_v = ni.iloc[-1]
        sh = shares.iloc[-1]

        if not self._is_valid(ni_v) or sh <= 0:
            return np.nan

        eps = ni_v / sh
        if eps <= 0:
            return np.nan

        return float(eps * pe_fair)

    def _scenario_params(self, df: pd.DataFrame):
        g_base = self.growth_rate(df)
        r_base = self.discount_rate(df)
        return {
            "base": {
                "g": g_base,
                "r": r_base,
                "terminal_g": 0.02,
                "pe": 15,
            },
            "bull": {
                "g": float(np.clip(g_base + 0.02, 0.02, 0.12)) if self._is_valid(g_base) else np.nan,
                "r": float(np.clip(r_base - 0.01, 0.07, 0.12)) if self._is_valid(r_base) else np.nan,
                "terminal_g": 0.03,
                "pe": 18,
            },
            "bear": {
                "g": float(np.clip(g_base - 0.01, 0.00, 0.08)) if self._is_valid(g_base) else np.nan,
                "r": float(np.clip(r_base + 0.01, 0.07, 0.13)) if self._is_valid(r_base) else np.nan,
                "terminal_g": 0.015,
                "pe": 12,
            },
        }

    # -------------------------------------------------
    # 7. SYNTHESIS
    # -------------------------------------------------
    def analyze(self, df: pd.DataFrame):
        """
        Entry point.
        Ritorna valutazioni per-share e confidence.
        """

        params = self._scenario_params(df)

        dcf_total = self.dcf_value(df)
        buffett_total = self.buffett_value(df)
        multiples_ps = self.multiples_value(df)

        dcf_equity = self._equity_value_from_enterprise(dcf_total, df)
        buffett_equity = self._equity_value_from_enterprise(buffett_total, df)

        dcf_ps = self._to_per_share(dcf_equity, df)
        buffett_ps = self._to_per_share(buffett_equity, df)

        # valori per-share (possono essere NaN)
        model_values = [dcf_ps, buffett_ps, multiples_ps]

        fair_value, confidence = self._safe_score(model_values)

        scenarios = {}
        for name, p in params.items():
            dcf_t = self.dcf_value(df, g=p["g"], r=p["r"], terminal_g=p["terminal_g"])
            buffett_t = self.buffett_value(df, g=p["g"], r=p["r"])
            dcf_eq = self._equity_value_from_enterprise(dcf_t, df)
            buffett_eq = self._equity_value_from_enterprise(buffett_t, df)
            dcf_ps = self._to_per_share(dcf_eq, df)
            buffett_ps = self._to_per_share(buffett_eq, df)
            mult_ps = self.multiples_value(df, pe_fair=p["pe"])
            scenario_values = [dcf_ps, buffett_ps, mult_ps]
            scenario_fv, scenario_conf = self._safe_score(scenario_values)
            scenarios[name] = {
                "fair_value": scenario_fv,
                "confidence": scenario_conf,
                "assumptions": {
                    "g": p["g"],
                    "r": p["r"],
                    "terminal_g": p["terminal_g"],
                    "pe": p["pe"],
                },
            }

        return {
            # MODELLI (possono essere NaN)
            "dcf_value": dcf_ps,
            "buffett_value": buffett_ps,
            "multiples_value": multiples_ps,

            # SINTESI
            "fair_value": round(fair_value, 2) if self._is_valid(fair_value) else np.nan,
            "valuation_confidence": confidence,
            "scenarios": scenarios,
        }
