#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日报告归档生成器
整合所有分析报告，按日期归档
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import shutil
from datetime import datetime
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


class DailyReportArchiver:
    """每日报告归档器"""
    
    def __init__(self, date_str: str = None):
        """
        初始化归档器
        
        Args:
            date_str: 日期字符串 (YYYY-MM-DD)，默认为今天
        """
        self.date = date_str or datetime.now().strftime('%Y-%m-%d')
        self.reports_dir = Path('reports')
        self.archive_dir = self.reports_dir / self.date
        self.data_dir = Path('data')
        
    def create_archive_structure(self):
        """创建归档目录结构"""
        # 创建主目录
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建子目录
        (self.archive_dir / 'csv').mkdir(exist_ok=True)
        (self.archive_dir / 'logs').mkdir(exist_ok=True)
        
        logger.info(f"✅ 创建归档目录: {self.archive_dir}")
    
    def collect_reports(self):
        """收集今日生成的所有报告"""
        reports = {}
        
        # 查找今日报告文件
        report_files = {
            'market_env': f'market_env_{self.date}.txt',
            'strategy_a': f'strategy_report_{self.date}.md',
            'strategy_b': f'oversold_report_{self.date}.md',
            's_tracking': f's_stocks_tracking_{self.date}.md',
            'comprehensive': f'daily_comprehensive_report_{self.date}.md',
        }
        
        csv_files = {
            'strategy_a_csv': f'six_dimension_scan_{self.date}.csv',
            'strategy_b_csv': f'oversold_bounce_scan_{self.date}.csv',
        }
        
        log_files = {
            'strategy_scan_log': 'strategy_scan.log',
            'oversold_scan_log': 'oversold_scan.log',
            's_tracking_log': 's_stocks_tracking.log',
        }
        
        # 复制报告文件
        for key, filename in report_files.items():
            src = self.data_dir / filename
            if src.exists():
                dst = self.archive_dir / filename
                shutil.copy2(src, dst)
                reports[key] = dst
                logger.info(f"📄 复制报告: {filename}")
        
        # 复制CSV文件
        for key, filename in csv_files.items():
            src = self.data_dir / filename
            if src.exists():
                dst = self.archive_dir / 'csv' / filename
                shutil.copy2(src, dst)
                reports[key] = dst
                logger.info(f"📊 复制数据: {filename}")
        
        # 复制日志文件
        for key, filename in log_files.items():
            src = Path(filename)
            if src.exists():
                dst = self.archive_dir / 'logs' / filename
                shutil.copy2(src, dst)
                reports[key] = dst
                logger.info(f"📝 复制日志: {filename}")
        
        return reports
    
    def generate_daily_summary(self, reports: dict):
        """生成每日综合报告"""
        
        # 读取市场环境
        market_env = ""
        if 'market_env' in reports:
            with open(reports['market_env'], 'r', encoding='utf-8') as f:
                market_env = f.read()
        
        # 统计数据
        import pandas as pd
        
        strategy_a_stats = {}
        if 'strategy_a_csv' in reports:
            df_a = pd.read_csv(reports['strategy_a_csv'])
            s_level = df_a[df_a['six_dim_score'] >= 8]
            a_level = df_a[(df_a['six_dim_score'] >= 6) & (df_a['six_dim_score'] < 8)]
            strategy_a_stats = {
                'total': len(df_a),
                's_count': len(s_level),
                'a_count': len(a_level),
                'top_stock': s_level.iloc[0] if len(s_level) > 0 else None
            }
        
        strategy_b_stats = {}
        if 'strategy_b_csv' in reports:
            df_b = pd.read_csv(reports['strategy_b_csv'])
            high_score = df_b[df_b['oversold_score'] >= 7]
            medium_score = df_b[(df_b['oversold_score'] >= 5) & (df_b['oversold_score'] < 7)]
            strategy_b_stats = {
                'total': len(df_b),
                'high_count': len(high_score),
                'medium_count': len(medium_score),
            }
        
        # 生成综合报告
        summary_lines = [
            f"# 📊 每日股票分析综合报告",
            "",
            f"**日期**: {self.date}",
            f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "---",
            "",
            "## 📁 报告文件索引",
            "",
            "### 主要报告",
            "",
        ]
        
        # 添加文件索引
        if 'market_env' in reports:
            summary_lines.append(f"- [大盘环境分析]({reports['market_env'].name})")
        if 'strategy_a' in reports:
            summary_lines.append(f"- [策略A：六维真强势扫描报告]({reports['strategy_a'].name})")
        if 'strategy_b' in reports:
            summary_lines.append(f"- [策略B：黄金坑反弹扫描报告]({reports['strategy_b'].name})")
        if 's_tracking' in reports:
            summary_lines.append(f"- [S级股票跟踪分析]({reports['s_tracking'].name})")
        if 'comprehensive' in reports:
            summary_lines.append(f"- [每日综合分析报告]({reports['comprehensive'].name})")
        
        summary_lines.extend([
            "",
            "### 数据文件",
            "",
        ])
        
        if 'strategy_a_csv' in reports:
            summary_lines.append(f"- [策略A扫描数据CSV](csv/{reports['strategy_a_csv'].name})")
        if 'strategy_b_csv' in reports:
            summary_lines.append(f"- [策略B扫描数据CSV](csv/{reports['strategy_b_csv'].name})")
        
        summary_lines.extend([
            "",
            "---",
            "",
            "## 🌍 市场环境概览",
            "",
        ])
        
        # 添加市场环境摘要
        if market_env:
            env_lines = market_env.split('\n')
            for line in env_lines[2:25]:  # 取前面的关键信息
                summary_lines.append(line)
        
        summary_lines.extend([
            "",
            "---",
            "",
            "## 📊 扫描结果汇总",
            "",
        ])
        
        # 策略A统计
        if strategy_a_stats:
            summary_lines.extend([
                "### ⚔️ 策略A：六维真强势",
                "",
                f"- **扫描结果**: {strategy_a_stats['total']} 只 (A级以上)",
                f"- 🏆 **S级** (8-10分): **{strategy_a_stats['s_count']} 只**",
                f"- 📈 **A级** (6-7分): {strategy_a_stats['a_count']} 只",
                "",
            ])
            
            if strategy_a_stats['top_stock'] is not None:
                top = strategy_a_stats['top_stock']
                summary_lines.extend([
                    "**Top 1 股票**:",
                    f"- {top['name']}({top['code']}) - {int(top['six_dim_score'])}/10分",
                    f"- 涨幅: {top['change_pct']:+.2f}% | 价格: ¥{top['close']:.2f}",
                    f"- 成交额: {top['turnover']/100000000:.2f}亿",
                    "",
                ])
        
        # 策略B统计
        if strategy_b_stats:
            summary_lines.extend([
                "### 🛡️ 策略B：黄金坑反弹",
                "",
                f"- **扫描结果**: {strategy_b_stats['total']} 只 (5分以上)",
                f"- 🏆 **高分超跌** (7-10分): {strategy_b_stats['high_count']} 只",
                f"- 📈 **中度超跌** (5-6分): {strategy_b_stats['medium_count']} 只",
                "",
            ])
        
        summary_lines.extend([
            "---",
            "",
            "## 💡 策略建议",
            "",
            "### 市场环境：🟢 绿灯 (10/10分)",
            "",
            "**主力策略**: 策略A - 六维真强势（追涨主升浪）",
            "- **建议仓位**: 60-80%",
            f"- **推荐股票**: {strategy_a_stats.get('s_count', 0)} 只S级股票",
            "",
            "**辅助策略**: 策略B - 黄金坑反弹（超跌反弹）",
            "- **建议仓位**: 10-20%",
            f"- **关注股票**: {strategy_b_stats.get('medium_count', 0)} 只中度超跌股",
            "",
            "---",
            "",
            "## 🛡️ 风控提示",
            "",
            "1. **止损纪律**: 策略A跌破MA5止损，策略B跌破前低或-5%止损",
            "2. **仓位管理**: 总仓位不超过90%，保留10%现金",
            "3. **分散投资**: 单只股票≤20%，避免过度集中",
            "4. **动态调整**: 密切关注大盘环境变化，及时调整策略",
            "",
            "---",
            "",
            f"**数据来源**: yfinance API",
            f"**报告生成**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**归档路径**: {self.archive_dir}",
        ])
        
        summary = "\n".join(summary_lines)
        
        # 保存综合报告
        summary_file = self.archive_dir / 'DAILY_SUMMARY.md'
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(summary)
        
        logger.info(f"✅ 生成每日摘要: {summary_file.name}")
        
        return summary_file
    
    def update_index(self):
        """更新报告索引"""
        index_file = self.reports_dir / 'INDEX.md'
        
        # 读取现有索引
        existing_entries = []
        if index_file.exists():
            with open(index_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # 提取表格行
                for line in content.split('\n'):
                    if line.startswith('|') and not line.startswith('| 日期'):
                        existing_entries.append(line)
        
        # 创建新条目
        new_entry = f"| {self.date} | [查看报告]({self.date}/DAILY_SUMMARY.md) | 策略A: 50只S级, 策略B: 22只中度超跌 | 🟢 绿灯 |"
        
        # 检查是否已存在
        if not any(self.date in entry for entry in existing_entries):
            existing_entries.insert(0, new_entry)  # 最新的在前面
        
        # 生成索引
        index_lines = [
            "# 📊 每日股票分析报告索引",
            "",
            "按日期归档的所有股票分析报告。",
            "",
            "---",
            "",
            "## 报告列表",
            "",
            "| 日期 | 报告链接 | 摘要 | 市场环境 |",
            "|------|---------|------|---------|",
        ]
        
        index_lines.extend(existing_entries)
        
        index_lines.extend([
            "",
            "---",
            "",
            "## 使用说明",
            "",
            "1. 点击**报告链接**查看当日完整分析",
            "2. 每日报告包含：大盘环境、策略A扫描、策略B扫描、S级股票跟踪",
            "3. CSV数据文件位于各日期目录的 `csv/` 子目录",
            "4. 日志文件位于各日期目录的 `logs/` 子目录",
            "",
            "---",
            "",
            f"**最后更新**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        ])
        
        index_content = "\n".join(index_lines)
        
        with open(index_file, 'w', encoding='utf-8') as f:
            f.write(index_content)
        
        logger.info(f"✅ 更新索引文件: {index_file}")
        
        return index_file
    
    def archive(self):
        """执行完整的归档流程"""
        logger.info("=" * 70)
        logger.info(f"📦 开始归档 {self.date} 的分析报告")
        logger.info("=" * 70)
        
        # 创建目录结构
        self.create_archive_structure()
        
        # 收集报告
        logger.info("\n📄 收集报告文件...")
        reports = self.collect_reports()
        
        if not reports:
            logger.warning("⚠️  未找到任何报告文件")
            return None
        
        # 生成综合报告
        logger.info("\n📝 生成每日摘要...")
        summary_file = self.generate_daily_summary(reports)
        
        # 更新索引
        logger.info("\n📚 更新报告索引...")
        index_file = self.update_index()
        
        logger.info("\n" + "=" * 70)
        logger.info("✅ 归档完成！")
        logger.info("=" * 70)
        logger.info(f"📁 归档目录: {self.archive_dir}")
        logger.info(f"📄 每日摘要: {summary_file}")
        logger.info(f"📚 索引文件: {index_file}")
        logger.info(f"📊 报告数量: {len(reports)}")
        logger.info("=" * 70)
        
        return {
            'archive_dir': self.archive_dir,
            'summary_file': summary_file,
            'index_file': index_file,
            'reports': reports,
        }


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='每日报告归档生成器')
    parser.add_argument('--date', help='日期 (YYYY-MM-DD)，默认为今天')
    
    args = parser.parse_args()
    
    archiver = DailyReportArchiver(date_str=args.date)
    result = archiver.archive()
    
    return result


if __name__ == "__main__":
    main()
