#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Append Hot A-level Stocks to Watchlist and Report
"""

import sys
import os
import json
import pandas as pd
import logging
import re

# Add project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.analyzer import GeminiAnalyzer

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
SCAN_FILE = os.path.join(DATA_DIR, 'six_dimension_scan_2026-02-08.csv')
WATCHLIST_FILE = os.path.join(DATA_DIR, 'watchlist.json')
REPORT_FILE = os.path.join(DATA_DIR, 'daily_comprehensive_report_2026-02-08.md')

# The 8 stocks filtered by AI
TARGET_CODES = ['688428', '002957', '002339', '300666', '300812', '300843', '300479', '300523']

def append_to_watchlist(df_targets):
    logger.info("Appending stocks to watchlist...")
    with open(WATCHLIST_FILE, 'r', encoding='utf-8') as f:
        watchlist = json.load(f)
    
    entries = watchlist.get("2026-02-08", [])
    existing_codes = {e['code'] for e in entries}
    
    count = 0
    for _, row in df_targets.iterrows():
        code = str(row['code']).zfill(6)
        if code in existing_codes:
            continue
            
        entry = {
            "code": code,
            "name": row['name'],
            "score": int(row['six_dim_score']),
            "change_pct": round(float(row['change_pct']), 2),
            "price": round(float(row['close']), 2),
            "reason": f"🔥 A级热门 - 评分{row['six_dim_score']}"
        }
        entries.append(entry)
        count += 1
    
    # Sort by score descending
    entries.sort(key=lambda x: x['score'], reverse=True)
    watchlist["2026-02-08"] = entries
    
    with open(WATCHLIST_FILE, 'w', encoding='utf-8') as f:
        json.dump(watchlist, f, indent=2, ensure_ascii=False)
    logger.info(f"Added {count} new stocks to watchlist. Total: {len(entries)}")

def append_to_report(df_targets):
    logger.info("Appending analysis to report...")
    try:
        analyzer = GeminiAnalyzer()
    except:
        logger.error("Analyzer init failed")
        return

    new_section = "\n\n---\n\n## 🔥 A 级热门题材精选\n\n> **筛选逻辑**: 结合市场热点（华为产业链、低空经济、AI算力、新质生产力等）从 A 级股票中优选出的活跃标的。\n"
    
    # Check if this section already exists to avoid duplicates
    with open(REPORT_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
        if "## 🔥 A 级热门题材精选" in content:
            logger.warning("Section already exists in report. Skipping append.")
            # If we want to overwrite, we'd need to rewrite the file. 
            # For now, let's assume if it exists we don't append.
            return

    for idx, row in df_targets.iterrows():
        code = str(row['code']).zfill(6)
        name = row['name']
        score = row['six_dim_score']
        price = row['close']
        pct = row['change_pct']
        details = row['six_dim_details']
        
        logger.info(f"[{idx+1}/{len(df_targets)}] Analyzing {name} ({code})...")
        
        try:
            prompt = f"""
请为 A 级热门股 **{name} ({code})** 撰写精炼分析（Markdown格式，严禁JSON）。

**数据**: 现价 ¥{price}, 涨幅 {pct}%, 评分 {score}/10.
**详情**: {details}

**撰写要求**:
1. **核心题材**: 明确指出其所属的热门板块（如华为、AI、低空等）。
2. **技术亮点**: 简述K线和量能特征。
3. **操作建议**: 给出明确的**支撑位**和**压力位**。
4. 字数 200-300 字。
"""
            response = analyzer._call_api_with_retry(prompt, {'temperature': 0.7})
            
            # Clean up
            response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL).strip()
            
            new_section += f"""
### {idx+1}. {name} ({code}) - {score}分

**📈 市场表现**: 现价 ¥{price:.2f} ({pct:+.2f}%)

{response}

---
"""
        except Exception as e:
             new_section += f"\n### {name} ({code})\n*(分析失败: {e})*\n"

    with open(REPORT_FILE, 'a', encoding='utf-8') as f:
        f.write(new_section)
    logger.info("✅ Analysis appended to report.")

def main():
    if not os.path.exists(SCAN_FILE):
        return

    df = pd.read_csv(SCAN_FILE)
    df['code'] = df['code'].astype(str).str.zfill(6)
    
    # Filter targets
    # Note: reset_index to make idx 0-based in loop
    df_targets = df[df['code'].isin(TARGET_CODES)].reset_index(drop=True)
    
    if df_targets.empty:
        logger.warning("No targets found in scan CSV.")
        return

    # 1. Update Watchlist
    append_to_watchlist(df_targets)
    
    # 2. Append to Report
    append_to_report(df_targets)

if __name__ == "__main__":
    main()
