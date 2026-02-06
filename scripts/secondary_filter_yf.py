#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
S级股票二次严格筛选 - 使用yfinance API
筛选条件：
1. 评分≥85分
2. 成交量放大倍数>1.5
3. RSI(6)>60且<80
4. 价格在MA5之上
"""

import csv
import logging
from datetime import datetime
from typing import List, Dict, Optional
import yfinance as yf
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def calculate_rsi(prices: pd.Series, period: int = 6) -> float:
    """计算RSI指标"""
    deltas = prices.diff()
    gains = deltas.where(deltas > 0, 0)
    losses = -deltas.where(deltas < 0, 0)
    
    avg_gain = gains.rolling(window=period).mean().iloc[-1]
    avg_loss = losses.rolling(window=period).mean().iloc[-1]
    
    if avg_loss == 0:
        return 100.0
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def get_stock_details(code: str) -> Optional[Dict]:
    """使用yfinance获取股票详细技术指标"""
    try:
        # 添加市场后缀
        if code.startswith('6'):
            ticker = f"{code}.SS"  # 上交所
        else:
            ticker = f"{code}.SZ"  # 深交所
        
        # 获取股票对象
        stock = yf.Ticker(ticker)
        
        # 获取历史数据 (最近30天)
        hist = stock.history(period='1mo')
        
        if hist.empty or len(hist) < 10:
            logger.warning(f"  ⚠️  {code} 数据不足")
            return None
        
        # 获取最新数据
        latest = hist.iloc[-1]
        latest_close = float(latest['Close'])
        latest_volume = float(latest['Volume'])
        
        # 计算均线
        hist['MA5'] = hist['Close'].rolling(window=5).mean()
        hist['MA10'] = hist['Close'].rolling(window=10).mean()
        hist['MA20'] = hist['Close'].rolling(window=20).mean()
        
        ma5 = float(hist['MA5'].iloc[-1])
        ma10 = float(hist['MA10'].iloc[-1]) if len(hist) >= 10 else 0
        ma20 = float(hist['MA20'].iloc[-1]) if len(hist) >= 20 else 0
        
        # 计算成交量均线和量比
        hist['VOL_MA5'] = hist['Volume'].rolling(window=5).mean()
        vol_ma5 = float(hist['VOL_MA5'].iloc[-1])
        volume_ratio = latest_volume / vol_ma5 if vol_ma5 > 0 else 0
        
        # 计算RSI(6)
        rsi6 = calculate_rsi(hist['Close'], period=6)
        
        # 计算涨跌幅
        if len(hist) >= 2:
            prev_close = float(hist['Close'].iloc[-2])
            change_pct = ((latest_close - prev_close) / prev_close) * 100
        else:
            change_pct = 0
        
        result = {
            'code': code,
            'price': latest_close,
            'change_pct': change_pct,
            'ma5': ma5,
            'ma10': ma10,
            'ma20': ma20,
            'volume': latest_volume,
            'volume_ratio': volume_ratio,
            'rsi6': rsi6,
            'price_above_ma5': latest_close > ma5,
        }
        
        return result
        
    except Exception as e:
        logger.error(f"  ❌ {code} 获取失败: {e}")
        return None


def apply_filters(stock: Dict) -> tuple[bool, List[str]]:
    """应用筛选条件"""
    reasons = []
    
    # 条件1: 评分≥85
    if stock.get('score', 0) < 85:
        reasons.append(f"评分{stock.get('score')}分<85")
    
    # 条件2: 量比>1.5
    vol_ratio = stock.get('volume_ratio', 0)
    if vol_ratio <= 1.5:
        reasons.append(f"量比{vol_ratio:.2f}≤1.5")
    
    # 条件3: RSI(6)>60且<80
    rsi = stock.get('rsi6', 0)
    if not (60 < rsi < 80):
        reasons.append(f"RSI={rsi:.1f}不在(60,80)")
    
    # 条件4: 价格在MA5之上
    if not stock.get('price_above_ma5', False):
        reasons.append("未站上MA5")
    
    return len(reasons) == 0, reasons


def main():
    logger.info("=" * 70)
    logger.info("🔍 S级股票二次严格筛选 (yfinance)")
    logger.info("=" * 70)
    logger.info("")
    
    # 读取S级股票列表
    today = datetime.now().strftime('%Y-%m-%d')
    csv_file = f'data/s_level_stocks_{today}.csv'
    
    stocks = []
    with open(csv_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            stocks.append({
                'code': row['股票代码'],
                'name': row['股票名称'],
                'score': int(row['评分']),
                'trend': row['趋势预测'],
                'board': row['板块']
            })
    
    logger.info(f"📊 初始S级股票: {len(stocks)} 只")
    logger.info("")
    logger.info("筛选标准:")
    logger.info("  1️⃣  评分 ≥ 85分")
    logger.info("  2️⃣  量比 > 1.5")
    logger.info("  3️⃣  RSI(6) ∈ (60, 80)")
    logger.info("  4️⃣  价格 > MA5")
    logger.info("")
    logger.info("=" * 70)
    logger.info("")
    
    # 逐个获取详细数据并筛选
    passed_stocks = []
    failed_stocks = []
    
    for i, stock in enumerate(stocks, 1):
        logger.info(f"[{i}/{len(stocks)}] {stock['name']}({stock['code']})...")
        
        details = get_stock_details(stock['code'])
        if not details:
            failed_stocks.append({**stock, 'reason': '数据获取失败'})
            continue
        
        # 合并数据
        stock.update(details)
        
        # 应用筛选
        passed, reasons = apply_filters(stock)
        
        if passed:
            passed_stocks.append(stock)
            logger.info(f"  ✅ 通过 | 量比:{stock['volume_ratio']:.2f} RSI:{stock['rsi6']:.1f} 价格/MA5:{stock['price']:.2f}/{stock['ma5']:.2f}")
        else:
            stock['reason'] = '; '.join(reasons)
            failed_stocks.append(stock)
            logger.info(f"  ❌ 淘汰 | {stock['reason']}")
    
    logger.info("")
    logger.info("=" * 70)
    logger.info(f"🎯 筛选结果: {len(passed_stocks)}/{len(stocks)} 只通过")
    logger.info("=" * 70)
    logger.info("")
    
    if passed_stocks:
        # 保存CSV
        result_file = f'data/s_level_strict_filtered_{today}.csv'
        with open(result_file, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                '股票代码', '股票名称', '评分', '最新价', '涨跌幅', 
                'MA5', 'MA10', 'MA20', '量比', 'RSI(6)', '板块'
            ])
            writer.writeheader()
            
            for s in sorted(passed_stocks, key=lambda x: -x.get('rsi6', 0)):
                writer.writerow({
                    '股票代码': s['code'],
                    '股票名称': s['name'],
                    '评分': s['score'],
                    '最新价': f"{s['price']:.2f}",
                    '涨跌幅': f"{s['change_pct']:.2f}%",
                    'MA5': f"{s['ma5']:.2f}",
                    'MA10': f"{s['ma10']:.2f}",
                    'MA20': f"{s['ma20']:.2f}",
                    '量比': f"{s['volume_ratio']:.2f}",
                    'RSI(6)': f"{s['rsi6']:.1f}",
                    '板块': s['board']
                })
        
        # 保存Markdown
        md_file = f'data/s_level_strict_filtered_{today}.md'
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(f"# {today} S级股票严格筛选结果\n\n")
            f.write(f"**筛选时间**: {today}\n")
            f.write(f"**通过数量**: {len(passed_stocks)}/{len(stocks)} 只\n\n")
            f.write(f"**筛选标准**:\n")
            f.write(f"- ✅ 评分 ≥ 85分\n")
            f.write(f"- ✅ 量比 > 1.5\n")
            f.write(f"- ✅ RSI(6) ∈ (60, 80)\n")
            f.write(f"- ✅ 价格 > MA5\n\n")
            f.write("---\n\n")
            
            # 按板块分组
            boards = {}
            for s in passed_stocks:
                board = s['board']
                if board not in boards:
                    boards[board] = []
                boards[board].append(s)
            
            for board_name, stocks_list in sorted(boards.items()):
                f.write(f"## {board_name} ({len(stocks_list)}只)\n\n")
                f.write("| 序号 | 代码 | 名称 | 评分 | 价格 | MA5 | 量比 | RSI(6) |\n")
                f.write("|------|------|------|------|------|------|------|--------|\n")
                
                for i, s in enumerate(sorted(stocks_list, key=lambda x: -x.get('rsi6', 0)), 1):
                    f.write(f"| {i} | {s['code']} | {s['name']} | {s['score']} | "
                           f"{s['price']:.2f} | {s['ma5']:.2f} | {s['volume_ratio']:.2f} | {s['rsi6']:.1f} |\n")
                f.write("\n")
        
        logger.info(f"✅ 已保存: {result_file}")
        logger.info(f"✅ 已保存: {md_file}")
        logger.info("")
        logger.info("🏆 通过筛选的股票 (按RSI排序):")
        logger.info("")
        
        for i, s in enumerate(sorted(passed_stocks, key=lambda x: -x.get('rsi6', 0)), 1):
            logger.info(f"{i:2d}. {s['name']}({s['code']}) | "
                       f"评分{s['score']} 价格{s['price']:.2f} "
                       f"量比{s['volume_ratio']:.2f} RSI{s['rsi6']:.1f}")
    else:
        logger.info("⚠️  没有股票通过严格筛选")
    
    logger.info("")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
