import pandas as pd

from resample import to_quarterly


def test_quarterly_resample():
    dates = pd.date_range("2024-01-01", periods=6, freq="MS")
    df = pd.DataFrame(
        {
            "date": dates,
            "open": [1, 2, 3, 4, 5, 6],
            "high": [2, 3, 4, 5, 6, 7],
            "low": [1, 2, 3, 4, 5, 6],
            "close": [1.5, 2.5, 3.5, 4.5, 5.5, 6.5],
            "volume": [10, 10, 10, 10, 10, 10],
        }
    )
    quarterly = to_quarterly(df)
    assert len(quarterly) == 2
    assert quarterly.loc[0, "open"] == 1
    assert quarterly.loc[0, "close"] == 3.5
    assert quarterly.loc[0, "volume"] == 30
