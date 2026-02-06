#!/usr/bin/env python3  
# -*- coding: utf-8 -*-
"""
完整流程：技术指标扫描 + AI深度分析
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from datetime import datetime
from src.analyzer import GeminiAnalyzer
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def load_scan_results(csv_file):
    """加载扫描结果CSV"""
    try:
        df = pd.read_csv(csv_file)
        logger.info(f"✅ 加载扫描结果: {len(df)} 只股票")
        return df
    except Exception as e:
        logger.error(f"❌ 加载CSV失败: {e}")
        return None


def convert_to_analyze_context(row):
    """将扫描结果转换为AI analyzer期望的context格式"""
    
    code = str(row['code'])
    
    # 构建context字典
    context = {
        'code': code,
        'stock_name': row.get('name', f'股票{code}'),
        'date': datetime.now().strftime('%Y-%m-%d'),
        
        # 今日行情数据
        'today': {
            'close': row.get('close'),
            'open': row.get('open'),
            'high': row.get('high'),
            'low': row.get('low'),
            'pct_chg': row.get('change_pct'),
            'volume': row.get('volume'),
            'amount': row.get('turnover'),
            'ma5': row.get('ma5'),
            'ma10': row.get('ma10'),
            'ma20': row.get('ma20'),
        },
        
        # 实时数据
        'realtime': {
            'price': row.get('close'),
            'volume_ratio': row.get('volume_ratio'),
            'name': row.get('name'),
        },
        
        # 均线状态
        'ma_status': '多头排列' if (row.get('ma5', 0) > row.get('ma10', 0) > row.get('ma20', 0)) else '其他',
    }
    
    return context


def analyze_scanned_stocks(csv_file, top_n=5):
    """对扫描结果进行AI深度分析"""
    
    logger.info("="*70)
    logger.info("🚀 完整分析流程：技术扫描 + AI深度分析")
    logger.info("="*70)
    
    # 1. 加载扫描结果
    df = load_scan_results(csv_file)
    if df is None or len(df) == 0:
        logger.error("❌ 没有可分析的股票")
        return
    
    # 2. 按评分排序并取TOP N
    df_sorted = df.sort_values('six_dim_score', ascending=False)
    top_stocks = df_sorted.head(top_n)
    
    logger.info(f"\n📊 将分析TOP {len(top_stocks)} 只高分股票\n")
    
    # 3. 初始化AI分析器
    try:
        analyzer = GeminiAnalyzer()
        if not analyzer.is_available():
            logger.error("❌ AI分析器不可用")
            logger.info("💡 请在.env中配置AI API:")
            logger.info("   OPENAI_API_KEY=sk-xxx")
            logger.info("   OPENAI_BASE_URL=https://api.deepseek.com/v1")
            return
        logger.info("✅ AI分析器就绪\n")
    except Exception as e:
        logger.error(f"❌ AI分析器初始化失败: {e}")
        return
    
    # 4. 逐一进行AI分析
    results = []
    for i, (_, row) in enumerate(top_stocks.iterrows(), 1):
        code = str(row['code'])
        name = row.get('name', f'股票{code}')
        score = row.get('six_dim_score', 0)
        
        logger.info(f"📊 [{i}/{len(top_stocks)}] 分析 {name} ({code}) - 六维评分: {score}/10")
        
        try:
            # 转换为AI期待的格式
            context = convert_to_analyze_context(row)
            
            # AI分析
            logger.info(f"  🤖 调用AI分析...")
            analysis = analyzer.analyze(context, news_context=None)
            
            logger.info(f"  ✅ AI分析完成")
            logger.info(f"     AI评分: {analysis.sentiment_score}/100")
            logger.info(f"     趋势: {analysis.trend_prediction}")
            logger.info(f"     建议: {analysis.operation_advice}")
            
            if analysis.dashboard:
                core = analysis.dashboard.get('core_conclusion', {})
                logger.info(f"     结论: {core.get('one_sentence', 'N/A')[:60]}...")
            
            results.append({
                'code': code,
                'name': name,
                'six_dim_score': score,
                'technical_data': row.to_dict(),
                'ai_analysis': analysis
            })
            
        except Exception as e:
            logger.error(f"  ❌ 分析失败: {e}")
        
        print()
    
    # 5. 生成综合报告
    if results:
        save_comprehensive_report(results, csv_file)
    
    logger.info("="*70)
    logger.info(f"✅ 分析完成，成功分析 {len(results)}/{top_n} 只股票")
    logger.info("="*70)
    
    return results


def save_comprehensive_report(results, scan_file):
    """生成综合分析报告（技术面 + AI分析）"""
    today = datetime.now().strftime('%Y-%m-%d')
    
    report = f"""# 📊 综合分析报告 ({today})

