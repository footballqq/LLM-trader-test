# 项目进度与使用说明

本页说明：当前已完成内容、如何配置与运行、如何测试，以及后续计划。

## 已完成（本轮新增）
- **测试框架**：pytest 测试套件，覆盖核心模块（portfolio, execution, metrics），23 个测试用例全部通过。
- 架构分层与可插拔接口
  - `market/`：统一 `MarketDataProvider` 接口；`a_share_wind.py`（Wind 分钟线，带 parquet 缓存）；`crypto_binance.py`（Binance 分钟线）。
  - `execution/`：统一 `ExecutionProvider` 接口；`paper_trader.py` 虚拟撮合（滑点/佣金）。
  - `portfolio/`：`PortfolioState` 记录现金、持仓、最新价与成交明细；`metrics.py` 基础统计骨架。
  - `adapters/`：`app_context.py` 读取 YAML 配置并装配 market/execution/portfolio；`llm_prompt_loader.py` 加载 prompt。
  - `ui/`：`dashboard_sections.py` 新的分区渲染（行情、持仓资金、成交记录）。
  - `backtest/`：`engine.py` 简易回放生成权益曲线（骨架）。
- `dashboard.py` 已接入新分区与配置（新增 “Market” 页签，读取 `APP_SETTINGS`）。
  - 新增 “Stats” 页签：
    - 基于 `data/portfolio_state.csv` 的 `total_equity` 计算 1D/1W/1M 回报与最大回撤；
    - 基于 `data/trade_history.csv` 的 `pnl` 计算胜率与赔率（若有成交数据）。
- 依赖：新增 `pyyaml`, `pyarrow`（配置与 parquet 缓存）。
- 脚本：`scripts/generate_mock_data.py` 可生成演示所需的 CSV 数据（非交易时段使用）。

## 你现在可以测试什么
1) 无 Wind 环境可直接打开 Streamlit，看到：
   - Market 分区：若配置为 A股+Wind 无数据时，页面不崩；若换成 crypto+binance，可显示最近 300 根 K 线（分钟）。
   - Portfolio/Trades/AI Activity 分区：继续展示原 CSV 数据的统计与明细（保持兼容）。
2) YAML 配置切换市场与符号；PaperTrader 会随行情更新最新价，持仓/权益面板可以联动（通过 Market 页签中的价格标记）。
3) 非交易时间/无 Wind 场景：通过模拟数据脚本一键演示完整仪表板。

## 如何配置
1) 复制示例配置：
   - 从 `config/settings.example.yaml` 复制为 `config/settings.yaml` 并按需修改。
2) 关键字段：
   - `market.type`: `a_share` 或 `crypto`
   - `market.provider`: A股用 `wind`；加密用 `binance`
   - `symbols`: 符号列表，例如 A股期货 `IF.CFE`，加密 `BTCUSDT`
   - `trading.freq`: 频率，`1m/5m/15m...`
   - `trading.slippage_bps / commission / commission_per_lot`: 滑点与佣金参数
   - `model.prompt`: 指定 prompt 文本路径
   - `storage.data_dir`: 数据目录（也用于 parquet 缓存）
   - `binance.api_key / api_secret`: 若走 Binance，可选填

3) 运行时读取配置的两种方式：
   - 环境变量：设置 `APP_SETTINGS` 指向你的 yaml
   - 默认：未设置时使用 `config/settings.example.yaml`

## 如何运行

### 安装依赖
```bash
pip install -r requirements.txt
```

### 运行测试
```bash
# 运行所有测试
python -m pytest tests/ -v

# 运行特定测试文件
python -m pytest tests/test_portfolio_state.py -v

# 运行测试并查看覆盖率（需要安装 pytest-cov）
python -m pytest tests/ --cov=portfolio --cov=execution --cov=market -v
```
2) 启动 Streamlit 仪表板：
```bash
set APP_SETTINGS=config/settings.yaml  # Windows PowerShell 可改为 $env:APP_SETTINGS
streamlit run dashboard.py
```
3) 切换到加密行情（无需 Wind）：
   - 在 `config/settings.yaml` 中设：
```yaml
market:
  type: crypto
  provider: binance
symbols:
  - BTCUSDT
trading:
  freq: 1m
```

5) 仅用于演示（非交易时段/无行情）
```bash
python scripts/generate_mock_data.py
streamlit run dashboard.py
```

4) 可选开启统一执行桥（将 bot 的交易镜像到 `PaperTrader` 组合）
- 环境变量：
```bash
set USE_EXECUTION_PROVIDER=true  # PowerShell: $env:USE_EXECUTION_PROVIDER="true"
```
- 作用：在不改变原有资金/持仓计算与CSV记录的前提下，将 ENTRY/CLOSE 同步为市场买卖单到 `adapters/app_context.py` 创建的 `PaperTrader`（用于后续统一回测/可视化）。
- 说明：当前为镜像执行，默认关闭，不影响现有逻辑。

## 如何测试（最小手动回放）
1) A股（无 Wind 环境时）：
   - 暂时会显示“无数据”，属于降级行为，页面可正常渲染。
2) 加密：
   - 设为 `crypto/binance` 与 `BTCUSDT`，打开 “Market” 页签应能看到收盘价曲线；
   - 页面会将最新价标记进 `PortfolioState`，你可在持仓分区看到现金/权益（初始100万）。
   - 打开 “Stats” 页签：可查看 1D/1W/1M 回报与最大回撤，以及（若 `trade_history.csv` 含 pnl）胜率与赔率。
3) 非交易时间：
   - 运行 `python scripts/generate_mock_data.py` 生成 `data/*.csv`；
   - 启动仪表板后，Market/Portfolio/Trades/AI/Stats 页面均可展示。
4) 回测骨架：
   - 后续会提供命令行示例，将 `MarketDataProvider + PaperTrader` 与简单决策函数组合生成权益曲线 CSV 供 UI 展示。

## 与上游同步的做法
- 新增代码全部在独立目录与入口薄注入（`build_context()`），尽量不改原函数签名，降低合并冲突。
- 保持原有 CSV 驱动的 Portfolio/Trades/AI 页面，兼顾兼容性与扩展性。

## 下一步计划
1) 将 `bot.py` 的交易决策以最小侵入接到 `ExecutionProvider`，把决策转成 `Order` 并由 `PaperTrader` 执行（仍默认纸上撮合）。
2) 在 `ui` 中加入更多统计：1D/1W/1M 胜率、赔率、回撤等（用 `portfolio/metrics.py`）。
3) 扩展 A股交易日历/会话过滤，完善回测时段过滤逻辑。
4) 提供 `market/crypto_binance.py` 的缓存与限频控制；Wind 拉取加入断点续更。
5) 准备 Streamlit Cloud 指南（包含数据推送到 Git 的最小脚本）。
6) Stats 增强：按周几/小时热力图、持有时长分布、品种分布。
7) 扩展测试覆盖：增加适配层、UI 组件、回测引擎的集成测试。


