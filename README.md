# A股多周期 MACD 选股器

仅面向中国 A 股（上交所/深交所，可选北交所），实现：多周期 MACD + 市值上限 + EPS 增长 + 均线形态的选股工具。

## 功能概览

- **市场范围**：A 股（默认排除北交所，可通过参数开启）
- **指标与规则**：
  - 季度/月份/周线 MACD（季度/月/周为硬条件，日线仅展示）
  - 市值上限（统一换算为“亿元人民币”）
  - EPS 最新季度增长且为正
  - 5/10/20 日均线：汇聚或多头排列
  - 自动排除 ST 股票
- **数据源**：AkShare（无需 token）
- **缓存**：默认 `./cache/` 目录

## 目录结构

```
.
├── main.py
├── data_provider.py
├── resample.py
├── indicators.py
├── rules.py
├── screener.py
├── requirements.txt
├── README.md
└── tests/
```

## 安装

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 运行示例

```bash
python main.py --start-date 20210101 --end-date 20241231 --top-n 20 --out results.csv
```

开启日线展示与北交所支持：

```bash
python main.py --use-daily --include-bj
```

配置月线开口趋势根数：

```bash
python main.py --month-trend-n 3
```

## 输出示例（节选）

```
 code   name status reason  market_value_yi  eps_latest  eps_prev  dif  dea  spread  spread_prev  ma5  ma10  ma20  converge  bull  slope_ok
600000 浦发银行   淘汰  市值超限           2100.5        0.12      0.10  0.12 0.09    0.03        0.02  12.3  12.0  11.8     False  True      True
000001 平安银行   通过 满足所有条件         680.2        0.35      0.28  0.08 0.05    0.03        0.01  14.1  13.8  13.2      True False      True
```

> 注：实际输出字段会包含季度/月/周 MACD 详情、均线判定详情以及淘汰原因。

## 规则说明（简要）

- **季度 MACD**：近 `recent_q_k` 根内金叉；且 DIF 或 DEA 不低于 `-zero_near`。
- **月线 MACD**：DIF/DEA 均在零轴上方且开口扩大（最近 `month_trend_n` 根开口持续放大）。
- **周线 MACD**：DIF 或 DEA 在零轴附近。
- **市值**：总市值换算成“亿元人民币”后 `< max_mv`。
- **EPS**：最新季度 EPS > 0 且 EPS > 上一季度 EPS。
- **均线**：
  - 汇聚：MA5/10/20 两两差距小于 `ma_converge_pct * MA20`。
  - 多头：MA5 > MA10 > MA20 且 MA20 最近 `ma_slope_n` 日上升。

## 字段与单位说明

- AkShare 提供的 `总市值` 为人民币元，程序统一换算为“亿元”。
- EPS 来自 AkShare 的季度财报（如字段名变化，会在控制台提示）。

## 常见问题

- **无数据/停牌**：程序会记录日志并跳过。
- **EPS 字段缺失**：不同接口字段可能调整，必要时可在 `data_provider.py` 中增加字段映射。
- **网络错误**：可重试或删除缓存后重新运行。

## 测试

```bash
pytest -q
```
