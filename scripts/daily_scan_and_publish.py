#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
六维策略: 全自动扫描 + 发布 + AI报告
用法: python3 scripts/daily_scan_and_publish.py [日期]
      日期可选，默认今天
"""

import sys
import os
import json
import re
import pandas as pd
import logging
import time
import concurrent.futures
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.strategy_scanner import SixDimensionScanner
from src.analyzer import GeminiAnalyzer

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
os.makedirs(DATA_DIR, exist_ok=True)

TODAY = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime('%Y-%m-%d')


# ============================================================
# Step 1: 全市场扫描
# ============================================================
def run_full_scan():
    logger.info("=" * 60)
    logger.info(f"🚀 六维策略全市场扫描 - {TODAY}")
    logger.info("=" * 60)

    # 市场环境评估
    scanner = SixDimensionScanner(market_score=10)
    is_good, reason = scanner.check_market_environment()

    if is_good:
        market_score = 9
        logger.info(f"✅ 市场环境良好: {reason}")
    else:
        if "未站上MA20" in reason and "MA5未上穿MA10" in reason:
            market_score = 4
        else:
            market_score = 6
        logger.info(f"⚠️ 市场环境偏弱: {reason} (评分: {market_score})")

    scanner = SixDimensionScanner(market_score=market_score)
    stock_list = sorted(list(set(scanner.get_stock_list())))
    logger.info(f"📋 待扫描: {len(stock_list)} 只")

    results = []
    processed = 0
    start = datetime.now()

    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        future_to_code = {executor.submit(scanner.fetch_stock_data, code): code for code in stock_list}
        for future in concurrent.futures.as_completed(future_to_code):
            processed += 1
            try:
                data = future.result()
                if data:
                    score, details = scanner.calculate_six_dimensions(data)
                    if score >= 6:
                        results.append({**data, 'six_dim_score': score, 'six_dim_details': details})
                        if score >= 8:
                            logger.info(f"🏆 S级: {data['name']}({future_to_code[future]}) {score}分 {data['change_pct']:+.2f}%")
            except Exception:
                pass
            if processed % 500 == 0:
                elapsed = (datetime.now() - start).total_seconds()
                logger.info(f"进度: {processed}/{len(stock_list)} ({processed/len(stock_list)*100:.1f}%) - {processed/elapsed:.0f}只/秒 - 发现{len(results)}只")

    results.sort(key=lambda x: -x['six_dim_score'])

    # 保存CSV
    output_file = os.path.join(DATA_DIR, f'six_dimension_scan_{TODAY}.csv')
    if results:
        df = pd.DataFrame(results)
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        logger.info(f"✅ 扫描结果已保存: {output_file} ({len(results)} 只)")

    s_level = [r for r in results if r['six_dim_score'] >= 8]
    a_level = [r for r in results if 6 <= r['six_dim_score'] < 8]
    logger.info(f"📊 S级: {len(s_level)} 只, A级: {len(a_level)} 只")

    return results, output_file


# ============================================================
# Step 2: 更新 Watchlist
# ============================================================
def update_watchlist(results):
    s_stocks = [r for r in results if r['six_dim_score'] >= 8]

    if not s_stocks:
        logger.warning("无 S 级股票，跳过 watchlist 更新")
        return s_stocks

    watchlist_file = os.path.join(DATA_DIR, 'watchlist.json')
    watchlist = {}
    if os.path.exists(watchlist_file):
        with open(watchlist_file, 'r', encoding='utf-8') as f:
            watchlist = json.load(f)

    entries = []
    for s in s_stocks:
        code = str(s['code']).zfill(6)
        entries.append({
            "code": code,
            "name": s['name'],
            "score": int(s['six_dim_score']),
            "change_pct": round(float(s.get('change_pct', 0)), 2),
            "price": round(float(s.get('close', 0)), 2),
            "price": round(float(s.get('close', 0)), 2),
            "reason": f"六维评分 {int(s['six_dim_score'])}/10",
            "buy_zone": s['six_dim_details'].get('建议', '')
        })

    watchlist[TODAY] = entries
    sorted_wl = dict(sorted(watchlist.items(), reverse=True))

    with open(watchlist_file, 'w', encoding='utf-8') as f:
        json.dump(sorted_wl, f, indent=2, ensure_ascii=False)

    logger.info(f"✅ watchlist.json 已更新: {TODAY} ({len(entries)} 只 S级)")
    return s_stocks


# ============================================================
# Step 3: 生成 AI 综合报告
# ============================================================
def generate_report(s_stocks):
    if not s_stocks:
        report_file = os.path.join(DATA_DIR, f'daily_comprehensive_report_{TODAY}.md')
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(f"# 🤖 AI 综合分析报告 - {TODAY}\n\n今日未发现 S 级股票。市场环境可能偏弱，建议观望。")
        return

    analyzer = GeminiAnalyzer()

    report = f"""# 🤖 AI 综合分析报告 - {TODAY}

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**策略**: 六维真强势策略 (S级精选)

