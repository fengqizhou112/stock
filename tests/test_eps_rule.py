from rules import check_eps_growth


def test_eps_growth_positive():
    result = check_eps_growth(0.8, 0.5)
    assert result.passed


def test_eps_growth_negative():
    result = check_eps_growth(-0.1, 0.2)
    assert not result.passed
