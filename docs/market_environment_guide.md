# 市场环境分析器使用指南

## 功能说明

自动抓取大盘数据和新闻情绪，生成综合评分报告（0-10分）：
- 🔴 0-4分：红灯 → 空仓观望
- 🟡 5-7分：黄灯 → 半仓精选
- 🟢 8-10分：绿灯 → 重仓出击

## 快速开始

### 1. 基础用法（无新闻API）

```bash
# 分析上证指数
python3 scripts/market_environment.py

# 分析深证成指
python3 scripts/market_environment.py --index 399001.SZ

# 分析沪深300
python3 scripts/market_environment.py --index 000300.SS

# 分析美股
python3 scripts/market_environment.py --index ^GSPC  # 标普500
python3 scripts/market_environment.py --index ^DJI   # 道琼斯
```

### 2. 完整用法（含新闻情绪）

首先配置Alpha Vantage API Key：

```bash
# 1. 获取免费API Key
# 访问: https://www.alphavantage.co/support/#api-key

# 2. 在 .env 文件中添加
echo "ALPHA_VANTAGE_API_KEY=your_key_here" >> .env

# 3. 运行分析
python3 scripts/market_environment.py --topics china economy technology
```

### 3. 常用指数代码

**A股指数**:
- `000001.SS` - 上证指数
- `399001.SZ` - 深证成指
- `399006.SZ` - 创业板指
- `000300.SS` - 沪深300
- `000016.SS` - 上证50
- `000905.SS` - 中证500

**美股指数**:
- `^GSPC` - 标普500
- `^DJI` - 道琼斯工业
- `^IXIC` - 纳斯达克综合

**其他**:
- `^HSI` - 恒生指数
- `^N225` - 日经225

## 评分逻辑

### 技术面评分（0-10分）

1. **涨跌幅** (±3分)
   - 大涨 >2%: +3分
   - 上涨 0.5-2%: +1.5分
   - 微跌小幅震荡: 0分
   - 下跌 -0.5~-2%: -1.5分
   - 大跌 <-2%: -3分

2. **均线位置** (±2分)
   - 多头排列(收盘>MA5>MA20): +2分
   - 站上MA20: +1分
   - 均线纠缠: -1分
   - 空头排列: -2分

3. **K线形态** (±2分)
   - 大阳线(实体>60%): +2分
   - 小阳线: +1分
   - 小阴线: -1分
   - 大阴线: -2分

4. **成交量** (±1分)
   - 放量上涨(>1.3倍): +1分
   - 放量下跌: -1分

### 新闻情绪（0-10分）

- 通过Alpha Vantage分析最新50条新闻
- 情绪范围: -1(极端负面) 到 +1(极端正面)
- 转换为0-10分制

### 综合评分

- 技术面权重: 70%
- 新闻情绪权重: 30%
- 如未配置新闻API，则100%按技术面

## 输出示例

```
======================================================================
📊 市场环境分析报告
======================================================================
📅 日期: 2026-02-04
📈 指数: 000001.SS

---

【📊 市场环境】: 10/10 分 🟢 绿灯

【🌍 技术面评分】: 10/10
   评分依据:
   - 上涨0.85% (+1.5分)
   - 站上MA20 (+1分)
   - 大阳线 (+2分)
   - 放量上涨 (+1分)

【📰 新闻情绪】: 5/10 (未配置API)

【⚖️ 建议仓位】: 重仓出击

---

【📈 指数详情】:
   - 收盘价: 4102.20 (+0.85%)
   - MA5: 4092.32 | MA20: 4092.32
   - K线: 阳线 (实体89.5%)
   - 成交量比: 4.99x

【🛡️ 风控提示】:
   ✅ 市场环境优良，可积极布局
   ✅ 重点关注强势板块龙头
   ⚠️  注意及时止盈，避免追高

======================================================================
```

## Python代码集成

```python
from scripts.market_environment import MarketEnvironmentAnalyzer

# 创建分析器
analyzer = MarketEnvironmentAnalyzer(alpha_vantage_key='your_key')

# 获取指数数据
index_data = analyzer.get_index_data('000001.SS')

# 获取新闻情绪
news_data = analyzer.get_news_sentiment(['china', 'economy'])

# 生成完整报告
report = analyzer.generate_report('000001.SS', ['china', 'market'])
print(report)
```

## 注意事项

1. **数据延迟**: yfinance数据可能有15-20分钟延迟
2. **API限额**: Alpha Vantage免费版限制500次/天
3. **盘前盘后**: 非交易时间获取的是前一交易日数据
4. **网络问题**: 如遇连接失败，请检查网络或稍后重试

## 整合到交易策略

配合之前的"六维真强势"和"黄金坑反弹"策略使用：

1. 先运行环境分析：`python3 scripts/market_environment.py`
2. 根据评分决定仓位：
   - 🟢 绿灯(8-10分): 可追强势股（策略A）
   - 🟡 黄灯(5-7分): 精选个股，快进快出
   - 🔴 红灯(0-4分): 观望或极小仓位抄底（策略B）
3. 再对个股进行六维分析

## 定时任务

可设置cron定时运行：

```bash
# 每天15:30运行（收盘后）
30 15 * * 1-5 cd /path/to/project && python3 scripts/market_environment.py
```
