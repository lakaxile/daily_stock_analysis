#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对精选股票进行AI深度分析
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import pandas as pd
import yfinance as yf
from datetime import datetime
from src.analyzer import GeminiAnalyzer
from src.search_service import SearchService
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def get_stock_context(code: str) -> dict:
    """获取股票技术面数据"""
    ticker = f"{code}.SS" if code.startswith(('6', '688')) else f"{code}.SZ"
    
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period='60d')
        
        if hist.empty:
            return None
        
        today = hist.iloc[-1]
        yesterday = hist.iloc[-2] if len(hist) >= 2 else today
        
        # 计算技术指标
        hist['MA5'] = hist['Close'].rolling(window=5).mean()
        hist['MA10'] = hist['Close'].rolling(window=10).mean()
        hist['MA20'] = hist['Close'].rolling(window=20).mean()
        
        close = float(today['Close'])
        change_pct = ((close - float(yesterday['Close'])) / float(yesterday['Close'])) * 100
        
        return {
            'code': code,
            'price': close,
            'change_pct': change_pct,
            'volume': float(today['Volume']),
            'ma5': float(hist['MA5'].iloc[-1]),
            'ma10': float(hist['MA10'].iloc[-1]),
            'ma20': float(hist['MA20'].iloc[-1]),
        }
    except Exception as e:
        logger.error(f"获取{code}数据失败: {e}")
        return None


def analyze_top5_with_ai():
    """对TOP 5股票进行AI分析"""
    
    # 读取今日选股池
    with open('data/watchlist.json', 'r', encoding='utf-8') as f:
        watchlist = json.load(f)
    
    today = datetime.now().strftime('%Y-%m-%d')
    stocks = watchlist.get(today, [])
    
    if not stocks:
        logger.error("未找到今日选股")
        return
    
    logger.info("="*70)
    logger.info("🤖 AI深度分析 - TOP股票")
    logger.info("="*70)
    
    # 初始化AI分析器
    try:
        analyzer = GeminiAnalyzer()
        if not analyzer.is_available():
            logger.error("❌ AI分析器不可用，请检查API配置")
            logger.info("💡 需要在.env中配置:")
            logger.info("   GEMINI_API_KEY=你的key")
            logger.info("   或")
            logger.info("   OPENAI_API_KEY=你的key")
            logger.info("   OPENAI_BASE_URL=https://api.deepseek.com/v1")
            return
        logger.info(f"✅ AI分析器就绪")
    except Exception as e:
        logger.error(f"❌ AI分析器初始化失败: {e}")
        return
    
    # 初始化搜索服务（获取新闻）
    try:
        search_service = SearchService()
        logger.info("✅ 搜索服务就绪")
    except Exception as e:
        logger.warning(f"⚠️  搜索服务初始化失败: {e}")
        search_service = None
    
    print()  # 空行
    
    # 分析每只股票
    results = []
    for i, stock in enumerate(stocks[:5], 1):
        code = stock['code']
        name = stock['name']
        
        logger.info(f"📊 [{i}/5] 分析 {name} ({code})...")
        
        # 1. 获取技术面数据
        context = get_stock_context(code)
        if not context:
            logger.warning(f"  ⚠️  跳过{code}：数据获取失败")
            continue
        
        # 2. 获取新闻（可选）
        news_context = None
        if search_service:
            try:
                logger.info(f"  🔍 搜索最新新闻...")
                news = search_service.search_stock_news(code, name, max_results=3)
                if news:
                    news_context = f"{name}最新新闻：\n"
                    for j, item in enumerate(news[:3], 1):
                        news_context += f"{j}. {item.get('title', '')}\n"
                    logger.info(f"  ✅ 找到{len(news)}条新闻")
            except Exception as e:
                logger.warning(f"  ⚠️  新闻检索失败: {e}")
        
        # 3. AI分析
        try:
            logger.info(f"  🤖 调用AI分析...")
            analysis = analyzer.analyze(context, news_context)
            
            logger.info(f"  ✅ AI分析完成")
            logger.info(f"     评分: {analysis.sentiment_score}/100")
            logger.info(f"     趋势: {analysis.trend_prediction}")
            logger.info(f"     建议: {analysis.operation_advice}")
            logger.info(f"     核心结论: {analysis.dashboard.get('core_conclusion', {}).get('one_sentence', 'N/A')}")
            
            results.append({
                'code': code,
                'name': name,
                'analysis': analysis
            })
            
        except Exception as e:
            logger.error(f"  ❌ AI分析失败: {e}")
        
        print()  # 空行
    
    # 保存分析结果
    if results:
        save_analysis_report(results)
    
    logger.info("="*70)
    logger.info(f"✅ AI分析完成，成功分析 {len(results)}/{len(stocks[:5])} 只股票")
    logger.info("="*70)


def save_analysis_report(results):
    """保存AI分析报告"""
    today = datetime.now().strftime('%Y-%m-%d')
    
    report = f"""# 🤖 AI深度分析报告 ({today})

## 📊 分析概览

本报告使用AI对今日精选的TOP股票进行深度分析，结合技术面、基本面和新闻面给出投资建议。

---

"""
    
    for i, item in enumerate(results, 1):
        analysis = item['analysis']
        core_conclusion = analysis.dashboard.get('core_conclusion', {}).get('one_sentence', 'N/A')
        key_drivers = analysis.dashboard.get('key_drivers', [])[:3]
        risk_factors = analysis.dashboard.get('risk_factors', [])[:3]
        
        report += f"""
## {i}. {item['name']} ({item['code']})

### 🎯 核心结论
{core_conclusion}

### 📈 AI评分
- **情绪评分**: {analysis.sentiment_score}/100
- **趋势预测**: {analysis.trend_prediction}
- **操作建议**: {analysis.operation_advice}
- **置信度**: {analysis.confidence_level}

### 💡 关键驱动因素
{chr(10).join([f'- {factor}' for factor in key_drivers]) if key_drivers else '- 暂无'}

### ⚠️ 风险提示
{chr(10).join([f'- {risk}' for risk in risk_factors]) if risk_factors else '- 暂无'}

---
"""
    
    # 保存报告
    filename = f'data/ai_analysis_report_{today}.md'
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(report)
    
    logger.info(f"📄 AI分析报告已保存: {filename}")


if __name__ == "__main__":
    analyze_top5_with_ai()
