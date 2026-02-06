# 📊 AI股票分析系统

基于六维真强势策略的智能选股系统，结合技术指标扫描和AI深度分析。

## 🎯 核心功能

- **六维技术评分**：趋势、K线、量价、分时、盘口、尾盘
- **市场环境过滤**：自动检测大盘强弱，避免逆势操作
- **AI深度分析**：DeepSeek Chat 提供风险评估和操作建议
- **Web可视化**：美观的网页界面展示分析结果
- **策略持续优化**：基于实盘表现自动改进

## 🚀 快速开始

### 本地运行

```bash
# 1. 安装依赖
pip install -r requirements_web.txt

# 2. 启动Web应用
python3 web_app.py

# 3. 访问
http://localhost:5000
```

### 每日选股流程

```bash
# 1. 检查市场环境
python3 scripts/strategy_scanner_v2.py

# 2. AI深度分析（如市场OK）
python3 scripts/scan_and_analyze.py --top 5

# 3. 推送到企业微信
python3 scripts/push_top5_picks.py
```

## 📈 策略特点

### ✅ 已实施的改进

1. **市场环境过滤**（2026-02-06）
   - 大盘未站上MA20时自动拦截
   - 避免在弱势环境选股

2. **AI风险分析强化**
   - 强制输出技术风险点
   - 假设下跌的原因和支撑位
   - 对比板块相对强度

3. **六维真强势评分**
   - 动态成交量过滤
   - 多头均线排列要求
   - 综合打分系统

## 🌐 部署（外网访问）

本系统支持多种部署方式，推荐使用Railway：

### Railway部署（推荐）

1. 推送代码到GitHub
2. 访问 https://railway.app/
3. 连接GitHub仓库
4. 自动部署
5. 获得公网域名

详细步骤见 [DEPLOYMENT.md](DEPLOYMENT.md)

## 📊 技术栈

- **后端**: Python + Flask
- **AI模型**: DeepSeek Chat / Gemini
- **数据源**: Yahoo Finance
- **前端**: HTML + CSS + JavaScript
- **部署**: Railway / Render / Vercel

## 📝 环境变量

创建 `.env` 文件（本地测试）：

```bash
# AI API Keys
OPENAI_API_KEY=your_deepseek_key
OPENAI_BASE_URL=https://api.deepseek.com/v1

# 可选
GEMINI_API_KEY=your_gemini_key
WECHAT_WEBHOOK=your_wechat_webhook
```

⚠️ **重要**：`.env` 文件已在 `.gitignore` 中，不会推送到GitHub

## 🎨 Web界面

- 首页：最新选股和策略特点
- 选股策略：详细策略文档
- 综合分析：AI分析报告
- 策略回顾：实盘表现分析
- 个股详情：单只股票深度分析

## 📱 移动端支持

响应式设计，支持手机/平板访问。

## 📄 License

MIT License

## 🙏 致谢

- Yahoo Finance API
- DeepSeek Chat
- Flask Framework