> 本报告结合技术指标扫描和AI深度分析，提供全方位的投资决策支持

**数据来源**: `{os.path.basename(scan_file)}`  
**分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}  
**AI模型**: DeepSeek Chat

---

"""
    
    for i, item in enumerate(results, 1):
        analysis = item['ai_analysis']
        tech = item['technical_data']
        
        # 获取仪表盘数据
        dashboard = analysis.dashboard or {}
        core_conclusion = dashboard.get('core_conclusion', {})
        battle_plan = dashboard.get('battle_plan', {})
        sniper_points = battle_plan.get('sniper_points', {})
        
        report += f"""
## {i}. {item['name']} ({item['code']})

### 🎯 综合评级

| 维度 | 评分 | 说明 |
|------|------|------|
| **技术面评分** | **{item['six_dim_score']}/10** | 六维真强势策略 |
| **AI情绪评分** | **{analysis.sentiment_score}/100** | AI深度分析 |
| **AI趋势预测** | {analysis.trend_prediction} | - |
| **AI操作建议** | **{analysis.operation_advice}** | - |
| **置信度** | {analysis.confidence_level} | - |

### 📈 技术面数据

- **当前价格**: ¥{tech.get('close', 'N/A')} ({tech.get('change_pct', 'N/A'):+.2f}%)
- **成交额**: {tech.get('turnover', 0)/1e8:.2f}亿
- **量比**: {tech.get('volume_ratio', 'N/A')}x
- **均线**: MA5={tech.get('ma5', 'N/A')}, MA10={tech.get('ma10', 'N/A')}, MA20={tech.get('ma20', 'N/A')}
- **收盘位置**: {tech.get('close_position', 'N/A')}%

### 🤖 AI核心结论

**{core_conclusion.get('one_sentence', '暂无结论')}**

**信号类型**: {core_conclusion.get('signal_type', 'N/A')}  
**时间敏感度**: {core_conclusion.get('time_sensitivity', 'N/A')}

"""
        
        # 添加狙击点位（如果有）
        if sniper_points:
            report += f"""
### 🎯 操作点位

- **理想买入**: {sniper_points.get('ideal_buy', 'N/A')}
- **次优买入**: {sniper_points.get('secondary_buy', 'N/A')}
- **止损位**: {sniper_points.get('stop_loss', 'N/A')}
- **目标位1**: {sniper_points.get('target_1', 'N/A')}
- **目标位2**: {sniper_points.get('target_2', 'N/A')}
"""
        
        # 添加检查清单（如果有）
        checklist = battle_plan.get('checklist', {})
        if checklist:
            report += f"""
### ✅ 决策检查清单

"""
            for key, value in checklist.items():
                if isinstance(value, dict):
                    status = value.get('status', '❓')
                    detail = value.get('detail', '')
                    report += f"- {status} **{key}**: {detail}\n"
        
        report += "\n---\n"
    
    # 保存报告
    filename = f'data/comprehensive_analysis_{today}.md'
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(report)
    
    logger.info(f"📄 综合分析报告已保存: {filename}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='对技术扫描结果进行AI深度分析')
    parser.add_argument('--csv', default='data/six_dimension_scan_2026-02-05.csv',
                       help='扫描结果CSV文件路径')
    parser.add_argument('--top', type=int, default=5,
                       help='分析TOP N只股票')
    
    args = parser.parse_args()
    
    analyze_scanned_stocks(args.csv, args.top)


if __name__ == "__main__":
    main()