## 🎯 今日精选 S级股票

本期共选出 **{len(s_stocks)}** 只 S级股票，均满足"趋势、K线、量能、分时、盘口、尾盘"六维高分标准。

> **风险提示**: 本报告由 AI 自动生成，仅供参考，不构成投资建议。

---
"""

    for i, s in enumerate(s_stocks):
        code = str(s['code']).zfill(6)
        name = s['name']
        score = s['six_dim_score']
        change_pct = s.get('change_pct', 0)
        price = s.get('close', 0)
        details = s.get('six_dim_details', '')

        logger.info(f"[{i+1}/{len(s_stocks)}] AI分析 {name} ({code})...")

        try:
            prompt = f"""
请作为一名资深 A 股分析师，为 S 级强势股 **{name} ({code})** 撰写一份**深度研报**（Markdown格式）。

**当前数据**:
- 收盘价: ¥{price}
- 涨跌幅: {change_pct}%
- 六维评分: {score}/10
- 涨跌幅: {change_pct}%
- 六维评分: {score}/10
- 得分详情: {details}
- 建议低吸: {details.get('建议', '无')}

**撰写要求**:
1.  **严禁输出 JSON** 或 代码块。只输出易读的 Markdown 文本。
2.  **字数要求**：400-600字。内容需详实，拒绝空洞。
3.  **结构要求**：
    *   **核心逻辑**: 结合市场热点和六维评分，深度解析为何该股强势。
    *   **技术面复盘**: K线形态、均线系统、量能配合。
    *   **实战策略**: 给出明确的 **买入区间**、**止损位** 和 **目标位**。
    *   **风险提示**: 潜在风险。

请用专业投资顾问语气撰写。
"""
            text = analyzer._call_api_with_retry(prompt, {'temperature': 0.7})
            text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()

            report += f"""
### {i+1}. {name} ({code}) - 评分: {score}

**📈 市场表现**: 现价 ¥{price:.2f} ({change_pct:+.2f}%)
**🎯 操作建议**: {details.get('建议', '无')}

{text}

---
"""
        except Exception as e:
            logger.error(f"AI分析 {code} 失败: {e}")
            report += f"\n### {i+1}. {name} ({code})\n\n*(AI 分析暂时不可用)*\n\n---\n"

    report += """
## 📝 总结

以上是今日市场中最强势的标的。建议结合明日开盘情况（观察竞价量比）决定是否介入。

**观察重点**:
1. 开盘是否大幅高开（>3%需谨慎）
2. 量能是否持续放大
3. 大盘环境是否配合
"""

    report_file = os.path.join(DATA_DIR, f'daily_comprehensive_report_{TODAY}.md')
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    logger.info(f"✅ 报告已生成: {report_file}")


# ============================================================
# Main
# ============================================================
if __name__ == "__main__":
    logger.info(f"📅 目标日期: {TODAY}")

    # 1. 全市场扫描
    results, scan_file = run_full_scan()

    # 2. 更新 watchlist
    s_stocks = update_watchlist(results)

    # 3. 生成 AI 报告
    generate_report(s_stocks)

    logger.info("\n🏁 全流程完成！")
