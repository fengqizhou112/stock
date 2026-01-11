import logging
from dataclasses import dataclass
from typing import List, Optional

import pandas as pd

from data_provider import DataProvider
from indicators import macd, moving_average
from resample import to_monthly, to_quarterly, to_weekly
from rules import (
    RuleResult,
    check_eps_growth,
    check_ma_pattern,
    check_market_value,
    check_month_macd,
    check_quarter_macd,
    check_week_macd,
    is_st_stock,
)


LOGGER = logging.getLogger(__name__)


@dataclass
class ScreenerConfig:
    start_date: str
    end_date: str
    max_mv: float
    zero_near: float
    recent_q_k: int
    month_trend_n: int
    ma_converge_pct: float
    ma_slope_n: int
    use_daily: bool = False


class StockScreener:
    def __init__(self, provider: DataProvider, config: ScreenerConfig) -> None:
        self.provider = provider
        self.config = config

    def screen(self, top_n: Optional[int] = None) -> List[dict]:
        stock_list = self.provider.get_stock_list()
        mv_df = self.provider.get_market_value()
        mv_map = {}
        if mv_df is not None:
            mv_map = mv_df.set_index("code")["total_mv"].to_dict()
        results = []
        for _, row in stock_list.iterrows():
            code = row["code"]
            name = row["name"]
            if is_st_stock(name):
                results.append(self._reject_result(code, name, "ST股票淘汰"))
                continue
            kline = self.provider.get_daily_kline(code, self.config.start_date, self.config.end_date)
            if kline is None or kline.empty:
                results.append(self._reject_result(code, name, "无日线数据"))
                continue
            mv_yi = self._convert_mv_to_yi(mv_map.get(code))
            mv_rule = check_market_value(mv_yi, self.config.max_mv)
            eps_rule, eps_latest, eps_prev = self._eps_rule(code)
            if not mv_rule.passed:
                results.append(self._build_result(code, name, mv_rule, eps_rule, "市值超限"))
                continue
            if not eps_rule.passed:
                results.append(self._build_result(code, name, mv_rule, eps_rule, "EPS未满足"))
                continue
            quarterly = to_quarterly(kline)
            monthly = to_monthly(kline)
            weekly = to_weekly(kline)
            q_macd = macd(quarterly)
            m_macd = macd(monthly)
            w_macd = macd(weekly)
            q_rule = check_quarter_macd(q_macd, self.config.zero_near, self.config.recent_q_k)
            if not q_rule.passed:
                results.append(self._build_result(code, name, mv_rule, eps_rule, q_rule.reason, q_rule))
                continue
            m_rule = check_month_macd(m_macd, self.config.month_trend_n)
            if not m_rule.passed:
                results.append(self._build_result(code, name, mv_rule, eps_rule, m_rule.reason, q_rule, m_rule))
                continue
            w_rule = check_week_macd(w_macd, self.config.zero_near)
            if not w_rule.passed:
                results.append(self._build_result(code, name, mv_rule, eps_rule, w_rule.reason, q_rule, m_rule, w_rule))
                continue
            ma5 = moving_average(kline, 5).iloc[-1]
            ma10 = moving_average(kline, 10).iloc[-1]
            ma20_series = moving_average(kline, 20)
            ma20 = ma20_series.iloc[-1]
            ma_rule = check_ma_pattern(
                ma5,
                ma10,
                ma20,
                ma20_series,
                self.config.ma_converge_pct,
                self.config.ma_slope_n,
            )
            if not ma_rule.passed:
                results.append(
                    self._build_result(code, name, mv_rule, eps_rule, ma_rule.reason, q_rule, m_rule, w_rule, ma_rule)
                )
                continue
            daily_info = {}
            if self.config.use_daily:
                d_macd = macd(kline)
                daily_info = {
                    "daily_dif": float(d_macd["dif"].iloc[-1]),
                    "daily_dea": float(d_macd["dea"].iloc[-1]),
                }
            result = {
                "code": code,
                "name": name,
                "status": "通过",
                "reason": "满足所有条件",
                "market_value_yi": mv_yi,
                "eps_latest": eps_latest,
                "eps_prev": eps_prev,
                "quarter_pass": q_rule.passed,
                "quarter_reason": q_rule.reason,
                "month_pass": m_rule.passed,
                "month_reason": m_rule.reason,
                "week_pass": w_rule.passed,
                "week_reason": w_rule.reason,
                "ma_pass": ma_rule.passed,
                "ma_reason": ma_rule.reason,
                **daily_info,
            }
            self._merge_rule_result(result, "quarter", q_rule)
            self._merge_rule_result(result, "month", m_rule)
            self._merge_rule_result(result, "week", w_rule)
            self._merge_rule_result(result, "ma", ma_rule)
            results.append(result)
        if top_n:
            results = results[:top_n]
        return results

    def _eps_rule(self, code: str) -> tuple[RuleResult, Optional[float], Optional[float]]:
        eps_df = self.provider.get_quarter_eps(code)
        if eps_df is None or eps_df.empty or len(eps_df) < 2:
            return check_eps_growth(None, None), None, None
        eps_df = eps_df.sort_values("report_date")
        eps_latest = float(eps_df["eps"].iloc[-1])
        eps_prev = float(eps_df["eps"].iloc[-2])
        return check_eps_growth(eps_latest, eps_prev), eps_latest, eps_prev

    @staticmethod
    def _convert_mv_to_yi(total_mv: Optional[float]) -> Optional[float]:
        if total_mv is None:
            return None
        try:
            return float(total_mv) / 100000000
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _reject_result(code: str, name: str, reason: str) -> dict:
        return {"code": code, "name": name, "status": "淘汰", "reason": reason}

    def _build_result(
        self,
        code: str,
        name: str,
        mv_rule: RuleResult,
        eps_rule: RuleResult,
        reason: str,
        q_rule: Optional[RuleResult] = None,
        m_rule: Optional[RuleResult] = None,
        w_rule: Optional[RuleResult] = None,
        ma_rule: Optional[RuleResult] = None,
    ) -> dict:
        result = {
            "code": code,
            "name": name,
            "status": "淘汰",
            "reason": reason,
            "market_value_yi": mv_rule.details.get("market_value_yi"),
            "max_mv": mv_rule.details.get("max_mv"),
            "eps_latest": eps_rule.details.get("eps_latest"),
            "eps_prev": eps_rule.details.get("eps_prev"),
            "quarter_pass": q_rule.passed if q_rule else None,
            "quarter_reason": q_rule.reason if q_rule else None,
            "month_pass": m_rule.passed if m_rule else None,
            "month_reason": m_rule.reason if m_rule else None,
            "week_pass": w_rule.passed if w_rule else None,
            "week_reason": w_rule.reason if w_rule else None,
            "ma_pass": ma_rule.passed if ma_rule else None,
            "ma_reason": ma_rule.reason if ma_rule else None,
            **mv_rule.details,
            **eps_rule.details,
        }
        if q_rule:
            self._merge_rule_result(result, "quarter", q_rule)
        if m_rule:
            self._merge_rule_result(result, "month", m_rule)
        if w_rule:
            self._merge_rule_result(result, "week", w_rule)
        if ma_rule:
            self._merge_rule_result(result, "ma", ma_rule)
        return result

    @staticmethod
    def _merge_rule_result(result: dict, prefix: str, rule: RuleResult) -> None:
        for key, value in rule.details.items():
            result[f"{prefix}_{key}"] = value
