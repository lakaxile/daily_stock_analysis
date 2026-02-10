#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
筛选 A 级股票中的热门题材股 (重试版)
"""

import sys
import os
import pandas as pd
import logging
import re

# Add project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.analyzer import GeminiAnalyzer

logging.basicConfig(level=logging.INFO)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
SCAN_FILE = os.path.join(DATA_DIR, 'six_dimension_scan_2026-02-08.csv')

def main():
    if not os.path.exists(SCAN_FILE):
        print(f"❌ Scan file not found: {SCAN_FILE}")
        return

    df = pd.read_csv(SCAN_FILE)
    
    # Filter A-level
    a_stocks = df[(df['six_dim_score'] >= 6) & (df['six_dim_score'] < 8)]
    
    if a_stocks.empty:
        print("No A-level stocks found.")
        return
        
    print(f"Found {len(a_stocks)} A-level stocks. Filtering for hot themes...")
    
    # Limit list length to avoid context window issues
    # Just take top 30 by score/change_pct
    stocks_to_check = a_stocks.sort_values(by='change_pct', ascending=False).head(30)
    
    stock_list_lines = []
    for _, row in stocks_to_check.iterrows():
        name = row['name']
        code = str(row['code']).zfill(6)
        pct = row['change_pct']
        stock_list_lines.append(f"{code} {name} (+{pct:.2f}%)")
        
    stock_list_str = "\n".join(stock_list_lines)
    
    prompt = f"""
You are a Chinese stock market expert.
Please filter the following list of A-share stocks and identify 5-8 stocks that belong to the **CURRENT HOTTEST THEMES** (e.g., Low Altitude Economy, AI/Computing, Huawei Chain, M&A/Restructuring, New Productivity, etc.).

Stock List:
{stock_list_str}

**OUTPUT REQUIREMENT:**
1. Output ONLY a Markdown Table.
2. Columns: 代码 (Code), 名称 (Name), 涨幅 (Change), 核心题材 (Theme), 推荐理由 (Reason).
3. Do NOT output JSON. Do NOT output Code Blocks.
4. Use Chinese for the content.

Example Output:
| 代码 | 名称 | 涨幅 | 核心题材 | 推荐理由 |
|---|---|---|---|---|
| 000000 | 某某股份 | +9.9% | 低空经济 | 龙头股... |
"""
    
    analyzer = GeminiAnalyzer()
    try:
        response = analyzer._call_api_with_retry(prompt, {'temperature': 0.3})
        
        # Clean up response (remove <think> etc)
        response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL).strip()
        response = re.sub(r'```json.*?```', '', response, flags=re.DOTALL).strip() # Safety net
        
        print("\n" + "="*50)
        print("🔥 Filtered Hot Stocks")
        print("="*50)
        print(response)
        
        # Save
        with open(os.path.join(DATA_DIR, 'a_level_hot_picks_2026-02-08.md'), 'w', encoding='utf-8') as f:
            f.write("# 🔥 A 级热门题材股精选\n\n")
            f.write(response)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
