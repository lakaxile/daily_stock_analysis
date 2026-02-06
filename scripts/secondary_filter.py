#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
S级股票二次严格筛选
筛选条件：
1. 评分≥85分
2. 成交量放大倍数>1.5
3. RSI(6)>60且<80
4. 价格在MA5之上
5. 主力资金净流入（如有数据）
"""

import csv
import logging
from datetime import datetime
from typing import List, Dict
import akshare as ak

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def get_stock_details(code: str) -> Dict:
    """获取股票详细技术指标"""
    try:
        # 添加后缀
        if code.startswith('6'):
            full_code = f"{code}.SS"
        else:
            full_code = f"{code}.SZ"
        
        # 获取实时数据
        df = ak.stock_zh_a_spot_em()
        stock_data = df[df['代码'] == code]
        
        if stock_data.empty:
            return None
        
        row = stock_data.iloc[0]
        
        # 提取关键指标
        result = {
            'code': code,
            'name': row.get('名称', ''),
            'price': float(row.get('最新价', 0)),
            'change_pct': float(row.get('涨跌幅', 0)),
            'volume_ratio': float(row.get('量比', 0)),
            'turnover_rate': float(row.get('换手率', 0)),
            'amplitude': float(row.get('振幅', 0)),
        }
        
        # 尝试获取RSI和均线（需要历史数据）
        try:
            import pandas as pd
            hist_df = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq")
            if not hist_df.empty and len(hist_df) >= 20:
                # 计算MA5
                hist_df['ma5'] = hist_df['收盘'].rolling(window=5).mean()
                latest = hist_df.iloc[-1]
                result['ma5'] = float(latest['ma5'])
                result['price_above_ma5'] = result['price'] > result['ma5']
                
                # 计算成交量放大倍数（今日vs 5日均量）
                hist_df['vol_ma5'] = hist_df['成交量'].rolling(window=5).mean()
                latest_vol = float(latest['成交量'])
                vol_ma5 = float(latest['vol_ma5'])
                result['volume_amplification'] = latest_vol / vol_ma5 if vol_ma5 > 0 else 0
                
                # 简易RSI(6)计算
                close_prices = hist_df['收盘'].tail(14).values
                deltas = [close_prices[i] - close_prices[i-1] for i in range(1, len(close_prices))]
                gains = [d if d > 0 else 0 for d in deltas]
                losses = [-d if d < 0 else 0 for d in deltas]
                
                avg_gain = sum(gains[-6:]) / 6 if len(gains) >= 6 else 0
                avg_loss = sum(losses[-6:]) / 6 if len(losses) >= 6 else 0
                
                if avg_loss == 0:
                    result['rsi6'] = 100
                else:
                    rs = avg_gain / avg_loss
                    result['rsi6'] = 100 - (100 / (1 + rs))
            else:
                result['ma5'] = 0
                result['price_above_ma5'] = False
                result['volume_amplification'] = 0
                result['rsi6'] = 0
        except Exception as e:
            logger.warning(f"  ⚠️  {code} 历史数据获取失败: {e}")
            result['ma5'] = 0
            result['price_above_ma5'] = False
            result['volume_amplification'] = 0
            result['rsi6'] = 0
        
        return result
        
    except Exception as e:
        logger.error(f"  ❌ {code} 数据获取失败: {e}")
        return None


def apply_filters(stock: Dict, min_score: int = 85) -> tuple[bool, List[str]]:
    """
    应用筛选条件
    返回: (是否通过, 未通过原因列表)
    """
    reasons = []
    
    # 条件1: 评分≥85
    if stock.get('score', 0) < min_score:
        reasons.append(f"评分{stock.get('score')}分<{min_score}分")
    
    # 条件2: 成交量放大倍数>1.5
    vol_amp = stock.get('volume_amplification', 0)
    if vol_amp <= 1.5:
        reasons.append(f"量比{vol_amp:.2f}≤1.5")
    
    # 条件3: RSI(6)>60且<80
    rsi = stock.get('rsi6', 0)
    if not (60 < rsi < 80):
        reasons.append(f"RSI(6)={rsi:.1f}不在(60,80)区间")
    
    # 条件4: 价格在MA5之上
    if not stock.get('price_above_ma5', False):
        reasons.append("价格未站上MA5")
    
    passed = len(reasons) == 0
    return passed, reasons


def main():
    logger.info("=" * 70)
    logger.info("🔍 S级股票二次严格筛选")
    logger.info("=" * 70)
    logger.info("")
    
    # 读取今日S级股票列表
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
        logger.info(f"[{i}/{len(stocks)}] 分析 {stock['name']}({stock['code']})...")
        
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
            logger.info(f"  ✅ 通过 - 量比:{stock['volume_amplification']:.2f} | RSI:{stock['rsi6']:.1f} | 价格/MA5:{stock['price']:.2f}/{stock['ma5']:.2f}")
        else:
            stock['reason'] = '; '.join(reasons)
            failed_stocks.append(stock)
            logger.info(f"  ❌ 淘汰 - {stock['reason']}")
        
        logger.info("")
    
    # 输出结果
    logger.info("=" * 70)
    logger.info(f"🎯 筛选结果: {len(passed_stocks)}/{len(stocks)} 只通过")
    logger.info("=" * 70)
    logger.info("")
    
    if passed_stocks:
        # 保存结果
        result_file = f'data/s_level_strict_filtered_{today}.csv'
        with open(result_file, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                '股票代码', '股票名称', '评分', '最新价', '涨跌幅', 
                'MA5', '量比', 'RSI(6)', '换手率', '振幅', '板块'
            ])
            writer.writeheader()
            
            for s in passed_stocks:
                writer.writerow({
                    '股票代码': s['code'],
                    '股票名称': s['name'],
                    '评分': s['score'],
                    '最新价': f"{s['price']:.2f}",
                    '涨跌幅': f"{s['change_pct']:.2f}%",
                    'MA5': f"{s['ma5']:.2f}",
                    '量比': f"{s['volume_amplification']:.2f}",
                    'RSI(6)': f"{s['rsi6']:.1f}",
                    '换手率': f"{s['turnover_rate']:.2f}%",
                    '振幅': f"{s['amplitude']:.2f}%",
                    '板块': s['board']
                })
        
        logger.info(f"✅ 结果已保存: {result_file}")
        logger.info("")
        logger.info("🏆 通过筛选的股票:")
        for i, s in enumerate(passed_stocks, 1):
            logger.info(f"{i:2d}. {s['name']}({s['code']}) | {s['score']}分 | 量比{s['volume_amplification']:.2f} | RSI{s['rsi6']:.1f}")
    else:
        logger.info("⚠️  没有股票通过严格筛选")


if __name__ == "__main__":
    main()
