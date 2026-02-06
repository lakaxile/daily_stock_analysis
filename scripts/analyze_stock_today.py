#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析华升股份今日走势
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yfinance as yf
import pandas as pd
from datetime import datetime
from src.analyzer import GeminiAnalyzer
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def analyze_stock_today(code='600156', name='华升股份'):
    """分析今日走势"""
    
    logger.info("="*70)
    logger.info(f"📊 {name}({code}) 今日走势分析")
    logger.info("="*70)
    
    ticker = f"{code}.SS" if code.startswith('6') else f"{code}.SZ"
    
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period='10d')
        
        if len(hist) < 2:
            logger.error("数据不足")
            return
        
        # 昨日和今日数据
        yesterday = hist.iloc[-2]
        today = hist.iloc[-1]
        
        yesterday_close = float(yesterday['Close'])
        today_open = float(today['Open'])
        today_high = float(today['High'])
        today_low = float(today['Low'])
        today_close = float(today['Close'])
        today_volume = float(today['Volume'])
        
        # 计算指标
        change_pct = ((today_close - yesterday_close) / yesterday_close) * 100
        amplitude = ((today_high - today_low) / yesterday_close) * 100
        
        # 开盘相对涨幅
        open_change = ((today_open - yesterday_close) / yesterday_close) * 100
        
        # 涨跌停距离
        limit_up = yesterday_close * 1.10
        limit_down = yesterday_close * 0.90
        
        # 收盘位置
        if today_high != today_low:
            close_position = ((today_close - today_low) / (today_high - today_low)) * 100
        else:
            close_position = 50
        
        # 计算均线
        hist['MA5'] = hist['Close'].rolling(window=5).mean()
        hist['MA10'] = hist['Close'].rolling(window=10).mean()
        ma5 = float(hist['MA5'].iloc[-1])
        ma10 = float(hist['MA10'].iloc[-1])
        
        logger.info(f"\n📈 基础数据")
        logger.info(f"  昨收: ¥{yesterday_close:.2f}")
        logger.info(f"  今开: ¥{today_open:.2f} ({open_change:+.2f}%)")
        logger.info(f"  最高: ¥{today_high:.2f}")
        logger.info(f"  最低: ¥{today_low:.2f}")
        logger.info(f"  今收: ¥{today_close:.2f}")
        logger.info(f"  涨跌: {change_pct:+.2f}%")
        logger.info(f"  振幅: {amplitude:.2f}%")
        logger.info(f"  收盘位置: {close_position:.1f}%")
        
        logger.info(f"\n📊 技术指标")
        logger.info(f"  MA5: ¥{ma5:.2f}")
        logger.info(f"  MA10: ¥{ma10:.2f}")
        logger.info(f"  相对MA5: {((today_close - ma5) / ma5 * 100):+.2f}%")
        logger.info(f"  相对MA10: {((today_close - ma10) / ma10 * 100):+.2f}%")
        
        # 判断走势特征
        logger.info(f"\n🔍 走势特征")
        
        if change_pct > 0:
            logger.info(f"  ✅ 收阳线 ({change_pct:+.2f}%)")
        else:
            logger.info(f"  ❌ 收阴线 ({change_pct:+.2f}%)")
        
        if today_close > yesterday_close:
            if close_position >= 80:
                logger.info(f"  ✅ 强势收盘 (位置{close_position:.0f}%)")
            elif close_position >= 50:
                logger.info(f"  🟡 中性收盘 (位置{close_position:.0f}%)")
            else:
                logger.info(f"  ⚠️  上影线较长 (位置{close_position:.0f}%)")
        
        if today_close > ma5:
            logger.info(f"  ✅ 站上MA5")
        else:
            logger.info(f"  ❌ 跌破MA5")
        
        # 昨日AI预测回顾
        logger.info(f"\n📋 昨日AI预测回顾")
        logger.info(f"  AI评分: 85/100")
        logger.info(f"  AI建议: 买入 🟢")
        logger.info(f"  AI结论: [S级] 六维全优，趋势强劲")
        logger.info(f"  理想买入: ¥8.80")
        logger.info(f"  止损位: ¥8.15")
        logger.info(f"  昨收盘: ¥9.03 (涨停)")
        
        # 验证预测
        logger.info(f"\n✅ 预测验证")
        if change_pct > 0:
            logger.info(f"  ✅ 预测方向正确：继续上涨")
        else:
            logger.info(f"  ❌ 预测失误：出现回调")
        
        if today_close > 8.15:
            logger.info(f"  ✅ 未触及止损位")
        else:
            logger.info(f"  ❌ 触及止损位")
        
        # 准备AI分析
        context = f"""
华升股份(600156)走势分析请求

## 背景
昨日(2026-02-05)选股时：
- 技术评分: 9/10 (S级)
- AI评分: 85/100
- AI建议: 买入
- 收盘: 涨停 +9.99% at ¥9.03
- AI结论: "[S级] 六维全优，趋势强劲，量价齐升，建议果断上车"

## 今日(2026-02-06)实际表现
- 昨收: ¥{yesterday_close:.2f}
- 今开: ¥{today_open:.2f} ({open_change:+.2f}%)
- 最高: ¥{today_high:.2f}
- 最低: ¥{today_low:.2f}
- 今收: ¥{today_close:.2f}
- 涨跌: {change_pct:+.2f}%
- 振幅: {amplitude:.2f}%
- 收盘位置: {close_position:.1f}%
- MA5: ¥{ma5:.2f}
- MA10: ¥{ma10:.2f}

## 市场环境
- 上证指数: 未站上MA20，MA5<MA10，偏弱

请分析：
1. 今日走势是否符合昨日的S级评价？
2. 如何解读今日的K线形态？
3. 接下来2-3天的操作建议？
4. 如果昨日按AI建议买入（无法买入因涨停），今日应如何操作？
5. 当前是否仍值得关注或买入？

请给出专业、客观的分析和操作建议。
"""
        
        # 调用AI分析
        logger.info(f"\n🤖 调用AI深度分析...")
        
        try:
            analyzer = GeminiAnalyzer()
            if not analyzer.is_available():
                logger.warning("AI分析器不可用")
                return
            
            generation_config = {
                "temperature": 0.3,
                "max_output_tokens": 4096,
            }
            
            ai_response = analyzer._call_api_with_retry(context, generation_config)
            
            logger.info("\n" + "="*70)
            logger.info("🤖 AI分析报告")
            logger.info("="*70)
            logger.info(f"\n{ai_response}")
            
            # 保存报告
            report = f"""# 华升股份(600156)今日走势分析

**分析日期**: {datetime.now().strftime('%Y-%m-%d %H:%M')}

## 📊 今日行情

| 指标 | 数值 |
|------|------|
| 昨收 | ¥{yesterday_close:.2f} |
| 今开 | ¥{today_open:.2f} ({open_change:+.2f}%) |
| 最高 | ¥{today_high:.2f} |
| 最低 | ¥{today_low:.2f} |
| 今收 | ¥{today_close:.2f} |
| **涨跌幅** | **{change_pct:+.2f}%** |
| 振幅 | {amplitude:.2f}% |
| 收盘位置 | {close_position:.1f}% |
| MA5 | ¥{ma5:.2f} |
| MA10 | ¥{ma10:.2f} |

## 🤖 AI深度分析

{ai_response}

---
*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
            
            filename = f'data/stock_analysis_600156_{datetime.now().strftime("%Y-%m-%d")}.md'
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(report)
            
            logger.info(f"\n📄 分析报告已保存: {filename}")
            
        except Exception as e:
            logger.error(f"AI分析失败: {e}")
        
    except Exception as e:
        logger.error(f"❌ 数据获取失败: {e}")


if __name__ == "__main__":
    analyze_stock_today()
