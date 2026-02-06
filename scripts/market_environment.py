#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
市场环境分析器 - 自动抓取大盘数据和新闻情绪
结合宏观环境和新闻面进行综合评分
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yfinance as yf
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MarketEnvironmentAnalyzer:
    """市场环境分析器"""
    
    def __init__(self, alpha_vantage_key: Optional[str] = None):
        """
        初始化分析器
        
        Args:
            alpha_vantage_key: Alpha Vantage API Key (可选，从环境变量读取)
        """
        self.av_key = alpha_vantage_key or os.getenv('ALPHA_VANTAGE_API_KEY')
        
    def get_index_data(self, symbol: str = '000001.SS') -> Dict:
        """
        获取指数数据
        
        Args:
            symbol: 指数代码
                - '000001.SS': 上证指数
                - '399001.SZ': 深证成指
                - '000300.SS': 沪深300
                - '^GSPC': 标普500
                - '^DJI': 道琼斯
                - '^IXIC': 纳斯达克
        
        Returns:
            包含指数数据的字典
        """
        logger.info(f"📊 正在获取 {symbol} 指数数据...")
        
        try:
            # 获取最近5天数据（包含今天）
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period='5d')
            
            if hist.empty:
                logger.error(f"❌ 无法获取 {symbol} 数据")
                return None
            
            # 最新数据
            latest = hist.iloc[-1]
            prev = hist.iloc[-2] if len(hist) >= 2 else latest
            
            # 计算涨跌幅
            close = float(latest['Close'])
            prev_close = float(prev['Close'])
            change_pct = ((close - prev_close) / prev_close) * 100
            
            # 计算均线
            hist['MA5'] = hist['Close'].rolling(window=5).mean()
            hist['MA10'] = hist['Close'].rolling(window=10, min_periods=1).mean()
            hist['MA20'] = hist['Close'].rolling(window=20, min_periods=1).mean()
            
            ma5 = float(hist['MA5'].iloc[-1]) if len(hist) >= 5 else close
            ma10 = float(hist['MA10'].iloc[-1])
            ma20 = float(hist['MA20'].iloc[-1])
            
            # 成交量分析
            volume = float(latest['Volume'])
            avg_volume = float(hist['Volume'].mean())
            volume_ratio = volume / avg_volume if avg_volume > 0 else 1
            
            # K线实体分析
            open_price = float(latest['Open'])
            high_price = float(latest['High'])
            low_price = float(latest['Low'])
            
            body = abs(close - open_price)
            total_range = high_price - low_price
            body_ratio = (body / total_range * 100) if total_range > 0 else 0
            
            is_yang = close > open_price
            
            # 上下影线
            upper_shadow = (high_price - max(close, open_price)) / total_range * 100 if total_range > 0 else 0
            lower_shadow = (min(close, open_price) - low_price) / total_range * 100 if total_range > 0 else 0
            
            data = {
                'symbol': symbol,
                'date': latest.name.strftime('%Y-%m-%d'),
                'close': close,
                'change_pct': change_pct,
                'open': open_price,
                'high': high_price,
                'low': low_price,
                'volume': volume,
                'volume_ratio': volume_ratio,
                'ma5': ma5,
                'ma10': ma10,
                'ma20': ma20,
                'is_yang': is_yang,
                'body_ratio': body_ratio,
                'upper_shadow': upper_shadow,
                'lower_shadow': lower_shadow,
            }
            
            logger.info(f"✅ 获取成功: {symbol} {change_pct:+.2f}%")
            return data
            
        except Exception as e:
            logger.error(f"❌ 获取指数数据失败: {e}")
            return None
    
    def get_news_sentiment(self, topics: List[str] = None) -> Dict:
        """
        获取新闻情绪（Alpha Vantage）
        
        Args:
            topics: 关注的主题列表，如 ['china', 'technology', 'finance']
        
        Returns:
            新闻情绪数据
        """
        if not self.av_key:
            logger.warning("⚠️  未配置 Alpha Vantage API Key，跳过新闻情绪分析")
            return {
                'available': False,
                'sentiment_score': 5,
                'news_count': 0,
                'headlines': []
            }
        
        logger.info("📰 正在获取新闻情绪...")
        
        try:
            # Alpha Vantage News Sentiment API
            url = 'https://www.alphavantage.co/query'
            
            # 默认主题
            if not topics:
                topics = ['china', 'market']
            
            params = {
                'function': 'NEWS_SENTIMENT',
                'topics': ','.join(topics),
                'apikey': self.av_key,
                'limit': 50
            }
            
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if 'feed' not in data:
                logger.warning("⚠️  新闻API返回异常")
                return {
                    'available': False,
                    'sentiment_score': 5,
                    'news_count': 0,
                    'headlines': []
                }
            
            # 解析新闻
            news_items = data['feed']
            headlines = []
            sentiment_scores = []
            
            for item in news_items[:10]:  # 只取前10条
                title = item.get('title', '')
                sentiment = item.get('overall_sentiment_score', 0)
                sentiment_label = item.get('overall_sentiment_label', 'Neutral')
                
                headlines.append({
                    'title': title,
                    'sentiment': sentiment,
                    'label': sentiment_label,
                    'source': item.get('source', 'Unknown')
                })
                
                sentiment_scores.append(float(sentiment))
            
            # 计算平均情绪
            avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
            
            # 转换为0-10分制（Alpha Vantage范围是-1到1）
            sentiment_score = (avg_sentiment + 1) * 5  # 映射到0-10
            
            logger.info(f"✅ 获取 {len(headlines)} 条新闻，平均情绪: {sentiment_score:.1f}/10")
            
            return {
                'available': True,
                'sentiment_score': sentiment_score,
                'news_count': len(headlines),
                'headlines': headlines,
                'avg_raw_sentiment': avg_sentiment
            }
            
        except Exception as e:
            logger.error(f"❌ 获取新闻情绪失败: {e}")
            return {
                'available': False,
                'sentiment_score': 5,
                'news_count': 0,
                'headlines': []
            }
    
    def calculate_environment_score(self, index_data: Dict, news_data: Dict) -> Dict:
        """
        综合评分：大盘技术面 + 新闻情绪面
        
        Returns:
            包含环境评分的字典
        """
        logger.info("\n" + "="*70)
        logger.info("🎯 计算市场环境评分...")
        logger.info("="*70)
        
        # 技术面评分 (0-10)
        tech_score = 5.0
        tech_reasons = []
        
        # 1. 涨跌幅 (±3分)
        change = index_data['change_pct']
        if change > 2:
            tech_score += 3
            tech_reasons.append(f"大涨{change:.2f}% (+3分)")
        elif change > 0.5:
            tech_score += 1.5
            tech_reasons.append(f"上涨{change:.2f}% (+1.5分)")
        elif change > -0.5:
            tech_reasons.append(f"微跌{change:.2f}% (0分)")
        elif change > -2:
            tech_score -= 1.5
            tech_reasons.append(f"下跌{change:.2f}% (-1.5分)")
        else:
            tech_score -= 3
            tech_reasons.append(f"大跌{change:.2f}% (-3分)")
        
        # 2. 均线位置 (±2分)
        close = index_data['close']
        ma5 = index_data['ma5']
        ma20 = index_data['ma20']
        
        if close > ma5 and ma5 > ma20:
            tech_score += 2
            tech_reasons.append("多头排列 (+2分)")
        elif close > ma20:
            tech_score += 1
            tech_reasons.append("站上MA20 (+1分)")
        elif close < ma5 and ma5 < ma20:
            tech_score -= 2
            tech_reasons.append("空头排列 (-2分)")
        else:
            tech_score -= 1
            tech_reasons.append("均线纠缠 (-1分)")
        
        # 3. K线形态 (±2分)
        if index_data['is_yang']:
            if index_data['body_ratio'] > 60:
                tech_score += 2
                tech_reasons.append("大阳线 (+2分)")
            else:
                tech_score += 1
                tech_reasons.append("小阳线 (+1分)")
        else:
            if index_data['body_ratio'] > 60:
                tech_score -= 2
                tech_reasons.append("大阴线 (-2分)")
            else:
                tech_score -= 1
                tech_reasons.append("小阴线 (-1分)")
        
        # 4. 成交量 (±1分)
        vol_ratio = index_data['volume_ratio']
        if vol_ratio > 1.3:
            if index_data['is_yang']:
                tech_score += 1
                tech_reasons.append("放量上涨 (+1分)")
            else:
                tech_score -= 1
                tech_reasons.append("放量下跌 (-1分)")
        
        # 限制在0-10范围
        tech_score = max(0, min(10, tech_score))
        
        # 新闻情绪评分 (0-10)
        news_score = news_data['sentiment_score']
        news_weight = 0.3 if news_data['available'] else 0
        
        # 综合评分 (技术面70% + 新闻30%)
        if news_data['available']:
            final_score = tech_score * 0.7 + news_score * 0.3
        else:
            final_score = tech_score
        
        # 评级
        if final_score >= 8:
            rating = "🟢 绿灯"
            position = "重仓出击"
        elif final_score >= 5:
            rating = "🟡 黄灯"
            position = "半仓精选"
        else:
            rating = "🔴 红灯"
            position = "空仓观望"
        
        return {
            'final_score': round(final_score, 1),
            'tech_score': round(tech_score, 1),
            'news_score': round(news_score, 1),
            'rating': rating,
            'position_advice': position,
            'tech_reasons': tech_reasons,
            'news_available': news_data['available']
        }
    
    def generate_report(self, index_symbol: str = '000001.SS', news_topics: List[str] = None) -> str:
        """
        生成完整的市场环境报告
        
        Args:
            index_symbol: 指数代码
            news_topics: 新闻主题
        
        Returns:
            格式化的报告文本
        """
        # 获取数据
        index_data = self.get_index_data(index_symbol)
        if not index_data:
            return "❌ 无法获取指数数据"
        
        news_data = self.get_news_sentiment(news_topics)
        
        # 计算评分
        score_data = self.calculate_environment_score(index_data, news_data)
        
        # 生成报告
        report_lines = [
            "",
            "=" * 70,
            "📊 市场环境分析报告",
            "=" * 70,
            f"📅 日期: {index_data['date']}",
            f"📈 指数: {index_data['symbol']}",
            "",
            "---",
            "",
            f"【📊 市场环境】: {score_data['final_score']}/10 分 {score_data['rating']}",
            "",
            f"【🌍 技术面评分】: {score_data['tech_score']}/10",
            "   评分依据:",
        ]
        
        for reason in score_data['tech_reasons']:
            report_lines.append(f"   - {reason}")
        
        report_lines.extend([
            "",
            f"【📰 新闻情绪】: {score_data['news_score']}/10" + 
            (" (已集成)" if score_data['news_available'] else " (未配置API)"),
        ])
        
        if news_data['available'] and news_data['headlines']:
            report_lines.append("   最新头条:")
            for i, news in enumerate(news_data['headlines'][:5], 1):
                sentiment_emoji = "🔥" if news['sentiment'] > 0.2 else "❄️" if news['sentiment'] < -0.2 else "➖"
                report_lines.append(f"   {i}. {sentiment_emoji} {news['title'][:60]}...")
        
        report_lines.extend([
            "",
            f"【⚖️ 建议仓位】: {score_data['position_advice']}",
            "",
            "---",
            "",
            "【📈 指数详情】:",
            f"   - 收盘价: {index_data['close']:.2f} ({index_data['change_pct']:+.2f}%)",
            f"   - MA5: {index_data['ma5']:.2f} | MA20: {index_data['ma20']:.2f}",
            f"   - K线: {'阳线' if index_data['is_yang'] else '阴线'} (实体{index_data['body_ratio']:.1f}%)",
            f"   - 成交量比: {index_data['volume_ratio']:.2f}x",
            "",
            "【🛡️ 风控提示】:",
        ])
        
        if score_data['final_score'] >= 8:
            report_lines.extend([
                "   ✅ 市场环境优良，可积极布局",
                "   ✅ 重点关注强势板块龙头",
                "   ⚠️  注意及时止盈，避免追高"
            ])
        elif score_data['final_score'] >= 5:
            report_lines.extend([
                "   🟡 市场震荡，精选个股",
                "   🟡 控制仓位，快进快出",
                "   ⚠️  严格止损，避免重仓"
            ])
        else:
            report_lines.extend([
                "   🔴 市场风险较高，建议观望",
                "   🔴 空仓或极小仓位试探",
                "   ⚠️  严格止损，保护本金"
            ])
        
        report_lines.extend([
            "",
            "=" * 70,
        ])
        
        return "\n".join(report_lines)


def main():
    """主程序"""
    import argparse
    
    parser = argparse.ArgumentParser(description='市场环境分析器')
    parser.add_argument('--index', default='000001.SS', 
                       help='指数代码 (默认: 000001.SS上证指数)')
    parser.add_argument('--topics', nargs='+', default=['china', 'market'],
                       help='新闻主题 (默认: china market)')
    parser.add_argument('--av-key', help='Alpha Vantage API Key (可选)')
    
    args = parser.parse_args()
    
    # 创建分析器
    analyzer = MarketEnvironmentAnalyzer(alpha_vantage_key=args.av_key)
    
    # 生成报告
    report = analyzer.generate_report(
        index_symbol=args.index,
        news_topics=args.topics
    )
    
    print(report)
    
    # 保存到文件
    output_file = f'data/market_env_{datetime.now().strftime("%Y-%m-%d")}.txt'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n✅ 报告已保存: {output_file}")


if __name__ == "__main__":
    main()
