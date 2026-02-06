#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新闻情绪分析器 - Alpha Vantage实现
基于用户提供的完整实现方案
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import json
from datetime import datetime
from typing import Dict, List
import logging

# 自动加载.env文件
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


class NewsSentimentAnalyzer:
    """新闻情绪分析器"""
    
    def __init__(self, api_key: str = None):
        """
        初始化分析器
        
        Args:
            api_key: Alpha Vantage API Key
        """
        self.api_key = api_key or os.getenv('ALPHA_VANTAGE_API_KEY')
        
        if not self.api_key:
            raise ValueError("请设置 ALPHA_VANTAGE_API_KEY 环境变量或传入api_key参数")
    
    def analyze(self, topics: List[str] = None, tickers: List[str] = None, limit: int = 50) -> Dict:
        """
        分析新闻情绪
        
        Args:
            topics: 关注话题列表，如 ['financial_markets', 'economy_macro']
            tickers: 关注股票代码，如 ['AAPL', 'MSFT']
            limit: 获取新闻数量
        
        Returns:
            情绪分析结果字典
        """
        # 默认关注金融市场
        if not topics and not tickers:
            topics = ['financial_markets']
        
        # 构建请求参数
        params = {
            "function": "NEWS_SENTIMENT",
            "sort": "LATEST",
            "limit": str(limit),
            "apikey": self.api_key
        }
        
        if topics:
            params["topics"] = ",".join(topics)
        if tickers:
            params["tickers"] = ",".join(tickers)
        
        logger.info(f"🔍 正在分析 {topics or tickers} 的新闻情绪...")
        logger.info(f"   获取最近 {limit} 条新闻")
        
        try:
            url = "https://www.alphavantage.co/query"
            response = requests.get(url, params=params, timeout=15)
            data = response.json()
            
            # 检查错误
            if "Note" in data:
                logger.warning(f"⚠️  API提示: {data['Note']}")
                return self._empty_result("API限流")
            
            if "feed" not in data or len(data["feed"]) == 0:
                logger.warning("❌ 未获取到新闻数据")
                return self._empty_result("无数据")
            
            # 统计情绪
            total_score = 0
            sentiment_counts = {
                "Bullish": 0,           # 看多
                "Somewhat-Bullish": 0,  # 略微看多
                "Neutral": 0,           # 中性
                "Somewhat-Bearish": 0,  # 略微看空
                "Bearish": 0            # 看空
            }
            news_summary = []
            
            logger.info(f"\n--- 📊 抓取到 {len(data['feed'])} 条最新新闻 ---\n")
            
            for item in data["feed"]:
                # 获取情绪分数 (-1 到 1)
                score = float(item.get("overall_sentiment_score", 0))
                label = item.get("overall_sentiment_label", "Neutral")
                title = item.get("title", "")
                time_published = item.get("time_published", "")
                source = item.get("source", "Unknown")
                
                # 累加分数
                total_score += score
                
                # 统计标签
                if label in sentiment_counts:
                    sentiment_counts[label] += 1
                elif "Bullish" in label:
                    sentiment_counts["Bullish"] += 1
                elif "Bearish" in label:
                    sentiment_counts["Bearish"] += 1
                else:
                    sentiment_counts["Neutral"] += 1
                
                # 收集重要新闻
                news_summary.append({
                    'title': title,
                    'label': label,
                    'score': score,
                    'time': time_published,
                    'source': source
                })
            
            # 计算平均分
            avg_sentiment = total_score / len(data["feed"])
            
            # 转换为0-10分制
            # avg_sentiment范围: -1到1
            # 映射: -1->0, 0->5, 1->10
            sentiment_score_10 = (avg_sentiment + 1) * 5
            
            # 判断情绪标签
            if avg_sentiment > 0.15:
                mood_label = "🟢 情绪乐观 (偏多)"
                market_mood = "乐观"
            elif avg_sentiment < -0.15:
                mood_label = "🔴 情绪悲观 (偏空)"
                market_mood = "悲观"
            else:
                mood_label = "🟡 情绪中性 (震荡)"
                market_mood = "中性"
            
            # 统计看多看空
            bullish_total = sentiment_counts["Bullish"] + sentiment_counts["Somewhat-Bullish"]
            bearish_total = sentiment_counts["Bearish"] + sentiment_counts["Somewhat-Bearish"]
            
            result = {
                'success': True,
                'avg_sentiment': avg_sentiment,
                'sentiment_score_10': sentiment_score_10,
                'mood_label': mood_label,
                'market_mood': market_mood,
                'counts': sentiment_counts,
                'bullish_total': bullish_total,
                'bearish_total': bearish_total,
                'neutral_total': sentiment_counts["Neutral"],
                'news_count': len(data["feed"]),
                'news_summary': news_summary
            }
            
            # 输出报告
            self._print_report(result)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 发生错误: {e}")
            return self._empty_result("发生错误")
    
    def _empty_result(self, reason: str) -> Dict:
        """返回空结果"""
        return {
            'success': False,
            'avg_sentiment': 0.0,
            'sentiment_score_10': 5.0,
            'mood_label': reason,
            'market_mood': '未知',
            'counts': {},
            'bullish_total': 0,
            'bearish_total': 0,
            'neutral_total': 0,
            'news_count': 0,
            'news_summary': []
        }
    
    def _print_report(self, result: Dict):
        """打印分析报告"""
        logger.info("=" * 70)
        logger.info("📊 === 情绪分析报告 ===")
        logger.info("=" * 70)
        logger.info(f"")
        logger.info(f"平均情绪得分: {result['avg_sentiment']:.4f} (范围 -1.0 到 1.0)")
        logger.info(f"转换为10分制: {result['sentiment_score_10']:.2f}/10")
        logger.info(f"")
        logger.info(f"看多: {result['bullish_total']} | "
                   f"看空: {result['bearish_total']} | "
                   f"中性: {result['neutral_total']}")
        logger.info(f"")
        logger.info(f"初步判断: {result['mood_label']}")
        logger.info("")
        logger.info("=" * 70)
        logger.info("📝 === 这里的文本复制给AI (策略Prompt) ===")
        logger.info("=" * 70)
        logger.info(f"")
        logger.info(f"今日国际新闻综合情绪得分: {result['avg_sentiment']:.2f} ({result['mood_label']})。")
        logger.info(f"")
        logger.info("关键新闻摘要:")
        for i, news in enumerate(result['news_summary'][:5], 1):
            logger.info(f"{i}. [{news['label']}] {news['title']}")
        logger.info("")
        logger.info("=" * 70)
    
    def save_report(self, result: Dict, output_file: str = None):
        """保存分析报告"""
        if not output_file:
            output_file = f'data/news_sentiment_{datetime.now().strftime("%Y-%m-%d")}.json'
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ 报告已保存: {output_file}")
        return output_file


