#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Review performance of stocks recommended on 2026-02-10.
Analyzes their performance on the following trading day (2026-02-11).
"""

import sys
import os
import json
import yfinance as yf
import pandas as pd
from datetime import datetime
import numpy as np

# Add project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
WATCHLIST_FILE = os.path.join(DATA_DIR, 'watchlist.json')
US_WATCHLIST_FILE = os.path.join(DATA_DIR, 'us_watchlist.json')

def get_market_data(code):
    suffix = ".SS" if code.startswith("6") else ".SZ"
    symbol = f"{code}{suffix}"
    try:
        # Fetch 5 days to be safe
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="5d")
        if len(hist) < 2:
            return None
        return hist
    except Exception as e:
        print(f"Error fetching {code}: {e}")
        return None

def analyze_picks(date_str, strategy_name, picks):
    print(f"\n{'='*60}")
    print(f"🔍 Strategy: {strategy_name} (Recommended on {date_str})")
    print(f"{'='*60}")
    
    if not picks:
        print("No picks found.")
        return

    results = []
    
    print(f"{'Code':<8} {'Name':<10} {'Rec Price':<10} {'Open%':<8} {'High%':<8} {'Close%':<8} {'Result'}")
    print("-" * 70)

    total_return = 0
    win_count = 0
    valid_count = 0
    
    for stock in picks:
        code = stock['code']
        name = stock['name']
        rec_price = float(stock.get('price', 0)) # Close price on recommendation day
        
        hist = get_market_data(code)
        if hist is None or hist.empty:
            print(f"{code:<8} {name:<10} Data N/A")
            continue

        # We need data for the day AFTER recommendations (T+1)
        # Recommendation date: 2026-02-10
        # Target date: 2026-02-11 (or next transaction day)
        
        # Convert index strings to YYYY-MM-DD
        hist.index = hist.index.strftime('%Y-%m-%d')
        
        if '2026-02-10' not in hist.index:
            print(f"{code:<8} {name:<10} No data for {date_str}")
            continue
            
        rec_day_data = hist.loc['2026-02-10']
        
        # Determine next trading day
        loc = hist.index.get_loc('2026-02-10')
        if loc + 1 >= len(hist):
             print(f"{code:<8} {name:<10} No T+1 data yet")
             continue
             
        next_day_data = hist.iloc[loc + 1]
        next_date = hist.index[loc + 1]
        
        # Calculate returns based on Previous Close (Recommendation Price)
        prev_close = rec_day_data['Close']
        
        open_pct = (next_day_data['Open'] - prev_close) / prev_close * 100
        high_pct = (next_day_data['High'] - prev_close) / prev_close * 100
        close_pct = (next_day_data['Close'] - prev_close) / prev_close * 100
        
        result_emoji = "🔴" if close_pct < 0 else ("🟢" if close_pct > 0 else "⚪️")
        if close_pct > 9.5: result_emoji = "🔥" # Limit Up likely
        
        print(f"{code:<8} {name:<10} {prev_close:<10.2f} {open_pct:>7.2f}% {high_pct:>7.2f}% {close_pct:>7.2f}% {result_emoji}")
        
        results.append({
            'code': code,
            'name': name,
            'close_pct': close_pct,
            'high_pct': high_pct
        })
        
        total_return += close_pct
        if close_pct > 0:
            win_count += 1
        valid_count += 1

    if valid_count > 0:
        avg_return = total_return / valid_count
        win_rate = (win_count / valid_count) * 100
        print("-" * 70)
        print(f"📊 Summary for {strategy_name}:")
        print(f"   Count: {valid_count}")
        print(f"   Avg Return: {avg_return:.2f}%")
        print(f"   Win Rate: {win_rate:.1f}%")
        
        # Sort by best performance
        results.sort(key=lambda x: x['close_pct'], reverse=True)
        best = results[0]
        worst = results[-1]
        print(f"   🏆 Best: {best['name']} ({best['close_pct']:.2f}%)")
        print(f"   💣 Worst: {worst['name']} ({worst['close_pct']:.2f}%)")
    else:
        print("No valid T+1 data available.")

def main():
    date_str = "2026-02-10"
    
    # 1. Review Six Dimension Strategy
    if os.path.exists(WATCHLIST_FILE):
        with open(WATCHLIST_FILE, 'r') as f:
            data = json.load(f)
            picks = data.get(date_str, [])
            analyze_picks(date_str, "Six-Dimension Strategy (S-Level)", picks)

    # 2. Review US-A Strategy
    if os.path.exists(US_WATCHLIST_FILE):
        with open(US_WATCHLIST_FILE, 'r') as f:
            data = json.load(f)
            picks = data.get(date_str, [])
            analyze_picks(date_str, "US-A Cross-Market Strategy", picks)

if __name__ == "__main__":
    main()
