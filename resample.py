import pandas as pd


def resample_ohlcv(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    if df.empty:
        return df
    data = df.copy()
    data = data.sort_values("date")
    data = data.set_index("date")
    agg = {
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }
    resampled = data.resample(rule).agg(agg).dropna(subset=["open", "close"])
    resampled = resampled.reset_index()
    return resampled


def to_weekly(df: pd.DataFrame) -> pd.DataFrame:
    return resample_ohlcv(df, "W-FRI")


def to_monthly(df: pd.DataFrame) -> pd.DataFrame:
    return resample_ohlcv(df, "M")


def to_quarterly(df: pd.DataFrame) -> pd.DataFrame:
    return resample_ohlcv(df, "Q-DEC")
