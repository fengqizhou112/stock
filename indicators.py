import pandas as pd


def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    close = df["close"].astype(float)
    dif = ema(close, fast) - ema(close, slow)
    dea = ema(dif, signal)
    hist = (dif - dea) * 2
    result = df.copy()
    result["dif"] = dif
    result["dea"] = dea
    result["hist"] = hist
    return result


def moving_average(df: pd.DataFrame, window: int) -> pd.Series:
    return df["close"].rolling(window=window).mean()