def main():
    """主程序"""
    import argparse
    
    parser = argparse.ArgumentParser(description='新闻情绪分析器')
    parser.add_argument('--api-key', help='Alpha Vantage API Key (或设置环境变量 ALPHA_VANTAGE_API_KEY)')
    parser.add_argument('--topics', nargs='+', default=['financial_markets'],
                       help='关注话题 (默认: financial_markets)')
    parser.add_argument('--tickers', nargs='+', help='关注股票代码')
    parser.add_argument('--limit', type=int, default=50, help='获取新闻数量 (默认: 50)')
    parser.add_argument('--save', action='store_true', help='保存结果到JSON文件')
    
    args = parser.parse_args()
    
    try:
        # 创建分析器
        analyzer = NewsSentimentAnalyzer(api_key=args.api_key)
        
        # 执行分析
        result = analyzer.analyze(
            topics=args.topics,
            tickers=args.tickers,
            limit=args.limit
        )
        
        # 保存结果
        if args.save and result['success']:
            analyzer.save_report(result)
        
        # 返回评分用于集成
        if result['success']:
            return result['sentiment_score_10']
        else:
            return 5.0
            
    except ValueError as e:
        logger.error(f"❌ {e}")
        logger.info("\n💡 使用方法:")
        logger.info("1. 申请免费API Key: https://www.alphavantage.co/support/#api-key")
        logger.info("2. 设置环境变量: export ALPHA_VANTAGE_API_KEY=你的Key")
        logger.info("3. 或者运行: python3 scripts/news_sentiment.py --api-key 你的Key")
        return 5.0


if __name__ == "__main__":
    main()
