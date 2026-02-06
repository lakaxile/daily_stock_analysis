#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
回顾昨日选股表现并生成分析报告
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def load_yesterday_picks():
    """加载昨日选股"""
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    # 从watchlist.json加载
    try:
        with open('data/watchlist.json', 'r', encoding='utf-8') as f:
            watchlist = json.load(f)
        
        picks = watchlist.get(yesterday, [])
        if not picks:
            logger.warning(f"未找到{yesterday}的选股记录")
            return None
        
        logger.info(f"📊 加载{yesterday}的选股: {len(picks)}只")
        return picks, yesterday
    except Exception as e:
        logger.error(f"加载watchlist失败: {e}")
        return None


def get_today_performance(picks, yesterday_date):
    """获取今日表现"""
    results = []
    
    logger.info("\n🔍 获取今日实际表现...")
    
    for pick in picks:
        code = pick['code']
        name = pick.get('name', code)
        ticker = f"{code}.SS" if code.startswith(('6', '688')) else f"{code}.SZ"
        
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period='5d')
            
            if len(hist) < 2:
                logger.warning(f"  ⚠️  {name}({code}): 数据不足")
                continue
            
            # 昨日和今日数据
            yesterday_close = float(hist['Close'].iloc[-2])
            today_close = float(hist['Close'].iloc[-1])
            today_high = float(hist['High'].iloc[-1])
            today_low = float(hist['Low'].iloc[-1])
            today_volume = float(hist['Volume'].iloc[-1])
            
            change_pct = ((today_close - yesterday_close) / yesterday_close) * 100
            
            # 最大涨幅和最大回撤
            max_gain = ((today_high - yesterday_close) / yesterday_close) * 100
            max_drawdown = ((today_low - yesterday_close) / yesterday_close) * 100
            
            result = {
                'code': code,
                'name': name,
                'yesterday_close': yesterday_close,
                'today_close': today_close,
                'today_high': today_high,
                'today_low': today_low,
                'change_pct': change_pct,
                'max_gain': max_gain,
                'max_drawdown': max_drawdown,
                'volume': today_volume,
                'yesterday_score': pick.get('score', 0) / 10,  # 转为10分制
                'yesterday_operation': pick.get('operation_advice', ''),
            }
            
            # 判断表现
            if change_pct >= 5:
                performance = "🟢 优秀"
            elif change_pct >= 2:
                performance = "🟡 良好"
            elif change_pct >= 0:
                performance = "⚪ 平稳"
            elif change_pct >= -2:
                performance = "🟠 微跌"
            else:
                performance = "🔴 较差"
            
            result['performance'] = performance
            results.append(result)
            
            logger.info(f"  ✅ {name}({code}): {change_pct:+.2f}% {performance}")
            
        except Exception as e:
            logger.error(f"  ❌ {name}({code}): 获取数据失败 - {e}")
    
    return results


