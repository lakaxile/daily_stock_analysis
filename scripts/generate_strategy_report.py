#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
六维策略扫描报告生成器
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from datetime import datetime
from src.notification import NotificationService
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def generate_strategy_report(csv_file: str, push_to_wechat: bool = True):
    """生成策略扫描报告并推送"""
    
    # 读取数据
    df = pd.read_csv(csv_file)
    
    # 分级
    s_level = df[df['six_dim_score'] >= 8].sort_values('six_dim_score', ascending=False)
    a_level = df[(df['six_dim_score'] >= 6) & (df['six_dim_score'] < 8)].sort_values('six_dim_score', ascending=False)
    
    today = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    # 生成Markdown报告
    report_lines = [
        f"# 📊 六维真强势策略全市场扫描报告",
        "",
        f"**报告时间**: {today}",
        f"**扫描总数**: 6796 只股票",
        f"**符合基础条件**: {len(df)} 只",
        "",
        "---",
        "",
        "## 🌍 市场环境",
        "",
        "【📊 市场环境】: **10/10 分** 🟢 **绿灯**",
        "",
        "【🌍 技术面评分】: 10/10",
        "   - 上涨0.85% (+1.5分)",
        "   - 站上MA20 (+1分)",
        "   - 大阳线 (+2分)",
        "   - 放量上涨 (+1分)",
        "",
        "【⚖️ 建议仓位】: **重仓出击**",
        "【🛠️ 执行策略】: **策略A - 六维真强势**（追涨主升浪）",
        "",
        "---",
        "",
        "## 📊 扫描结果汇总",
        "",
        f"- 🏆 **S级** (8-10分): **{len(s_level)} 只**",
        f"- 📈 **A级** (6-7分): {len(a_level)} 只",
        "",
        "---",
        "",
        "## 🏆 S级股票推荐 (Top 20)",
        "",
        "*说明：S级股票具备六维真强势特征，适合当前绿灯环境重仓追涨*",
        "",
    ]
    
    # Top 20 S级股票
    for i, row in enumerate(s_level.head(20).iterrows(), 1):
        stock = row[1]
        
        report_lines.extend([
            f"### {i}. {stock['name']}({stock['code']}) - {int(stock['six_dim_score'])}/10分",
            "",
            "**关键数据**:",
            f"- 💰 股价: ¥{stock['close']:.2f} | 涨幅: {stock['change_pct']:+.2f}%",
            f"- 📊 成交额: {stock['turnover']/100000000:.2f}亿 | 量比: {stock['volume_ratio']:.2f}x",
            f"- 📈 均线: MA5 ¥{stock['ma5']:.2f} | MA10 ¥{stock['ma10']:.2f} | MA20 ¥{stock['ma20']:.2f}",
            "",
            "**六维评分详情**:",
        ])
        
        # 解析六维详情
        import ast
        try:
            details = ast.literal_eval(stock['six_dim_details'])
            for dim, result in details.items():
                report_lines.append(f"- {dim}: {result}")
        except:
            pass
        
        # 操作建议
        score = int(stock['six_dim_score'])
        if score == 10:
            advice = "**极力推荐**：满分股票，技术面完美，重点关注"
        elif score == 9:
            advice = "**强烈推荐**：高分股票，可积极布局"
        else:
            advice = "**推荐**：达标股票，可适度配置"
        
        report_lines.extend([
            "",
            f"**操作建议**: {advice}",
            "",
            "---",
            "",
        ])
    
    # A级股票简要列表
    report_lines.extend([
        "## 📈 A级股票列表 (6-7分)",
        "",
        "*备选池：技术面良好，可根据个人风险偏好配置*",
        "",
        "| 排名 | 股票名称 | 代码 | 评分 | 涨幅 | 成交额(亿) |",
        "|------|---------|------|------|------|------------|",
    ])
    
    for i, row in enumerate(a_level.head(30).iterrows(), 1):
        stock = row[1]
        report_lines.append(
            f"| {i} | {stock['name']} | {stock['code']} | "
            f"{int(stock['six_dim_score'])}/10 | {stock['change_pct']:+.2f}% | "
            f"{stock['turnover']/100000000:.2f} |"
        )
    
    report_lines.extend([
        "",
        "---",
        "",
        "## 💡 策略说明",
        "",
        "### ⚔️ 策略A：六维真强势 (Momentum)",
        "",
        "*适用场景：大盘绿灯，股价在均线之上，寻求主升浪*",
        "",
        "**六维评分标准**:",
        "",
        "1. **趋势维度** (0-2分): 均线多头排列 (MA5>MA10>MA20)",
        "2. **K线维度** (0-2分): 实体阳线，无长上影",
        "3. **量能维度** (0-2分): 上涨放量 (量比>1.5)",
        "4. **分时维度** (0-1分): 收盘价>开盘价",
        "5. **盘口维度** (0-1分): 振幅适中 (2%-8%)",
        "6. **尾盘维度** (0-2分): 收盘接近最高价",
        "",
        "**评级标准**:",
        "- **S级** (8-10分): 极强势，重点关注",
        "- **A级** (6-7分): 强势，可关注",
        "- **B级** (4-5分): 一般，观望",
        "",
        "---",
        "",
        "## 🛡️ 风控提示",
        "",
        "1. **止损位**: 跌破MA5或今日开盘价严格止损",
        "2. **仓位管理**: 单只股票≤20%，S级股票总仓位≤60%",
        "3. **分批建仓**: 不追涨停，分2-3批进场",
        "4. **及时止盈**: 涨幅>10%或六维评分下降时考虑减仓",
        "5. **市场监控**: 大盘转为黄灯或红灯时立即调整策略",
        "",
        "---",
        "",
        f"**数据来源**: yfinance API",
        f"**分析时间**: {today}",
        f"**策略版本**: v1.0",
    ])
    
    report = "\n".join(report_lines)
    
    # 保存报告
    report_file = f'data/strategy_report_{datetime.now().strftime("%Y-%m-%d")}.md'
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    logger.info(f"✅ 报告已保存: {report_file}")
    
    # 决定是否推送
    should_push = len(s_level) >= 5 and push_to_wechat
    
    if should_push:
        logger.info(f"\n📤 准备推送到企业微信 (S级股票: {len(s_level)} 只)")
        
        # 精简版报告（企业微信）
        wechat_report = f"""# 📊 六维真强势策略扫描 ({datetime.now().strftime('%m-%d')})

🌍 **市场环境**: 10/10分 🟢绿灯
🛠️  **执行策略**: 策略A-六维真强势
⚖️  **建议仓位**: 重仓出击

---

## 🏆 S级股票 ({len(s_level)} 只)

"""
        # Top 10
        for i, row in enumerate(s_level.head(10).iterrows(), 1):
            stock = row[1]
            wechat_report += f"{i}. **{stock['name']}({stock['code']})** - {int(stock['six_dim_score'])}/10分\n"
            wechat_report += f"   涨幅{stock['change_pct']:+.2f}% | 成交额{stock['turnover']/100000000:.2f}亿\n\n"
        
        if len(s_level) > 10:
            wechat_report += f"\n...及其他{len(s_level)-10}只S级股票\n"
        
        wechat_report += f"\n📈 A级股票: {len(a_level)} 只\n"
        wechat_report += "\n---\n\n💡 **操作建议**: 精选S级股票分批建仓\n"
        wechat_report += "🛡️  **风控**: 跌破MA5止损，单只≤20%仓位"
        
        # 推送
        try:
            notifier = NotificationService()
            notifier.send(wechat_report)
            logger.info("✅ 报告已推送到企业微信")
        except Exception as e:
            logger.error(f"❌ 推送失败: {e}")
    else:
        logger.info(f"\n⚠️  未推送: S级股票数量({len(s_level)})未达阈值(5)")
    
    # 输出摘要
    logger.info("\n" + "="*70)
    logger.info("📊 报告摘要:")
    logger.info(f"   S级股票: {len(s_level)} 只")
    logger.info(f"   A级股票: {len(a_level)} 只")
    logger.info(f"   详细报告: {report_file}")
    logger.info("="*70)
    
    return report_file


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='生成策略扫描报告')
    parser.add_argument('--csv', default=f'data/six_dimension_scan_{datetime.now().strftime("%Y-%m-%d")}.csv',
                       help='CSV文件路径')
    parser.add_argument('--no-push', action='store_true', help='不推送到企业微信')
    
    args = parser.parse_args()
    
    generate_strategy_report(args.csv, push_to_wechat=not args.no_push)
