import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd

try:
    import akshare as ak
except ImportError:  # pragma: no cover - dependency availability handled at runtime
    ak = None


LOGGER = logging.getLogger(__name__)


@dataclass
class DataProviderConfig:
    cache_dir: Path = Path("./cache")
    include_bj: bool = False


class DataProvider:
    def __init__(self, config: Optional[DataProviderConfig] = None) -> None:
        self.config = config or DataProviderConfig()
        self.config.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, key: str) -> Path:
        safe_key = key.replace("/", "_")
        return self.config.cache_dir / f"{safe_key}.csv"

    def _load_cache(self, key: str) -> Optional[pd.DataFrame]:
        path = self._cache_path(key)
        if path.exists():
            try:
                return pd.read_csv(path)
            except Exception as exc:  # pragma: no cover - cache corruption
                LOGGER.warning("Failed to read cache %s: %s", path, exc)
        return None

    def _save_cache(self, key: str, df: pd.DataFrame) -> None:
        path = self._cache_path(key)
        try:
            df.to_csv(path, index=False)
        except Exception as exc:  # pragma: no cover - disk issues
            LOGGER.warning("Failed to write cache %s: %s", path, exc)

    def get_stock_list(self) -> pd.DataFrame:
        if ak is None:
            raise RuntimeError("AkShare is not installed. Please install requirements.")
        cached = self._load_cache("stock_list")
        if cached is not None:
            return cached
        df = ak.stock_info_a_code_name()
        df = df.rename(columns={"code": "code", "name": "name"})
        df = df[df["name"].notna()]
        df = df[~df["name"].str.contains("ST", na=False)]
        df = df[df["code"].str.match(r"^\d{6}$")]
        if self.config.include_bj:
            df = df[df["code"].str.startswith(("0", "3", "6", "8"))]
        else:
            df = df[df["code"].str.startswith(("0", "3", "6"))]
        self._save_cache("stock_list", df)
        return df

    def get_daily_kline(self, code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        if ak is None:
            raise RuntimeError("AkShare is not installed. Please install requirements.")
        key = f"daily_{code}_{start_date}_{end_date}"
        cached = self._load_cache(key)
        if cached is not None and not cached.empty:
            cached["date"] = pd.to_datetime(cached["date"])
            return cached
        symbol = self._to_ak_symbol(code)
        try:
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="",
            )
        except Exception as exc:
            LOGGER.warning("Failed to fetch daily kline for %s: %s", code, exc)
            return None
        if df is None or df.empty:
            return None
        df = df.rename(
            columns={
                "日期": "date",
                "开盘": "open",
                "收盘": "close",
                "最高": "high",
                "最低": "low",
                "成交量": "volume",
            }
        )
        df = df[["date", "open", "high", "low", "close", "volume"]]
        df["date"] = pd.to_datetime(df["date"])
        self._save_cache(key, df)
        return df

    def get_market_value(self) -> Optional[pd.DataFrame]:
        if ak is None:
            raise RuntimeError("AkShare is not installed. Please install requirements.")
        cached = self._load_cache("market_value")
        if cached is not None:
            return cached
        try:
            df = ak.stock_zh_a_spot_em()
        except Exception as exc:
            LOGGER.warning("Failed to fetch market value data: %s", exc)
            return None
        if df is None or df.empty:
            return None
        df = df.rename(columns={"代码": "code", "名称": "name", "总市值": "total_mv"})
        df = df[["code", "name", "total_mv"]]
        self._save_cache("market_value", df)
        return df

    def get_quarter_eps(self, code: str) -> Optional[pd.DataFrame]:
        if ak is None:
            raise RuntimeError("AkShare is not installed. Please install requirements.")
        key = f"eps_{code}"
        cached = self._load_cache(key)
        if cached is not None and not cached.empty:
            return cached
        symbol = self._to_ak_symbol(code)
        try:
            df = ak.stock_financial_report_sina(stock=symbol)
        except Exception as exc:
            LOGGER.warning("Failed to fetch EPS for %s: %s", code, exc)
            return None
        if df is None or df.empty:
            return None
        df = df.rename(columns={"报告期": "report_date", "每股收益": "eps"})
        if "eps" not in df.columns:
            candidates = [col for col in df.columns if "每股收益" in col or "EPS" in col]
            if candidates:
                df = df.rename(columns={candidates[0]: "eps"})
        df = df[["report_date", "eps"]]
        df = df.dropna(subset=["eps"])
        self._save_cache(key, df)
        return df

    @staticmethod
    def _to_ak_symbol(code: str) -> str:
        if code.startswith("6"):
            return f"sh{code}"
        return f"sz{code}"
