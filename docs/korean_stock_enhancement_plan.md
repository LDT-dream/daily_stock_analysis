# 韩国股票分析能力增强方案

## 当前状态

| 分析维度 | SK海力士 (韩国) | A股股票 | 可行性 |
|---------|----------------|---------|--------|
| 实时行情 | ✅ | ✅ | 已完成 |
| 历史K线 | ✅ | ✅ | 已完成 |
| 技术指标 | ✅ | ✅ | 已完成 |
| 筹码分布 | ❌ | ✅ | 韩国市场无此概念 |
| 新闻情报 | ❌ | ✅ | 需配置 Finnhub API |
| 资金流向 | ❌ | ✅ | pykrx 有数据但有编码问题 |
| 基本面 | ⚠️ 部分 | ✅ | yfinance 提供部分数据 |

## 可实现的增强方案

### 1. 新闻情报 (推荐)

**方案**: 使用 Finnhub API (免费)

- 注册: https://finnhub.io
- 免费额度: 60 API calls/分钟
- 支持: 公司新闻、财报、分析师评级
- 配置: 在 `.env` 添加 `FINNHUB_API_KEY=your_key`

**Finnhub 提供的韩国股票数据**:
- 公司新闻 (最近90天)
- 财报日历
- 分析师推荐
- 内部人交易

### 2. 基本面数据 (推荐)

**方案**: 增强 yfinance 数据提取

yfinance 已提供:
- 市值 (Market Cap)
- 股息率 (Dividend Yield)
- 52周高低
- Beta 系数
- 行业/板块

可补充:
- 使用 `finance-datareader` 获取更多财务指标
- 使用 DART API 获取详细财报 (需注册)

### 3. 资金流向 (可选)

**方案**: pykrx 外资/机构交易数据

pykrx 提供:
- 外资净买入/卖出
- 机构净买入/卖出
- 个人投资者交易数据

**问题**: pykrx 在 Windows 上有编码问题，需要修复

### 4. 筹码分布 (不可行)

**原因**: 筹码分布是中国 A 股特有的概念，基于东方财富的持仓成本数据。韩国市场没有 equivalent 数据源。

**替代方案**: 可以提供:
- 机构持仓比例 (通过 DART 公开信息)
- 外资持股比例 (通过 KRX 数据)

## 实施建议

### 优先级 1: 新闻情报
1. 注册 Finnhub API (免费)
2. 在 `.env` 添加 API key
3. 系统已支持 Finnhub，无需代码改动

### 优先级 2: 基本面增强
1. 在 `KoreaFinanceFetcher` 中添加更多 yfinance 数据提取
2. 添加 DART API 集成 (需注册免费 API key)

### 优先级 3: 资金流向
1. 修复 pykrx 编码问题
2. 添加外资/机构交易数据接口

## 参考资源

- [Finnhub API 文档](https://finnhub.io/docs/api)
- [DART Open API](https://opendart.fss.or.kr)
- [pykrx GitHub](https://github.com/sharebook-kr/pykrx)
- [FinanceDataReader GitHub](https://github.com/FinanceData/FinanceDataReader)
