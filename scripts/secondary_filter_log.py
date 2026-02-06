#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
S级股票二次筛选 - 基于日志数据版本
从full_scan_log.txt中提取技术指标数据进行筛选
"""

import csv
import re
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def extract_technical_data_from_log(code: str, log_content: str) -> Optional[Dict]:
    """从日志中提取股票的技术指标"""
    try:
        # 查找股票的技术面数据
        pattern = rf'\[技术面\] {code}.*?MA5:([\d.]+).*?MA10:([\d.]+).*?MA20:([\d.]+).*?RSI\(6\):([\d.]+)'
        match = re.search(pattern, log_content)
        
        if not match:
            return None
        
        ma5 = float(match.group(1))
        ma10 = float(match.group(2))
        ma20 = float(match.group(3))
        rsi6 = float(match.group(4))
        
        # 查找价格信息
        price_pattern = rf'\[技术面\] {code}.*?价格:([\d.]+)'
        price_match = re.search(price_pattern, log_content)
        price = float(price_match.group(1)) if price_match else 0
        
        # 查找量比信息
        vol_pattern = rf'\[技术面\] {code}.*?量比:([\d.]+)'
        vol_match = re.search(vol_pattern, log_content)
        volume_ratio = float(vol_match.group(1)) if vol_match else 0
        
        return {
            'price': price,
            'ma5': ma5,
            'ma10': ma10,
            'ma20': ma20,
            'rsi6': rsi6,
            'volume_ratio': volume_ratio,
            'price_above_ma5': price > ma5 if price > 0 else False
        }
        
    except Exception as e:
        logger.debug(f"  解析{code}失败: {e}")
        return None


def apply_filters(stock: Dict) -> tuple[bool, List[str]]:
    """应用筛选条件"""
    reasons = []
    
    # 条件1: 评分≥85
    if stock.get('score', 0) < 85:
        reasons.append(f"评分{stock.get('score')}分<85分")
    
    # 条件2: 量比>1.5
    vol_ratio = stock.get('volume_ratio', 0)
    if vol_ratio <= 1.5:
        reasons.append(f"量比{vol_ratio:.2f}≤1.5")
    
    # 条件3: RSI(6)>60且<80
    rsi = stock.get('rsi6', 0)
    if not (60 < rsi < 80):
        reasons.append(f"RSI(6)={rsi:.1f}不在(60,80)")
    
    # 条件4: 价格在MA5之上
    if not stock.get('price_above_ma5', False):
        reasons.append("价格未站上MA5")
    
    return len(reasons) == 0, reasons


def main():
    logger.info("=" * 70)
    logger.info("🔍 S级股票二次严格筛选 (基于日志数据)")
    logger.info("=" * 70)
    logger.info("")
    
    # 读取日志
    with open('full_scan_log.txt', 'r', encoding='utf-8') as f:
        log_content = f.read()
    
    logger.info("✅ 已加载扫描日志")
    
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
    
    # 逐个提取并筛选
    passed_stocks = []
    failed_stocks = []
    no_data_count = 0
    
    for i, stock in enumerate(stocks, 1):
        logger.info(f"[{i}/{len(stocks)}] 分析 {stock['name']}({stock['code']})...")
        
        tech_data = extract_technical_data_from_log(stock['code'], log_content)
        
        if not tech_data:
            no_data_count += 1
            failed_stocks.append({**stock, 'reason': '日志中无技术数据'})
            logger.info(f"  ⚠️  日志中未找到技术数据")
            continue
        
        # 合并数据
        stock.update(tech_data)
        
        # 应用筛选
        passed, reasons = apply_filters(stock)
        
        if passed:
            passed_stocks.append(stock)
            logger.info(f"  ✅ 通过 - 量比:{stock['volume_ratio']:.2f} | RSI:{stock['rsi6']:.1f} | 价格/MA5:{stock['price']:.2f}/{stock['ma5']:.2f}")
        else:
            stock['reason'] = '; '.join(reasons)
            failed_stocks.append(stock)
            logger.info(f"  ❌ 淘汰 - {stock['reason']}")
    
    logger.info("")
    logger.info("=" * 70)
    logger.info(f"🎯 筛选结果: {len(passed_stocks)}/{len(stocks)} 只通过")
    logger.info(f"📊 数据统计: {no_data_count} 只无技术数据, {len(failed_stocks)-no_data_count} 只被淘汰")
    logger.info("=" * 70)
    logger.info("")
    
    if passed_stocks:
        # 保存结果
        result_file = f'data/s_level_strict_filtered_{today}.csv'
        md_file = f'data/s_level_strict_filtered_{today}.md'
        
        # CSV格式
        with open(result_file, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                '股票代码', '股票名称', '评分', '最新价', 'MA5', 'MA10', 'MA20',
                '量比', 'RSI(6)', '板块'
            ])
            writer.writeheader()
            
            for s in sorted(passed_stocks, key=lambda x: -x.get('rsi6', 0)):
                writer.writerow({
                    '股票代码': s['code'],
                    '股票名称': s['name'],
                    '评分': s['score'],
                    '最新价': f"{s['price']:.2f}",
                    'MA5': f"{s['ma5']:.2f}",
                    'MA10': f"{s['ma10']:.2f}",
                    'MA20': f"{s['ma20']:.2f}",
                    '量比': f"{s['volume_ratio']:.2f}",
                    'RSI(6)': f"{s['rsi6']:.1f}",
                    '板块': s['board']
                })
        
        # Markdown格式
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(f"# {today} S级股票严格筛选结果\\n\\n")
            f.write(f"**筛选时间**: {today}\\n")
            f.write(f"**通过数量**: {len(passed_stocks)}/{len(stocks)} 只\\n")
            f.write(f"**筛选标准**:\\n")
            f.write(f"- ✅ 评分 ≥ 85分\\n")
            f.write(f"- ✅ 量比 > 1.5\\n")
            f.write(f"- ✅ RSI(6) ∈ (60, 80)\\n")
            f.write(f"- ✅ 价格 > MA5\\n\\n")
            f.write("---\\n\\n")
            
            # 按板块分组
            boards = {}
            for s in passed_stocks:
                board = s['board']
                if board not in boards:
                    boards[board] = []
                boards[board].append(s)
            
            for board_name, stocks_list in sorted(boards.items()):
                f.write(f"## {board_name} ({len(stocks_list)}只)\\n\\n")
                f.write("| 序号 | 代码 | 名称 | 评分 | 价格 | MA5 | 量比 | RSI(6) |\\n")
                f.write("|------|------|------|------|------|------|------|--------|\\n")
                
                for i, s in enumerate(sorted(stocks_list, key=lambda x: -x.get('rsi6', 0)), 1):
                    f.write(f"| {i} | {s['code']} | {s['name']} | {s['score']} | "
                           f"{s['price']:.2f} | {s['ma5']:.2f} | {s['volume_ratio']:.2f} | {s['rsi6']:.1f} |\\n")
                f.write("\\n")
        
        logger.info(f"✅ CSV结果: {result_file}")
        logger.info(f"✅ MD结果: {md_file}")
        logger.info("")
        logger.info("🏆 通过筛选的股票 (按RSI排序):")
        logger.info("")
        
        for i, s in enumerate(sorted(passed_stocks, key=lambda x: -x.get('rsi6', 0)), 1):
            logger.info(f"{i:2d}. {s['name']}({s['code']}) | "
                       f"{s['score']}分 | 价格{s['price']:.2f} | "
                       f"量比{s['volume_ratio']:.2f} | RSI{s['rsi6']:.1f}")
    else:
        logger.info("⚠️  没有股票通过严格筛选")
    
    logger.info("")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
