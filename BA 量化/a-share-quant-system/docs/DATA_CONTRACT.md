# 数据接入契约

数据目录支持同名 Parquet 或 CSV；生产研究推荐 Parquet。所有表必须来自同一可追溯快照。

## securities

必需字段：

- security_id：系统内稳定证券标识；
- symbol；
- exchange；
- board：main、chinext 或 star；
- industry：当时可知的行业分类；
- list_date。

可选字段包括 delist_date 和历史代码映射。不能用当前行业分类覆盖历史。

## bars

主键为 security_id 与 trade_date。必需字段：

- open_raw、high_raw、low_raw、close_raw、prev_close_raw；
- volume、amount；
- adjust_factor；
- limit_up_price、limit_down_price；
- is_suspended、is_risk_warning、is_delisting；
- market_cap、float_market_cap。

原始价格用于成交和账本，复权价格只用于收益与信号。high 必须不小于其他 OHLC，low 必须不大于其他 OHLC，adjust_factor 必须为正。

## fundamentals

至少包含 security_id、report_period 和 available_time。available_time 是系统可以使用该记录的最早时点，而不是报告期末。建议同时保留 announcement_time、revision_time 和数据源版本。

系统对指定 as_of 只选择 available_time 不晚于 as_of 的最新记录。

## benchmark

包含 trade_date 和 close。缺失时市场状态可使用股票等权代理，但正式 Gate 应提供固定基准。

## corporate_actions

包含 security_id 和 ex_date。支持：

- cash_dividend_per_share；
- split_ratio。

账本在除权日先处理公司行动，再执行当日交易。

## 时间与快照

- 日期按 Asia/Shanghai 交易日解释；
- 收盘后信号最早在下一交易日成交；
- 数据目录一旦用于正式实验应只读；
- DatasetBundle 会生成内容指纹，实验 manifest 同时记录配置与数据哈希。

## RQData 映射

正式适配器位于 `src/a_share_quant/data/rqdata_adapter.py`，通过
`a-share-quant sync-rqdata` 调用。映射原则如下：

- `get_price(adjust_type="none")` 只用于成交、涨跌停和账本；
- `get_price(adjust_type="pre")` 只用于计算复权因子和信号；
- `is_suspended`、`is_st_stock` 保存每日历史状态；
- `get_shares` 与未复权收盘价生成总市值和流通市值；
- `get_factor` 按月末交易日生成点时快照并落入 `available_time`，回测只允许
  向后查找，避免传输完整日频财务因子造成不必要的数据成本；
- `get_instrument_industry` 保存历史行业快照，不以当前行业覆盖过去；
- `get_dividend` 和 `get_split` 映射至除权日公司行动；
- `index_components` 使用整个同步区间的历史成分股并集，避免只使用当前成分股。

RQData 认证由客户端本机配置管理，用户名、密码、令牌不得进入配置、日志、
数据快照或实验 manifest。
