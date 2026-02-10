#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
发布 S 级选股结果并生成 AI 分析报告
1. 读取 2026-02-08 的扫描结果
2. 更新 watchlist.json
3. 生成 daily_comprehensive_report_2026-02-08.md
"""

import sys
import os
import json
import pandas as pd
from datetime import datetime
import logging

# Add project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.analyzer import GeminiAnalyzer

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
SCAN_FILE = os.path.join(DATA_DIR, 'six_dimension_scan_2026-02-08.csv')
WATCHLIST_FILE = os.path.join(DATA_DIR, 'watchlist.json')
REPORT_FILE = os.path.join(DATA_DIR, 'daily_comprehensive_report_2026-02-08.md')

def update_watchlist(s_stocks):
    """更新 watchlist.json"""
    logger.info("Updating watchlist.json...")
    
    if not os.path.exists(WATCHLIST_FILE):
        watchlist = {}
    else:
        with open(WATCHLIST_FILE, 'r', encoding='utf-8') as f:
            try:
                watchlist = json.load(f)
            except json.JSONDecodeError:
                watchlist = {}
    
    date_key = "2026-02-08"
    entries = []
    
    for _, row in s_stocks.iterrows():
        # 安全获取字段
        code = str(row['code']).zfill(6) # 确保6位代码
        name = row['name']
        score = int(row['six_dim_score'])
        change_pct = float(row['change_pct']) if 'change_pct' in row else 0.0
        price = float(row['close']) if 'close' in row else 0.0
        
        # 处理可能的nan
        if pd.isna(change_pct): change_pct = 0.0
        if pd.isna(price): price = 0.0
        
        entry = {
            "code": code,
            "name": name,
            "score": score,
            "change_pct": round(change_pct, 2),
            "price": round(price, 2),
            "reason": f"六维评分 {score}/10"
        }
        entries.append(entry)
        
    watchlist[date_key] = entries
    
    # 排序：日期倒序
    # 但json是dict，python 3.7+ 保持插入顺序。我们可以尝试重排key
    sorted_watchlist = dict(sorted(watchlist.items(), reverse=True))
    
    with open(WATCHLIST_FILE, 'w', encoding='utf-8') as f:
        json.dump(sorted_watchlist, f, indent=2, ensure_ascii=False)
    
    logger.info(f"✅ Watchlist updated for {date_key} with {len(entries)} stocks.")

def generate_report(s_stocks):
    """生成 AI 分析报告"""
    logger.info("Generating AI Analysis Report...")
    
    # 实例化 Analyzer
    try:
        analyzer = GeminiAnalyzer()
    except Exception as e:
        logger.error(f"Failed to initialize analyzer: {e}")
        return

    # 报告头部
    report_content = f"""# 🤖 AI 综合分析报告 - 2026-02-08

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**策略**: 六维真强势策略 (S级精选)

## 🎯 今日精选 S级股票

本期共选出 **{len(s_stocks)}** 只 S级股票，均满足“趋势、K线、量能、分时、盘口、尾盘”六维高分标准。

> **风险提示**: 本报告由 AI 自动生成，仅供参考，不构成投资建议。

---
"""
    
    # 逐个分析
    for idx, row in s_stocks.iterrows():
        code = str(row['code']).zfill(6)
        name = row['name']
        score = row['six_dim_score']
        change_pct = row['change_pct']
        price = row['close']
        details = row['six_dim_details']
        
        logger.info(f"[{idx+1}/{len(s_stocks)}] Analyzing {name} ({code})...")
        
        try:
            prompt = f"""
请作为一名资深 A 股分析师，为 S 级强势股 **{name} ({code})** 撰写一份**深度研报**（Markdown格式）。

**当前数据**:
- 收盘价: ¥{price}
- 涨跌幅: {change_pct}%
- 六维评分: {score}/10
- 得分详情: {details}

**撰写要求**:
1.  **严禁输出 JSON** 或 代码块。只输出易读的 Markdown 文本。
2.  **字数要求**：400-600字。内容需详实，拒绝空洞。
3.  **结构要求**：
    *   **核心逻辑**: 结合市场热点和六维评分，深度解析为何该股强势（如：主力资金意图、板块效应）。
    *   **技术面复盘**: 详细分析 K 线形态（如：突破、反包）、均线系统（多头排列？）、量能配合（量比含义）。
    *   **资金面分析**: 结合分时走势和振幅，分析主力控盘程度。
    *   **实战策略**: 给出明确的 **买入区间**（精确到小数点后两位）、**止损位** 和 **第一/二目标位**。
    *   **风险提示**: 潜在的技术背离或板块退潮风险。

请用专业的投资顾问语气撰写，富有感染力。
"""
            # 调用 AI (使用默认配置)
            analysis_text = analyzer._call_api_with_retry(prompt, {'temperature': 0.7})
            
            # 清理可能的 <think> 标签 (DeepSeek 特性)
            import re
            analysis_text = re.sub(r'<think>.*?</think>', '', analysis_text, flags=re.DOTALL).strip()
            
            report_content += f"""
### {idx+1}. {name} ({code}) - 评分: {score}

**📈 市场表现**: 现价 ¥{price:.2f} ({change_pct:+.2f}%)

{analysis_text}

---
"""
        except Exception as e:
            logger.error(f"Failed to analyze {code}: {e}")
            report_content += f"""
### {idx+1}. {name} ({code})

*(AI 分析暂时不可用)*

---
"""
            
    # 结尾
    report_content += """
## 📝 总结

以上是今日市场中最强势的标的。建议结合明日开盘情况（观察竞价量比）决定是否介入。

**观察重点**:
1. 开盘是否大幅高开（>3%需谨慎）。
2. 量能是否持续放大。
3. 大盘环境是否配合。
"""

    # 保存文件
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write(report_content)
        
    logger.info(f"✅ Report generated: {REPORT_FILE}")

def main():
    if not os.path.exists(SCAN_FILE):
        logger.error(f"Scan file not found: {SCAN_FILE}")
        return

    try:
        df = pd.read_csv(SCAN_FILE)
    except Exception as e:
        logger.error(f"Error reading CSV: {e}")
        return
        
    # 筛选 S 级
    s_stocks = df[df['six_dim_score'] >= 8]
    
    if s_stocks.empty:
        logger.warning("No S-level stocks found in the scan file.")
        
        # 即使没有 S 级，也可能需要生成一个空的报告或者说明
        with open(REPORT_FILE, 'w', encoding='utf-8') as f:
             f.write(f"# 🤖 AI 综合分析报告 - 2026-02-08\n\n今日未发现满足 S 级标准的股票。市场环境可能较为弱势，建议观望。")
        return
        
    logger.info(f"Found {len(s_stocks)} S-level stocks.")
    
    # 1. Update Watchlist
    update_watchlist(s_stocks)
    
    # 2. Generate Report
    generate_report(s_stocks)

if __name__ == "__main__":
    main()
