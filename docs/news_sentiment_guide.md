# Alpha Vantage新闻情绪分析使用指南

## 📝 第一步：获取 API Key

1. **访问官网**: [Alpha Vantage](https://www.alphavantage.co/support/#api-key)

2. **填写申请表**:
   - 填写用途（选 "Student" 或 "Investor"）
   - 填写邮箱
   - 点击 "Get Free API Key"

3. **获取Key**: 立即在屏幕上看到一串字符（如 `W8X9...`），**复制并保存**

## 🔧 第二步：配置环境

### 安装依赖

```bash
pip install requests
```

### 配置API Key

有两种方式配置：

#### 方式1：环境变量（推荐）

```bash
# 临时设置（当前终端有效）
export ALPHA_VANTAGE_API_KEY=你的Key粘贴在这里

# 永久设置（添加到 ~/.zshrc 或 ~/.bashrc）
echo 'export ALPHA_VANTAGE_API_KEY=你的Key' >> ~/.zshrc
source ~/.zshrc
```

#### 方式2：.env文件

在项目根目录的 `.env` 文件中添加：

```
ALPHA_VANTAGE_API_KEY=你的Key粘贴在这里
```

## 🚀 第三步：运行分析

### 基础用法

```bash
# 分析国际金融市场情绪
python3 scripts/news_sentiment.py

# 指定话题
python3 scripts/news_sentiment.py --topics financial_markets economy_macro

# 分析特定股票
python3 scripts/news_sentiment.py --tickers AAPL MSFT

# 保存结果
python3 scripts/news_sentiment.py --save
```

### 高级用法

```bash
# 中国市场相关
python3 scripts/news_sentiment.py --topics china economy_macro --limit 100

# 科技板块
python3 scripts/news_sentiment.py --topics technology blockchain

# 能源板块
python3 scripts/news_sentiment.py --topics energy oil

# 临时指定API Key
python3 scripts/news_sentiment.py --api-key 你的Key --topics财经
```

## 📊 第四步：解读结果

### 情绪得分解读

**平均情绪得分** (Average Sentiment Score):

- **范围**: -1.0 (极度悲观) 到 1.0 (极度乐观)
- **0 附近**: 市场消息平淡，无明显利好利空
- **> 0.15**: 新闻面明显偏暖 🟢
- **< -0.15**: 新闻面明显偏冷 🔴

### 情绪标签含义

API返回的 `overall_sentiment_label`:

- **Bearish**: 看空 🔴
- **Somewhat-Bearish**: 略微看空 🟠
- **Neutral**: 中性 🟡
- **Somewhat-Bullish**: 略微看多 🟢
- **Bullish**: 看多 🟢🟢

### 输出示例

```
📊 === 情绪分析报告 ===
平均情绪得分: -0.2500 (范围 -1.0 到 1.0)
转换为10分制: 3.75/10

看多: 5 | 看空: 35 | 中性: 10

初步判断: 🔴 情绪悲观 (偏空)

📝 === 这里的文本复制给AI (策略Prompt) ===
今日国际新闻综合情绪得分: -0.25 (🔴 情绪悲观 (偏空))。

关键新闻摘要:
1. [Bearish] Fed signals interest rates may stay high
2. [Somewhat-Bearish] Tech sector slows down amid inflation fears
3. [Neutral] Market volatility continues amid uncertainty
4. [Bearish] Economic data shows slowdown in growth
5. [Somewhat-Bearish] Investors cautious ahead of earnings
```

## 🔄 第五步：集成到策略系统

### 闭环操作流程

1. **运行新闻分析**:
   ```bash
   python3 scripts/news_sentiment.py
   ```

2. **复制输出的"这里的文本复制给AI"部分**

3. **整合到市场环境分析**:

   将新闻情绪自动集成到大盘分析：
   
   ```bash
   # 设置API Key后，市场环境分析会自动包含新闻情绪
   python3 scripts/market_environment.py
   ```

4. **影响策略决策**:

   新闻情绪会影响市场环境评分：
   - **最终评分** = 技术面70% + 新闻面30%
   - 情绪悲观 → 降低市场评分 → 减少仓位
   - 情绪乐观 → 提高市场评分 → 增加仓位

### 策略调整示例

#### 场景1：新闻面悲观 + 技术面弱势

```
技术面评分: 4/10 (阴线下跌)
新闻情绪: 3/10 (悲观)
最终评分: 4*0.7 + 3*0.3 = 3.7/10 🔴红灯

→ 决策: 空仓观望
→ 即使个股符合六维战法，也提高门槛或放弃操作
```

#### 场景2：新闻面乐观 + 技术面强势

```
技术面评分: 9/10 (大阳线放量)
新闻情绪: 8/10 (乐观)
最终评分: 9*0.7 + 8*0.3 = 8.7/10 🟢绿灯

→ 决策: 重仓出击
→ 使用策略A追涨强势股
```

#### 场景3：新闻面分歧 + 技术面震荡

```
技术面评分: 6/10 (小阳线缩量)
新闻情绪: 5/10 (中性)
最终评分: 6*0.7 + 5*0.3 = 5.7/10 🟡黄灯

→ 决策: 半仓精选
→ 只操作高确定性机会，快进快出
```

## 💡 使用技巧

### 1. 选择合适的topics

常用话题：
```python
# 宏观经济
--topics economy_macro financial_markets

# 中国市场
--topics china asia

# 科技板块
--topics technology blockchain artificial_intelligence

# 能源板块
--topics energy oil renewable_energy

# 金融板块
--topics finance banking

# 通胀相关
--topics inflation central_banks
```

### 2. 频率控制

Alpha Vantage免费版限制：
- **每分钟**: 5次请求
- **每天**: 500次请求

建议：
- 每日执行1-2次（开盘前、收盘后）
- 避免在循环中调用
- 使用 `--save` 参数缓存结果

### 3. 结果缓存

```bash
# 保存今日分析
python3 scripts/news_sentiment.py --save

# 读取历史分析
cat data/news_sentiment_2026-02-04.json
```

### 4. 自动化运行

添加到crontab（每日早上8点分析）：

```bash
# 编辑crontab
crontab -e

# 添加任务
0 8 * * * cd /path/to/daily_stock_analysis && python3 scripts/news_sentiment.py --save
```

## ⚠️ 注意事项

1. **API限流**: 免费版有请求限制，不要频繁调用

2. **时差问题**: Alpha Vantage返回的是美国时间的新闻，注意时差

3. **语言限制**: 主要是英文新闻，中文财经新闻需要其他渠道

4. **情绪滞后**: 新闻情绪可能滞后于市场实际反应

5. **权重调整**: 
   - 美股交易时间：新闻权重可提高到50%
   - A股交易时间：技术面权重更重要（70-80%）

## 🔍 故障排查

### 问题1：KeyError或API返回空

```bash
# 检查API Key是否正确
echo $ALPHA_VANTAGE_API_KEY

# 测试API连接
curl "https://www.alphavantage.co/query?function=NEWS_SENTIMENT&topics=technology&apikey=你的Key&limit=5"
```

### 问题2：请求超时

```bash
# 增加超时时间或减少limit
python3 scripts/news_sentiment.py --limit 20
```

### 问题3：API限流

```
⚠️  API提示: Thank you for using Alpha Vantage! 
Our standard API call frequency is 5 calls per minute...
```

解决：等待1分钟后重试，或升级到付费版

## 📚 参考资源

- [Alpha Vantage官方文档](https://www.alphavantage.co/documentation/)
- [News Sentiment API文档](https://www.alphavantage.co/documentation/#news-sentiment)
- [可用话题列表](https://www.alphavantage.co/documentation/#news-sentiment)

---

**最后更新**: 2026-02-04
