from dataclasses import dataclass
from typing import Optional

import pandas as pd


@dataclass
class RuleResult:
    passed: bool
    reason: str
    details: dict


def is_st_stock(name: str) -> bool:
    return "ST" in name.upper()


def check_market_value(mv_yi: Optional[float], max_mv: float) -> RuleResult:
    if mv_yi is None:
        return RuleResult(False, "市值数据缺失", {"market_value_yi": None})
    passed = mv_yi < max_mv
    reason = "市值符合" if passed else "市值超限"
    return RuleResult(passed, reason, {"market_value_yi": mv_yi, "max_mv": max_mv})


def check_eps_growth(eps_latest: Optional[float], eps_prev: Optional[float]) -> RuleResult:
    if eps_latest is None or eps_prev is None:
        return RuleResult(False, "EPS数据缺失", {"eps_latest": eps_latest, "eps_prev": eps_prev})
    passed = eps_latest > 0 and eps_latest > eps_prev
    reason = "EPS增长且为正" if passed else "EPS未满足增长/为正"
    return RuleResult(passed, reason, {"eps_latest": eps_latest, "eps_prev": eps_prev})


def _find_recent_golden_cross(dif: pd.Series, dea: pd.Series, recent_k: int) -> Optional[int]:
    if len(dif) < 2:
        return None
    for idx in range(1, min(len(dif), recent_k + 1)):
        current = -idx
        previous = current - 1
        if dif.iloc[previous] <= dea.iloc[previous] and dif.iloc[current] > dea.iloc[current]:
            return idx
    return None


def check_quarter_macd(macd_df: pd.DataFrame, zero_near: float, recent_k: int) -> RuleResult:
    if macd_df.empty:
        return RuleResult(False, "季度MACD数据缺失", {})
    dif = macd_df["dif"]
    dea = macd_df["dea"]
    recent_cross = _find_recent_golden_cross(dif, dea, recent_k)
    if recent_cross is None:
        return RuleResult(False, "季度未在近N根金叉", {"recent_cross": None})
    current_idx = -recent_cross
    dif_val = dif.iloc[current_idx]
    dea_val = dea.iloc[current_idx]
    zero_ok = dif_val >= -zero_near or dea_val >= -zero_near
    passed = zero_ok
    reason = "季度金叉" if passed else "季度金叉但零轴过低"
    return RuleResult(
        passed,
        reason,
        {"dif": dif_val, "dea": dea_val, "recent_cross": recent_cross, "zero_near": zero_near},
    )


def check_month_macd(macd_df: pd.DataFrame, trend_n: int) -> RuleResult:
    if macd_df.empty:
        return RuleResult(False, "月线MACD数据缺失", {})
    if trend_n < 1:
        trend_n = 1
    dif_series = macd_df["dif"]
    dea_series = macd_df["dea"]
    spread_series = dif_series - dea_series
    if len(spread_series) < max(2, trend_n):
        return RuleResult(False, "月线MACD数据不足", {})
    dif = dif_series.iloc[-1]
    dea = dea_series.iloc[-1]
    spread = spread_series.iloc[-1]
    spread_prev = spread_series.iloc[-2]
    trend_slice = spread_series.tail(trend_n)
    trend_ok = trend_slice.diff().dropna().gt(0).all() if trend_n > 1 else spread > spread_prev
    passed = dif > 0 and dea > 0 and trend_ok
    reason = "月线零轴上开口扩大" if passed else "月线未满足零轴上开口"
    return RuleResult(
        passed,
        reason,
        {
            "dif": dif,
            "dea": dea,
            "spread": spread,
            "spread_prev": spread_prev,
            "trend_n": trend_n,
            "trend_ok": trend_ok,
        },
    )


def check_week_macd(macd_df: pd.DataFrame, zero_near: float) -> RuleResult:
    if macd_df.empty:
        return RuleResult(False, "周线MACD数据缺失", {})
    dif_val = macd_df["dif"].iloc[-1]
    dea_val = macd_df["dea"].iloc[-1]
    passed = dif_val >= -zero_near or dea_val >= -zero_near
    reason = "周线零轴附近" if passed else "周线零轴过低"
    return RuleResult(passed, reason, {"dif": dif_val, "dea": dea_val, "zero_near": zero_near})


def check_ma_pattern(
    ma5: float,
    ma10: float,
    ma20: float,
    ma20_series: pd.Series,
    ma_converge_pct: float,
    ma_slope_n: int,
) -> RuleResult:
    if pd.isna(ma5) or pd.isna(ma10) or pd.isna(ma20):
        return RuleResult(False, "均线数据不足", {"ma5": ma5, "ma10": ma10, "ma20": ma20})
    converge_threshold = ma20 * ma_converge_pct
    converge = (
        abs(ma5 - ma10) <= converge_threshold
        and abs(ma5 - ma20) <= converge_threshold
        and abs(ma10 - ma20) <= converge_threshold
    )
    slope_series = ma20_series.dropna()
    slope_ok = False
    if len(slope_series) >= ma_slope_n:
        slope_ok = slope_series.iloc[-1] > slope_series.iloc[-ma_slope_n]
    bull = ma5 > ma10 > ma20 and slope_ok
    passed = converge or bull
    reason = "均线汇聚" if converge else "均线多头排列" if bull else "均线不满足"
    return RuleResult(
        passed,
        reason,
        {
            "ma5": ma5,
            "ma10": ma10,
            "ma20": ma20,
            "converge": converge,
            "bull": bull,
            "slope_ok": slope_ok,
        },
    )
