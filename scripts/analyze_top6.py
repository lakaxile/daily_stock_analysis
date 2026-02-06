#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从扫描日志中提取Top6股票的AI分析结果并推送
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import re
import json
import csv
import logging
from datetime import datetime
from typing import List, Dict, Optional
from src.notification import NotificationService

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def load_top6_stocks() -> List[Dict]:
    """加载严格筛选的6只股票"""
    # 使用筛选时的日期
    csv_file = 'data/s_level_strict_filtered_2026-02-03.csv'
    
    stocks = []
    with open(csv_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            stocks.append({
                'code': row['股票代码'],
                'name': row['股票名称'],
                'score': int(row['评分']),
                'price': float(row['最新价']),
                'change_pct': row['涨跌幅'],
                'ma5': float(row['MA5']),
                'volume_ratio': float(row['量比']),
                'rsi6': float(row['RSI(6)']),
                'board': row['板块']
            })
    
    return stocks


def extract_analysis_from_log(code: str, log_content: str) -> Optional[Dict]:
    """从扫描日志中提取该股票的AI分析结果"""
    try:
        # 查找该股票的LLM解析部分
        pattern = rf'\[LLM解析\] (.*?)\({code}\) 分析完成: (.*?), 评分 (\d+)'
        match = re.search(pattern, log_content)
        
        if not match:
            logger.warning(f"  ⚠️  未找到{code}的分析结果")
            return None
        
        name = match.group(1)
        trend = match.group(2)
        score = int(match.group(3))
        
        # 尝试查找原始JSON response
        # 查找包含 code 的 JSON block
        json_pattern = rf'```json\s*\{{[^}}]*"code":\s*"{code}"[^}}]*\}}```'
        json_matches = re.findall(json_pattern, log_content, re.DOTALL)
        
        analysis_data = {
            'code': code,
            'name': name,
            'score': score,
            'trend': trend
        }
        
        # 如果找到JSON，尝试解析
        if json_matches:
            try:
                json_str = json_matches[0].strip('```json').strip('```').strip()
                data = json.loads(json_str)
                analysis_data.update({
                    'operation': data.get('operation_advice', '持有'),
                    'technical': data.get('technical_analysis', ''),
                    'fundamental': data.get('fundamental_analysis', ''),
                    'risk': data.get('risk_warning', ''),
                    'key_points': data.get('key_points', ''),
                    'buy_reason': data.get('buy_reason', ''),
                    '六维战法': data.get('dashboard', {}).get('six_dimensions', {})
                })
            except:
                pass
        
        return analysis_data
        
    except Exception as e:
        logger.error(f"  ❌ 提取{code}失败: {e}")
        return None


def format_stock_report(stock: Dict, analysis: Optional[Dict]) -> str:
    """格式化单只股票的详细报告"""
    lines = [
        f"## 📊 {stock['name']}({stock['code']})",
        "",
        f"### 基础信息",
        f"- 💰 最新价: ¥{stock['price']:.2f} ({stock['change_pct']})",
        f"- 📈 均线MA5: ¥{stock['ma5']:.2f}",
        f"- 📊 量比: {stock['volume_ratio']:.2f}",
        f"- 🔥 RSI(6): {stock['rsi6']:.1f}",
        f"- 🏢 板块: {stock['board']}",
        "",
    ]
    
    if analysis:
        lines.extend([
            f"### AI分析",
            f"- **综合评分**: {analysis.get('score', stock['score'])} 分",
            f"- **趋势预测**: {analysis.get('trend', '未知')}",
            f"- **操作建议**: {analysis.get('operation', '持有')}",
            "",
        ])
        
        # 六维战法
        six_dim = analysis.get('六维战法', {})
        if six_dim:
            lines.append("### 🎯 六维战法")
            for dim, val in six_dim.items():
                if isinstance(val, dict):
                    score = val.get('score', 0)
                    desc = val.get('description', '')
                    lines.append(f"- **{dim}**: {score}/10 - {desc}")
                else:
                    lines.append(f"- **{dim}**: {val}")
            lines.append("")
        
        # 核心理由
        if analysis.get('buy_reason'):
            lines.append("### 💡 核心逻辑")
            lines.append(analysis['buy_reason'])
            lines.append("")
        
        if analysis.get('key_points'):
            lines.append("### ✨ 关键看点")
            lines.append(analysis['key_points'])
            lines.append("")
        
        if analysis.get('technical'):
            lines.append("### 📈 技术面")
            lines.append(analysis['technical'])
            lines.append("")
        
        if analysis.get('fundamental'):
            lines.append("### 🏢 基本面")
            lines.append(analysis['fundamental'])
            lines.append("")
        
        if analysis.get('risk'):
            lines.append("### ⚠️ 风险提示")
            lines.append(analysis['risk'])
            lines.append("")
    else:
        lines.append("⚠️ 暂无AI分析数据")
        lines.append("")
    
    lines.append("---")
    lines.append("")
    
    return "\n".join(lines)


def main():
    logger.info("="*70)
    logger.info("🎯 Top6股票详细分析报告")
    logger.info("="*70)
    
    # 加载股票列表
    stocks = load_top6_stocks()
    logger.info(f"\n📊 待整理股票: {len(stocks)} 只")
    
    # 加载扫描日志
    logger.info("\n📖 正在读取扫描日志...")
    with open('full_scan_log.txt', 'r', encoding='utf-8') as f:
        log_content = f.read()
    logger.info(f"✅ 日志已加载 ({len(log_content)} 字符)")
    
    # 提取每只股票的分析
    reports = []
    for i, stock in enumerate(stocks, 1):
        logger.info(f"\n[{i}/{len(stocks)}] 处理 {stock['name']}({stock['code']})...")
        
        analysis = extract_analysis_from_log(stock['code'], log_content)
        if analysis:
            logger.info(f"  ✅ 找到AI分析: {analysis.get('score')}分, {analysis.get('trend')}")
        
        report = format_stock_report(stock, analysis)
        reports.append({
            'stock': stock,
            'analysis': analysis,
            'report': report
        })
    
    # 生成汇总报告
    logger.info(f"\n{'='*70}")
    logger.info("📝 生成汇总报告...")
    logger.info(f"{'='*70}")
    
    today = datetime.now().strftime('%Y-%m-%d')
    report_lines = [
        f"# 🎯 严格筛选Top6股票 - 详细分析报告",
        "",
        f"**报告时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**筛选标准**: 评分≥85 | 量比>1.5 | RSI∈(60,80) | 价格>MA5",
        f"**通过率**: 6/115 只 (5.2%)",
        "",
        "---",
        ""
    ]
    
    for r in reports:
        report_lines.append(r['report'])
    
    report_msg = "\n".join(report_lines)
    
    # 保存到文件
    report_file = 'data/top6_detailed_report_2026-02-03.md'
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report_msg)
    
    logger.info(f"\n✅ 报告已保存: {report_file}")
    
    # 推送到企业微信
    logger.info(f"\n{'='*70}")
    logger.info("📤 推送到企业微信...")
    logger.info(f"{'='*70}")
    
    notifier = NotificationService()
    
    try:
        # 发送汇总
        summary = [
            "🎯 **严格筛选Top6股票 - 详细分析报告**",
            "",
            f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "**筛选标准**",
            "✅ 评分≥85分",
            "✅ 量比>1.5",  
            "✅ RSI(6)∈(60,80)",
            "✅ 价格>MA5",
            "",
            f"**通过率**: 6/115 只 (5.2%)",
            "",
            "---",
            "",
            "**通过股票列表**:"
        ]
        
        for i, r in enumerate(reports, 1):
            stock = r['stock']
            analysis = r['analysis']
            if analysis:
                summary.append(
                    f"{i}. **{stock['name']}({stock['code']})** - "
                    f"{analysis.get('score', stock['score'])}分 | "
                    f"RSI{stock['rsi6']:.1f} | "
                    f"{analysis.get('operation', '持有')}"
                )
            else:
                summary.append(
                    f"{i}. **{stock['name']}({stock['code']})** - "
                    f"{stock['score']}分 | RSI{stock['rsi6']:.1f}"
                )
        
        summary.append("")
        summary.append("💡 详细分析报告将分条发送...")
        
        notifier.send("\n".join(summary))
        logger.info("✅ 汇总报告已推送")
        
        # 逐个发送详细报告
        import time
        for i, r in enumerate(reports, 1):
            notifier.send(r['report'])
            logger.info(f"✅ [{i}/{len(reports)}] {r['stock']['name']} 详细报告已推送")
            if i < len(reports):
                time.sleep(2)  # 避免推送过快
        
        logger.info("\n🎉 全部报告推送完成！")
        
    except Exception as e:
        logger.error(f"❌ 推送失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
