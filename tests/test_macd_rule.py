import pandas as pd

from rules import check_quarter_macd


def test_quarter_macd_recent_cross():
    data = pd.DataFrame(
        {
            "dif": [-0.2, -0.1, 0.05],
            "dea": [-0.1, -0.05, 0.0],
        }
    )
    result = check_quarter_macd(data, zero_near=0.05, recent_k=2)
    assert result.passed
    assert result.details["recent_cross"] == 1
