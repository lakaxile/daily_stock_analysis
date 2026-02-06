#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
S级股票跟踪分析 - 分析昨日筛选股票的今日表现
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import csv
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def load_filtered_stocks(date: str = '2026-02-03') -> List[Dict]:
    """加载昨日筛选的S级股票"""
    csv_file = f'data/s_level_strict_filtered_{date}.csv'
    
    stocks = []
    with open(csv_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            stocks.append({
                'code': row['股票代码'],
                'name': row['股票名称'],
                'yesterday_price': float(row['最新价']),
                'yesterday_ma5': float(row['MA5']),
                'yesterday_volume_ratio': float(row['量比']),
                'yesterday_rsi': float(row['RSI(6)']),
                'board': row['板块']
            })
    
    return stocks


def get_today_data(code: str) -> Dict:
    """获取股票今日数据"""
    try:
        # 添加市场后缀
        if code.startswith('6'):
            ticker = f"{code}.SS"
        else:
            ticker = f"{code}.SZ"
        
        stock = yf.Ticker(ticker)
        
        # 获取最近10天数据
        hist = stock.history(period='10d')
        
        if hist.empty or len(hist) < 2:
            logger.warning(f"  ⚠️  {code} 数据不足")
            return None
        
        # 今日和昨日数据
        today = hist.iloc[-1]
        yesterday = hist.iloc[-2]
        
        today_close = float(today['Close'])
        yesterday_close = float(yesterday['Close'])
        
        # 涨跌幅
        change_pct = ((today_close - yesterday_close) / yesterday_close) * 100
        
        # 今日开盘、最高、最低
        today_open = float(today['Open'])
        today_high = float(today['High'])
        today_low = float(today['Low'])
        
        # 振幅
        amplitude = ((today_high - today_low) / yesterday_close) * 100
        
        # 成交量
        today_volume = float(today['Volume'])
        yesterday_volume = float(yesterday['Volume'])
        volume_change = ((today_volume - yesterday_volume) / yesterday_volume) * 100
        
        # 计算均线
        hist['MA5'] = hist['Close'].rolling(window=5).mean()
        today_ma5 = float(hist['MA5'].iloc[-1])
        
        # 量比（今日vs最近5日平均）
        hist['VOL_MA5'] = hist['Volume'].rolling(window=5).mean()
        vol_ma5 = float(hist['VOL_MA5'].iloc[-1])
        volume_ratio = today_volume / vol_ma5 if vol_ma5 > 0 else 0
        
        # K线形态
        body = abs(today_close - today_open)
        total_range = today_high - today_low
        body_ratio = (body / total_range * 100) if total_range > 0 else 0
        is_yang = today_close > today_open
        
        # 涨停/跌停判断（±10%）
        is_limit_up = change_pct >= 9.9
        is_limit_down = change_pct <= -9.9
        
        return {
            'close': today_close,
            'open': today_open,
            'high': today_high,
            'low': today_low,
            'change_pct': change_pct,
            'amplitude': amplitude,
            'volume': today_volume,
            'volume_change': volume_change,
            'volume_ratio': volume_ratio,
            'ma5': today_ma5,
            'is_yang': is_yang,
            'body_ratio': body_ratio,
            'is_limit_up': is_limit_up,
            'is_limit_down': is_limit_down,
        }
        
    except Exception as e:
        logger.error(f"  ❌ {code} 获取失败: {e}")
        return None


def analyze_performance(stock: Dict, today_data: Dict) -> Dict:
    """分析股票表现"""
    
    # 价格变动分析
    price_change = today_data['close'] - stock['yesterday_price']
    
    # 与MA5关系
    above_ma5 = today_data['close'] > today_data['ma5']
    ma5_change = today_data['ma5'] - stock['yesterday_ma5']
    
    # 量能对比
    volume_status = "放量" if today_data['volume_ratio'] > 1.5 else "缩量" if today_data['volume_ratio'] < 0.8 else "平量"
    
    # 趋势判断
    if today_data['change_pct'] > 3:
        trend = "强势上涨"
        emoji = "🚀"
    elif today_data['change_pct'] > 0:
        trend = "温和上涨"
        emoji = "📈"
    elif today_data['change_pct'] > -3:
        trend = "小幅回调"
        emoji = "📉"
    else:
        trend = "深度回调"
        emoji = "⚠️"
    
    # 综合评级
    score = 0
    reasons = []
    
    # 涨跌幅评分
    if today_data['is_limit_up']:
        score += 5
        reasons.append("涨停板(+5)")
    elif today_data['change_pct'] > 5:
        score += 4
        reasons.append("大涨(+4)")
    elif today_data['change_pct'] > 2:
        score += 3
        reasons.append("上涨(+3)")
    elif today_data['change_pct'] > 0:
        score += 1
        reasons.append("微涨(+1)")
    elif today_data['change_pct'] > -2:
        score -= 1
        reasons.append("微跌(-1)")
    elif today_data['change_pct'] > -5:
        score -= 3
        reasons.append("回调(-3)")
    else:
        score -= 5
        reasons.append("大跌(-5)")
    
    # 均线评分
    if above_ma5:
        score += 1
        reasons.append("站上MA5(+1)")
    else:
        score -= 2
        reasons.append("跌破MA5(-2)")
    
    # 量能评分
    if today_data['is_yang'] and today_data['volume_ratio'] > 1.5:
        score += 2
        reasons.append("放量上涨(+2)")
    elif not today_data['is_yang'] and today_data['volume_ratio'] > 1.5:
        score -= 2
        reasons.append("放量下跌(-2)")
    
    # K线形态评分
    if today_data['is_yang'] and today_data['body_ratio'] > 60:
        score += 1
        reasons.append("大阳线(+1)")
    
    # 评级
    if score >= 6:
        rating = "S级-继续持有"
    elif score >= 3:
        rating = "A级-关注"
    elif score >= 0:
        rating = "B级-观望"
    else:
        rating = "C级-减仓"
    
    return {
        'trend': trend,
        'emoji': emoji,
        'score': score,
        'rating': rating,
        'reasons': reasons,
        'above_ma5': above_ma5,
        'volume_status': volume_status,
    }


def main():
    logger.info("=" * 70)
    logger.info("📊 S级股票今日表现跟踪分析")
    logger.info("=" * 70)
    logger.info("")
    
    # 加载昨日筛选股票
    stocks = load_filtered_stocks('2026-02-03')
    logger.info(f"📋 跟踪股票: {len(stocks)} 只")
    logger.info("")
    
    # 分析每只股票
    results = []
    for i, stock in enumerate(stocks, 1):
        logger.info(f"[{i}/{len(stocks)}] 分析 {stock['name']}({stock['code']})...")
        
        today_data = get_today_data(stock['code'])
        if not today_data:
            continue
        
        analysis = analyze_performance(stock, today_data)
        
        result = {
            **stock,
            **today_data,
            **analysis
        }
        results.append(result)
        
        logger.info(
            f"  {analysis['emoji']} {analysis['trend']} | "
            f"{today_data['change_pct']:+.2f}% | "
            f"量比{today_data['volume_ratio']:.2f} | "
            f"{analysis['rating']}"
        )
    
    logger.info("")
    logger.info("=" * 70)
    logger.info(f"✅ 分析完成: {len(results)}/{len(stocks)} 只成功")
    logger.info("=" * 70)
    
    # 生成报告
    if results:
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Markdown报告
        report_lines = [
            f"# S级股票今日表现跟踪 ({today})",
            "",
            f"**跟踪数量**: {len(results)} 只",
            f"**筛选日期**: 2026-02-03",
            "",
            "---",
            "",
        ]
        
        # 按评分排序
        sorted_results = sorted(results, key=lambda x: -x['score'])
        
        # 整体统计
        up_count = sum(1 for r in results if r['change_pct'] > 0)
        down_count = sum(1 for r in results if r['change_pct'] < 0)
        avg_change = sum(r['change_pct'] for r in results) / len(results)
        
        report_lines.extend([
            "## 📊 整体表现",
            "",
            f"- 上涨: {up_count} 只 ({up_count/len(results)*100:.1f}%)",
            f"- 下跌: {down_count} 只 ({down_count/len(results)*100:.1f}%)",
            f"- 平均涨幅: {avg_change:+.2f}%",
            "",
            "---",
            "",
            "## 📈 个股详情",
            "",
        ])
        
        for i, r in enumerate(sorted_results, 1):
            report_lines.extend([
                f"### {i}. {r['emoji']} {r['name']}({r['code']}) - {r['rating']}",
                "",
                "**今日表现**:",
                f"- 涨跌幅: {r['change_pct']:+.2f}% ({r['trend']})",
                f"- 价格: ¥{r['close']:.2f} (开:{r['open']:.2f} 高:{r['high']:.2f} 低:{r['low']:.2f})",
                f"- 振幅: {r['amplitude']:.2f}%",
                f"- K线: {'阳线' if r['is_yang'] else '阴线'} (实体{r['body_ratio']:.1f}%)",
                "",
                "**量能分析**:",
                f"- 量比: {r['volume_ratio']:.2f}x ({r['volume_status']})",
                f"- 成交量变化: {r['volume_change']:+.1f}%",
                "",
                "**技术指标**:",
                f"- MA5: ¥{r['ma5']:.2f} ({'站上' if r['above_ma5'] else '跌破'})",
                "",
                "**评分依据**:",
            ])
            
            for reason in r['reasons']:
                report_lines.append(f"- {reason}")
            
            report_lines.extend(["", "---", ""])
        
        report = "\n".join(report_lines)
        
        # 保存报告
        report_file = f'data/s_stocks_tracking_{today}.md'
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info(f"\n✅ 报告已保存: {report_file}")
        
        # 输出汇总
        logger.info("")
        logger.info("📊 今日表现汇总:")
        logger.info("")
        for i, r in enumerate(sorted_results, 1):
            logger.info(
                f"{i:2d}. {r['emoji']} {r['name']:8s} | "
                f"{r['change_pct']:+6.2f}% | "
                f"量比{r['volume_ratio']:.2f} | "
                f"{r['rating']}"
            )
        
        logger.info("")
        logger.info("=" * 70)


if __name__ == "__main__":
    main()