def analyze_strategy_with_ai(results, yesterday_date):
    """使用AI分析选股策略的优缺点"""
    from src.analyzer import GeminiAnalyzer
    
    # 准备分析数据
    summary = f"""# 昨日选股表现回顾 ({yesterday_date})

## 📊 整体表现

共选出 {len(results)} 只股票，今日表现如下：

"""
    
    # 计算统计数据
    avg_change = sum(r['change_pct'] for r in results) / len(results) if results else 0
    best_stock = max(results, key=lambda x: x['change_pct']) if results else None
    worst_stock = min(results, key=lambda x: x['change_pct']) if results else None
    win_rate = sum(1 for r in results if r['change_pct'] > 0) / len(results) * 100 if results else 0
    
    summary += f"""
**关键指标**:
- 平均涨跌幅: {avg_change:+.2f}%
- 胜率: {win_rate:.1f}% ({sum(1 for r in results if r['change_pct'] > 0)}/{len(results)} 上涨)
- 最佳: {best_stock['name']}({best_stock['code']}) {best_stock['change_pct']:+.2f}%
- 最差: {worst_stock['name']}({worst_stock['code']}) {worst_stock['change_pct']:+.2f}%

## 📋 个股详情

| 股票 | 昨收 | 今收 | 涨跌幅 | 最高点 | 最低点 | 昨日评分 | 表现 |
|------|------|------|--------|--------|--------|----------|------|
"""
    
    for r in sorted(results, key=lambda x: x['change_pct'], reverse=True):
        summary += f"| {r['name']}({r['code']}) | ¥{r['yesterday_close']:.2f} | ¥{r['today_close']:.2f} | {r['change_pct']:+.2f}% | ¥{r['today_high']:.2f} | ¥{r['today_low']:.2f} | {r['yesterday_score']}/10 | {r['performance']} |\n"
    
    summary += f"""

## 🎯 选股策略回顾

**昨日使用的策略**:
1. 六维真强势评分系统（趋势、K线、量价、分时、盘口、尾盘）
2. 动态成交量过滤（量比要求）
3. 多头均线排列要求
4. AI深度分析辅助决策

**选股标准**:
- 技术评分 ≥ 8/10
- AI评分 ≥ 65/100
- 优先选择AI建议"买入"的股票
- 均线多头排列
- 量价配合良好

---

请基于以上数据，深入分析：

1. **策略有效性评估**
   - 整体表现是否符合预期？
   - 哪些指标的筛选效果好？
   - 哪些指标可能存在误判？

2. **具体问题诊断**
   - 为什么某些高评分股票表现不佳？
   - AI评分与实际表现是否匹配？
   - 技术指标是否出现滞后？

3. **改进建议**（至少3-5条具体可执行的建议）
   - 应该调整哪些评分权重？
   - 需要增加哪些过滤条件？
   - 如何优化AI分析的prompt？
   - 是否需要加入新的技术指标？

请给出专业、客观、可执行的改进方案。
"""
    
    # 调用AI分析
    try:
        analyzer = GeminiAnalyzer()
        if not analyzer.is_available():
            logger.warning("AI分析器不可用，仅生成数据报告")
            return summary, None
        
        logger.info("\n🤖 调用AI分析选股策略...")
        
        # 构建AI prompt
        context = {
            'code': 'STRATEGY_REVIEW',
            'stock_name': '选股策略分析',
            'date': datetime.now().strftime('%Y-%m-%d'),
            'today': {},
        }
        
        # 直接调用AI
        from src.analyzer import GeminiAnalyzer
        config_prompt = f"""你是一位专业的量化交易策略分析师。请分析以下选股策略的表现并提出改进建议：

{summary}

请按照以下格式输出分析报告（纯文本格式，不要JSON）：

# 选股策略分析报告

## 一、整体表现评估
[评估整体表现，给出评级：优秀/良好/一般/较差]

## 二、问题诊断
### 1. 高分低表现股票分析
[分析为什么某些高评分股票今日表现不佳]

### 2. 指标有效性分析
[评估各项技术指标和AI评分的准确性]

### 3. 潜在风险点
[指出策略中存在的风险]

## 三、具体改进建议
### 建议1: [标题]
**问题**: [当前问题描述]
**方案**: [具体改进方案]
**预期效果**: [预期达成的效果]

### 建议2: [标题]
...

### 建议3: [标题]
...

### 建议4: [标题]
...

### 建议5: [标题]
...

## 四、执行优先级
[按重要性排序，说明哪些建议应该优先实施]
"""
        
        # 使用内部API调用
        generation_config = {
            "temperature": 0.3,  # 降低温度以获得更确定的分析
            "max_output_tokens": 8192,
        }
        
        ai_response = analyzer._call_api_with_retry(config_prompt, generation_config)
        
        logger.info("✅ AI分析完成")
        
        return summary, ai_response
        
    except Exception as e:
        logger.error(f"AI分析失败: {e}")
        return summary, None


def generate_report(data_summary, ai_analysis, yesterday_date):
    """生成完整报告"""
    today = datetime.now().strftime('%Y-%m-%d')
    
    report = f"""# 📊 选股策略回顾与改进分析

**回顾日期**: {yesterday_date}  
**分析日期**: {today}  
**分析师**: AI Strategy Analyzer

---

{data_summary}

---

"""
    
    if ai_analysis:
        report += f"""
# 🤖 AI深度分析

{ai_analysis}

---
"""
    else:
        report += """
# ⚠️ AI分析未能完成

请手工分析以上数据。

---
"""
    
    report += f"""
---
*本报告由自动化系统生成，结合历史数据和AI分析*
"""
    
    # 保存报告
    filename = f'data/strategy_review_{yesterday_date}.md'
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(report)
    
    logger.info(f"\n📄 策略分析报告已保存: {filename}")
    return filename


def main():
    logger.info("="*70)
    logger.info("📊 昨日选股策略回顾与分析")
    logger.info("="*70)
    
    # 1. 加载昨日选股
    result = load_yesterday_picks()
    if not result:
        return
    
    picks, yesterday_date = result
    
    # 2. 获取今日表现
    performance = get_today_performance(picks, yesterday_date)
    
    if not performance:
        logger.error("❌ 未获取到任何股票表现数据")
        return
    
    # 3. AI分析策略
    logger.info("\n" + "="*70)
    data_summary, ai_analysis = analyze_strategy_with_ai(performance, yesterday_date)
    
    # 4. 生成报告
    logger.info("\n" + "="*70)
    report_file = generate_report(data_summary, ai_analysis, yesterday_date)
    
    logger.info("\n" + "="*70)
    logger.info("✅ 分析完成")
    logger.info(f"   报告文件: {report_file}")
    logger.info("="*70)


if __name__ == "__main__":
    main()
