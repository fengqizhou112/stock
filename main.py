import argparse
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from data_provider import DataProvider, DataProviderConfig
from screener import ScreenerConfig, StockScreener


def _default_start_end():
    end = datetime.today().date()
    start = end - timedelta(days=365 * 3)
    return start.strftime("%Y%m%d"), end.strftime("%Y%m%d")


def parse_args() -> argparse.Namespace:
    start_default, end_default = _default_start_end()
    parser = argparse.ArgumentParser(description="A股多周期MACD选股器")
    parser.add_argument("--start-date", default=start_default, help="开始日期 YYYYMMDD")
    parser.add_argument("--end-date", default=end_default, help="结束日期 YYYYMMDD")
    parser.add_argument("--max-mv", type=float, default=1000, help="最大市值(亿元)")
    parser.add_argument("--zero-near", type=float, default=0.05, help="零轴附近阈值")
    parser.add_argument("--recent-q-k", type=int, default=2, help="季度金叉最近K数")
    parser.add_argument("--month-trend-n", type=int, default=2, help="月线MACD开口趋势根数")
    parser.add_argument("--ma-converge-pct", type=float, default=0.015, help="均线汇聚阈值")
    parser.add_argument("--ma-slope-n", type=int, default=20, help="均线斜率观察期")
    parser.add_argument("--top-n", type=int, default=50, help="输出前N只股票")
    parser.add_argument("--out", default=None, help="输出CSV/JSON文件路径")
    parser.add_argument("--use-daily", action="store_true", help="输出日线MACD信息")
    parser.add_argument("--include-bj", action="store_true", help="包含北交所股票")
    return parser.parse_args()


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def save_output(results: list[dict], output_path: str) -> None:
    path = Path(output_path)
    if path.suffix.lower() == ".json":
        path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        pd.DataFrame(results).to_csv(path, index=False)


def main() -> None:
    args = parse_args()
    setup_logging()
    provider = DataProvider(DataProviderConfig(include_bj=args.include_bj))
    config = ScreenerConfig(
        start_date=args.start_date,
        end_date=args.end_date,
        max_mv=args.max_mv,
        zero_near=args.zero_near,
        recent_q_k=args.recent_q_k,
        month_trend_n=args.month_trend_n,
        ma_converge_pct=args.ma_converge_pct,
        ma_slope_n=args.ma_slope_n,
        use_daily=args.use_daily,
    )
    screener = StockScreener(provider, config)
    results = screener.screen(top_n=args.top_n)
    df = pd.DataFrame(results)
    print(df.to_string(index=False))
    if args.out:
        save_output(results, args.out)


if __name__ == "__main__":
    main()
