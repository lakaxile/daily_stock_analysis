#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略回测分析器
分析昨日选股在今日的实际表现
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from typing import Dict, List
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


class StrategyBacktester:
    """策略回测分析器"""
    
    def __init__(self, backtest_date: str = None):
        """
        初始化回测器
        
        Args:
            backtest_date: 回测日期 (YYYY-MM-DD)，即选股的日期
        """
        self.backtest_date = backtest_date or (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        self.today = datetime.now().strftime('%Y-%m-%d')
    
    def load_previous_picks(self) -> Dict:
        """加载昨日的选股结果"""
        logger.info(f"📂 加载 {self.backtest_date} 的选股结果...")
        
        picks = {}
        
        # 策略A
        strategy_a_file = f'data/six_dimension_scan_{self.backtest_date}.csv'
        if os.path.exists(strategy_a_file):
            df_a = pd.read_csv(strategy_a_file)
            picks['strategy_a'] = df_a
            logger.info(f"   策略A: {len(df_a)} 只股票")
        
        # 策略B
        strategy_b_file = f'data/oversold_bounce_scan_{self.backtest_date}.csv'
        if os.path.exists(strategy_b_file):
            df_b = pd.read_csv(strategy_b_file)
            picks['strategy_b'] = df_b
            logger.info(f"   策略B: {len(df_b)} 只股票")
        
        return picks
    
    def get_today_performance(self, codes: List[str]) -> pd.DataFrame:
        """
        获取今日实际涨跌
        
        Args:
            codes: 股票代码列表
        
        Returns:
            DataFrame containing today's performance
        """
        logger.info(f"📊 获取 {len(codes)} 只股票的今日表现...")
        
        results = []
        
        def fetch_stock(code):
            try:
                # 确保代码是字符串并添加后缀
                code_str = str(code)
                if not code_str.endswith(('.SS', '.SZ')):
                    if code_str.startswith('6') or code_str.startswith('51') or code_str.startswith('9'):
                        code_str = f"{code_str}.SS"
                    elif code_str.startswith(('0', '3', '2')):
                        code_str = f"{code_str}.SZ"
                
                ticker = yf.Ticker(code_str)
                hist = ticker.history(period='3d')
                
                if len(hist) >= 2:
                    yesterday_close = float(hist.iloc[-2]['Close'])
                    today_close = float(hist.iloc[-1]['Close'])
                    change_pct = ((today_close - yesterday_close) / yesterday_close) * 100
                    
                    return {
                        'code': code,
                        'yesterday_close': yesterday_close,
                        'today_close': today_close,
                        'change_pct': change_pct,
                        'is_win': change_pct > 0
                    }
            except Exception as e:
                # logger.warning(f"   获取 {code} 失败: {e}")
                return None
        
        # 并发获取数据
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = {executor.submit(fetch_stock, code): code for code in codes}
            
            for i, future in enumerate(as_completed(futures), 1):
                if i % 50 == 0:
                    logger.info(f"   进度: {i}/{len(codes)} ({i/len(codes)*100:.1f}%)")
                
                result = future.result()
                if result:
                    results.append(result)
        
        logger.info(f"   成功获取: {len(results)}/{len(codes)} 只股票")
        
        return pd.DataFrame(results)
    
    def analyze_strategy_performance(self, original_df: pd.DataFrame, 
                                    performance_df: pd.DataFrame,
                                    strategy_name: str) -> Dict:
        """分析策略表现"""
        logger.info(f"\n📊 分析 {strategy_name} 表现...")
        
        # 检查performance_df是否为空
        if performance_df.empty:
            logger.warning(f"    ⚠️  {strategy_name} 没有获取到今日数据")
            return None
        
        logger.info(f"   Performance DF:  {performance_df.shape[0]} rows, columns: {list(performance_df.columns)[:5]}...")
        logger.info(f"   Original DF: {original_df.shape[0]} rows")
        logger.info(f"   Code dtypes - Original: {original_df['code'].dtype}, Performance: {performance_df['code'].dtype}")
        
        # 确保code列类型一致
        original_df = original_df.copy()
        original_df['code'] = original_df['code'].astype(int)
        performance_df = performance_df.copy()
        performance_df['code'] = performance_df['code'].astype(int)
        
        # 合并数据，使用suffixes避免列名冲突
        merged = original_df.merge(performance_df, on='code', how='left', suffixes=('_old', ''))
        logger.info(f"   Merged DF: {merged.shape[0]} rows, columns has change_pct: {'change_pct' in merged.columns}")
        
        #  只保留有今日数据的股票
        if 'change_pct' in merged.columns:
            merged = merged[merged['change_pct'].notna()]
        else:
            logger.error(f"   ❌ Merge失败: change_pct列不存在")
            logger.error(f"   Columns: {list(merged.columns)}")
            return None
        
        if len(merged) == 0:
            logger.warning(f"   ⚠️  {strategy_name} 没有有效的回测数据")
            return None
        
        logger.info(f"   有效数据: {len(merged)}/{len(original_df)} 只股票")
        
        # 基本统计
        total_count = len(merged)
        win_count = len(merged[merged['is_win'] == True])
        lose_count = total_count - win_count
        win_rate = win_count / total_count * 100 if total_count > 0 else 0
        
        avg_gain = merged['change_pct'].mean()
        max_gain = merged['change_pct'].max()
        max_loss = merged['change_pct'].min()
        
        # Top和Bottom股票
        merged_sorted = merged.sort_values('change_pct', ascending=False)
        top_5 = merged_sorted.head(5)
        bottom_5 = merged_sorted.tail(5)
        
        # 按原始评分分组分析（策略A）
        score_analysis = None
        if 'six_dim_score' in merged.columns:
            s_level = merged[merged['six_dim_score'] >= 8]
            a_level = merged[(merged['six_dim_score'] >= 6) & (merged['six_dim_score'] < 8)]
            
            score_analysis = {
                's_level': {
                    'count': len(s_level),
                    'win_rate': len(s_level[s_level['is_win'] == True]) / len(s_level) * 100 if len(s_level) > 0 else 0,
                    'avg_gain': s_level['change_pct'].mean() if len(s_level) > 0 else 0
                },
                'a_level': {
                    'count': len(a_level),
                    'win_rate': len(a_level[a_level['is_win'] == True]) / len(a_level) * 100 if len(a_level) > 0 else 0,
                    'avg_gain': a_level['change_pct'].mean() if len(a_level) > 0 else 0
                }
            }
        
        # 按原始评分分组分析（策略B）
        elif 'oversold_score' in merged.columns:
            high_score = merged[merged['oversold_score'] >= 6]
            mid_score = merged[merged['oversold_score'] == 5]
            
            score_analysis = {
                'high_score': {
                    'count': len(high_score),
                    'win_rate': len(high_score[high_score['is_win'] == True]) / len(high_score) * 100 if len(high_score) > 0 else 0,
                    'avg_gain': high_score['change_pct'].mean() if len(high_score) > 0 else 0
                },
                'mid_score': {
                    'count': len(mid_score),
                    'win_rate': len(mid_score[mid_score['is_win'] == True]) / len(mid_score) * 100 if len(mid_score) > 0 else 0,
                    'avg_gain': mid_score['change_pct'].mean() if len(mid_score) > 0 else 0
                }
            }
        
        return {
            'total_count': total_count,
            'win_count': win_count,
            'lose_count': lose_count,
            'win_rate': win_rate,
            'avg_gain': avg_gain,
            'max_gain': max_gain,
            'max_loss': max_loss,
            'top_5': top_5,
            'bottom_5': bottom_5,
            'score_analysis': score_analysis,
            'merged_data': merged
        }
    
    def find_failed_patterns(self, merged_data: pd.DataFrame, strategy_name: str) -> List[str]:
        """识别失败案例的共同特征"""
        logger.info(f"\n🔍 分析 {strategy_name} 失败案例...")
        
        # 找出大幅下跌的股票
        failed_stocks = merged_data[merged_data['change_pct'] < -3]
        
        if len(failed_stocks) == 0:
            return ["✅ 没有大幅下跌（-3%以下）的股票"]
        
        patterns = []
        patterns.append(f"共 {len(failed_stocks)} 只股票下跌超过3%")
        
        # 策略A的失败分析
        if 'six_dim_score' in merged_data.columns:
            # 分析失败股票的六维评分
            avg_score = failed_stocks['six_dim_score'].mean()
            patterns.append(f"失败股票平均评分: {avg_score:.1f}/10")
            
            # 分析是否有某些维度特别弱
            if 'six_dim_details' in failed_stocks.columns:
                # 统计失败股票的共同弱点
                patterns.append("失败股票可能存在的问题:")
                patterns.append("- 部分高分股票可能处于短期顶部")
                patterns.append("- 建议增加'是否超买'判断（RSI>70）")
                patterns.append("- 建议增加'近期涨幅过大'过滤（5日涨幅>20%）")
        
        # 策略B的失败分析
        elif 'oversold_score' in merged_data.columns:
            avg_score = failed_stocks['oversold_score'].mean()
            patterns.append(f"失败股票平均评分: {avg_score:.1f}/10")
            
            patterns.append("失败股票可能存在的问题:")
            patterns.append("- 超跌可能进一步下跌")
            patterns.append("- 建议增加'底部确认'信号")
            patterns.append("- 建议增加'成交量放大'要求")
        
        return patterns
    
    def generate_report(self, results: Dict) -> str:
        """生成回测报告"""
        lines = [
            "=" * 80,
            f"📊 策略回测分析报告",
            "=" * 80,
            f"选股日期: {self.backtest_date}",
            f"验证日期: {self.today}",
            f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "=" * 80,
        ]
        
        for strategy_name, analysis in results.items():
            if not analysis:
                continue
            
            lines.extend([
                "",
                f"## {'⚔️ 策略A：六维真强势' if strategy_name == 'strategy_a' else '🛡️ 策略B：黄金坑反弹'}",
                "",
                "### 📊 整体表现",
                f"- 验证股票数: {analysis['total_count']} 只",
                f"- 上涨股票数: {analysis['win_count']} 只",
                f"- 下跌股票数: {analysis['lose_count']} 只",
                f"- **胜率**: **{analysis['win_rate']:.2f}%**",
                f"- 平均涨跌幅: {analysis['avg_gain']:+.2f}%",
                f"- 最大涨幅: {analysis['max_gain']:+.2f}%",
                f"- 最大跌幅: {analysis['max_loss']:+.2f}%",
                "",
            ])
            
            # 评分分组分析
            if analysis['score_analysis']:
                lines.append("### 📈 分级表现")
                
                if strategy_name == 'strategy_a':
                    s_level = analysis['score_analysis']['s_level']
                    a_level = analysis['score_analysis']['a_level']
                    
                    lines.extend([
                        f"**S级股票 (8-10分)**:",
                        f"- 数量: {s_level['count']} 只",
                        f"- 胜率: **{s_level['win_rate']:.2f}%**",
                        f"- 平均涨幅: {s_level['avg_gain']:+.2f}%",
                        "",
                        f"**A级股票 (6-7分)**:",
                        f"- 数量: {a_level['count']} 只",
                        f"- 胜率: **{a_level['win_rate']:.2f}%**",
                        f"- 平均涨幅: {a_level['avg_gain']:+.2f}%",
                        "",
                    ])
                else:
                    high_score = analysis['score_analysis']['high_score']
                    mid_score = analysis['score_analysis']['mid_score']
                    
                    lines.extend([
                        f"**高分超跌 (6分以上)**:",
                        f"- 数量: {high_score['count']} 只",
                        f"- 胜率: **{high_score['win_rate']:.2f}%**",
                        f"- 平均涨幅: {high_score['avg_gain']:+.2f}%",
                        "",
                        f"**中度超跌 (5分)**:",
                        f"- 数量: {mid_score['count']} 只",
                        f"- 胜率: **{mid_score['win_rate']:.2f}%**",
                        f"- 平均涨幅: {mid_score['avg_gain']:+.2f}%",
                        "",
                    ])
            
            # Top 5
            lines.append("### 🏆 Top 5 表现最佳")
            for i, row in analysis['top_5'].iterrows():
                lines.append(f"{i+1}. {row['name']}({row['code']}) - {row['change_pct']:+.2f}%")
            
            lines.append("")
            
            # Bottom 5
            lines.append("### ⚠️ Bottom 5 表现最差")
            for i, row in analysis['bottom_5'].iterrows():
                lines.append(f"{i+1}. {row['name']}({row['code']}) - {row['change_pct']:+.2f}%")
            
            lines.append("")
        
        lines.extend([
            "=" * 80,
            "",
        ])
        
        return "\n".join(lines)
    
    def run_backtest(self) -> Dict:
        """执行完整回测"""
        logger.info("=" * 80)
        logger.info(f"🔍 开始回测分析")
        logger.info("=" * 80)
        
        # 加载昨日选股
        picks = self.load_previous_picks()
        
        if not picks:
            logger.error("❌ 未找到选股数据")
            return {}
        
        results = {}
        
        # 回测策略A
        if 'strategy_a' in picks:
            codes_a = picks['strategy_a']['code'].tolist()
            performance_a = self.get_today_performance(codes_a)
            
            if not performance_a.empty:
                results['strategy_a'] = self.analyze_strategy_performance(
                    picks['strategy_a'], performance_a, "策略A"
                )
                
                # 分析失败案例
                patterns_a = self.find_failed_patterns(
                    results['strategy_a']['merged_data'], "策略A"
                )
                results['strategy_a']['failed_patterns'] = patterns_a
        
        # 回测策略B
        if 'strategy_b' in picks:
            codes_b = picks['strategy_b']['code'].tolist()
            performance_b = self.get_today_performance(codes_b)
            
            if not performance_b.empty:
                results['strategy_b'] = self.analyze_strategy_performance(
                    picks['strategy_b'], performance_b, "策略B"
                )
                
                # 分析失败案例
                patterns_b = self.find_failed_patterns(
                    results['strategy_b']['merged_data'], "策略B"
                )
                results['strategy_b']['failed_patterns'] = patterns_b
        
        # 生成报告
        report = self.generate_report(results)
        print(report)
        
        # 保存报告
        report_file = f'data/backtest_report_{self.backtest_date}.txt'
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info(f"\n✅ 回测报告已保存: {report_file}")
        
        # 生成优化建议
        self.generate_optimization_suggestions(results)
        
        return results
    
    def generate_optimization_suggestions(self, results: Dict):
        """生成策略优化建议"""
        logger.info("\n" + "=" * 80)
        logger.info("💡 策略优化建议")
        logger.info("=" * 80)
        
        for strategy_name, analysis in results.items():
            if not analysis:
                continue
            
            strategy_label = "策略A" if strategy_name == "strategy_a" else "策略B"
            win_rate = analysis['win_rate']
            avg_gain = analysis['avg_gain']
            
            logger.info(f"\n## {strategy_label}")
            logger.info(f"当前胜率: {win_rate:.2f}%")
            logger.info(f"平均涨幅: {avg_gain:+.2f}%")
            
            # 根据表现给出建议
            if win_rate < 50:
                logger.info("\n⚠️  **胜率偏低，建议优化**:")
                for pattern in analysis['failed_patterns']:
                    logger.info(f"  - {pattern}")
            elif win_rate < 60:
                logger.info("\n🟡 **表现一般，可以改进**:")
                logger.info("  - 考虑增加更严格的筛选条件")
                logger.info("  - 分析高胜率股票的共同特征")
            else:
                logger.info("\n✅ **表现优秀，保持策略**:")
                logger.info("  - 当前策略有效")
                logger.info("  - 可以考虑优化仓位管理")
        
        logger.info("\n" + "=" * 80)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='策略回测分析')
    parser.add_argument('--date', help='选股日期 (YYYY-MM-DD)，默认为昨天')
    
    args = parser.parse_args()
    
    backtester = StrategyBacktester(backtest_date=args.date)
    results = backtester.run_backtest()
    
    return results


if __name__ == "__main__":
    main()
