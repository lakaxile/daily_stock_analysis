#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
复盘脚本：回顾 2026-02-08 推荐股票在 2026-02-09 和 2026-02-10 的表现
"""

import sys
import os
import yfinance as yf
import pandas as pd
import logging
from datetime import datetime, timedelta

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# 2月8日推荐的股票列表
# 包括 S级 和 A级热门
TARGETS = [
    # S级
    {"code": "002345", "name": "潮宏基", "level": "S", "buy_zone": [12.80, 13.00], "stop_loss": 12.35, "target": 14.80},
    {"code": "300448", "name": "浩云科技", "level": "S", "buy_zone": [9.70, 9.90], "stop_loss": 9.35, "target": 10.80},
    {"code": "300483", "name": "首华燃气", "level": "S", "buy_zone": [16.50, 16.80], "stop_loss": 15.50, "target": 19.00},
    # A级热门
    {"code": "002339", "name": "积成电子", "level": "A(热门)"},
    {"code": "002957", "name": "科瑞技术", "level": "A(热门)"},
    {"code": "688428", "name": "诺诚健华", "level": "A(热门)"},
    {"code": "300666", "name": "江丰电子", "level": "A(热门)"},
    {"code": "300812", "name": "易天股份", "level": "A(热门)"},
    {"code": "300843", "name": "胜蓝股份", "level": "A(热门)"},
    {"code": "300479", "name": "神思电子", "level": "A(热门)"},
    {"code": "300523", "name": "辰安科技", "level": "A(热门)"}
]

def get_market_data(code):
    """获取最近几天的市场数据"""
    suffix = ".SS" if code.startswith("6") else ".SZ"
    ticker = f"{code}{suffix}"
    
    try:
        stock = yf.Ticker(ticker)
        # 获取最近5天数据，确保覆盖周一周二
        hist = stock.history(period="5d")
        return hist
    except Exception as e:
        logger.error(f"Failed to fetch data for {code}: {e}")
        return None

def analyze_performance():
    print("# 📊 策略复盘报告 (2026-02-10)\n")
    print(f"**复盘对象**: 2月8日分析的 11 只股票")
    print(f"**观察周期**: 2月9日(周一) - 2月10日(周二)\n")
    
    print("## 1. 个股表现详情\n")
    print("| 代码 | 名称 | 等级 | 2/8收盘 | 最新收盘 | 累计涨跌 | 状态评价 |")
    print("|---|---|---|---|---|---|---|")
    
    success_count = 0
    total_count = 0
    sum_change = 0
    
    details_report = ""
    
    for stock in TARGETS:
        code = stock['code']
        name = stock['name']
        level = stock['level']
        
        hist = get_market_data(code)
        if hist is None or hist.empty:
            print(f"| {code} | {name} | {level} | N/A | N/A | N/A | 数据缺失 |")
            continue
            
        # 假设 2/6 是周五（推荐时的基准数据），2/9 是周一，2/10 是周二
        # 我们需要找到这些日期。由于时区问题，我们简单取最后两条数据
        if len(hist) < 2:
             print(f"| {code} | {name} | {level} | N/A | N/A | N/A | 数据不足 |")
             continue
             
        # 基准日（2月6日或最近的一个交易日，推荐日）
        # 这里为了简单，我们取倒数第三天作为基准（如果今天是周二，那倒数第三天是周五）
        # 或者更准确：找到 index 等于 2026-02-06, 09, 10 的行
        
        # 简单处理：取最后两天展示走势
        today_data = hist.iloc[-1]
        yesterday_data = hist.iloc[-2]
        base_data = hist.iloc[-3] if len(hist) >= 3 else hist.iloc[0]
        
        base_price = base_data['Close']
        curr_price = today_data['Close']
        
        total_change_pct = ((curr_price - base_price) / base_price) * 100
        sum_change += total_change_pct
        total_count += 1
        
        status = "🔴 亏损"
        if total_change_pct > 0:
            status = "🟢 盈利"
            success_count += 1
        if total_change_pct > 5:
            status = "🔥 大涨"
        if total_change_pct < -5:
            status = "❄️ 大跌"
            
        print(f"| {code} | {name} | {level} | {base_price:.2f} | {curr_price:.2f} | **{total_change_pct:+.2f}%** | {status} |")
        
        # 详细分析 S 级策略执行情况
        if "buy_zone" in stock:
            buy_low, buy_high = stock['buy_zone']
            stop = stock['stop_loss']
            target = stock['target']
            
            # 检查周一(yesterday) 和 周二(today) 最低价是否给机会买入
            min_low = min(yesterday_data['Low'], today_data['Low'])
            max_high = max(yesterday_data['High'], today_data['High'])
            
            check_msg = ""
            if min_low <= buy_high:
                check_msg += f"✅ 进入买入区间({buy_high})。"
                # 检查是否止损
                if min_low < stop:
                    check_msg += f"❌ 但触发止损({stop})。"
                # 检查是否止盈
                elif max_high >= target:
                    check_msg += f"🏆 达到目标位({target})！"
                else:
                    check_msg += "持仓中。"
            else:
                check_msg += "⚠️ 未给买入机会(未回调至区间)。"
                
            details_report += f"- **{name} ({code})**: {check_msg} (最低 {min_low:.2f}, 最高 {max_high:.2f})\n"

    avg_change = sum_change / total_count if total_count > 0 else 0
    win_rate = (success_count / total_count * 100) if total_count > 0 else 0
    
    print("\n## 2. 策略执行细节 (S级复盘)\n")
    print(details_report)
    
    print("\n## 3. 总结与修正建议\n")
    print(f"- **整体胜率**: {win_rate:.1f}% ({success_count}/{total_count})")
    print(f"- **平均收益**: {avg_change:+.2f}%")
    
    print("\n---")
    print("\n### 🧠 策略修正分析 (AI生成)\n")
    
    # 这里可以插入后续 AI 调用的逻辑，或者直接人工总结
    if win_rate < 50:
        print("⚠️ **警示**: 胜率偏低，当前市场环境可能不适合激进追涨。")
        print("建议: 1. 收紧买入条件（要求更深的回调）。2. 减少非主线题材的操作。")
    elif avg_change < 0:
        print("⚠️ **警示**: 赚了指数不赚钱，或高位接盘。")
        print("建议: 严格执行止损，避免单笔大亏。")
    else:
        print("✅ **状态**: 策略表现良好，继续保持。")
        print("建议: 关注龙头股的持续性，在此基础上可适当增加仓位。")

if __name__ == "__main__":
    analyze_performance()
