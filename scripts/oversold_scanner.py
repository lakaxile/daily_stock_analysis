#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略B：黄金坑反弹扫描器
适用场景：股价连续下跌，寻求超跌反弹机会
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


class OversoldBounceScanner:
    """策略B：黄金坑反弹扫描器"""
    
    def __init__(self):
        """初始化扫描器"""
        self.strategy = "策略B-黄金坑反弹"
        self.min_price = 5.0
        self.min_volume_ratio = 0.3  # 超跌股流动性要求更低，只需30%的平均量
    
    def get_stock_list(self) -> List[str]:
        """获取A股股票列表"""
        stock_codes = []
        
        # 上证主板
        for prefix in ['600', '601', '603']:
            stock_codes.extend([f"{prefix}{i:03d}" for i in range(1000)])
        
        # 科创板
        stock_codes.extend([f"688{i:03d}" for i in range(1, 800)])
        
        # 深证主板
        stock_codes.extend([f"000{i:03d}" for i in range(1, 1000)])
        
        # 中小板/创业板
        stock_codes.extend([f"002{i:03d}" for i in range(1, 1000)])
        stock_codes.extend([f"300{i:03d}" for i in range(1, 1000)])
        
        return stock_codes
    
    def fetch_stock_data(self, code: str) -> Dict:
        """获取股票数据并计算技术指标"""
        try:
            # 添加市场后缀
            ticker = f"{code}.SS" if code.startswith(('6', '688')) else f"{code}.SZ"
            
            stock = yf.Ticker(ticker)
            hist = stock.history(period='60d')
            
            if hist.empty or len(hist) < 20:
                return None
            
            # 今日数据
            today = hist.iloc[-1]
            yesterday = hist.iloc[-2] if len(hist) >= 2 else today
            
            # 基础数据
            close = float(today['Close'])
            open_price = float(today['Open'])
            high = float(today['High'])
            low = float(today['Low'])
            volume = float(today['Volume'])
            
            # 价格筛选
            if close < self.min_price:
                return None
            
            # 成交额筛选
            turnover = close * volume
            if turnover < self.min_volume:
                return None
            
            # 涨跌幅
            prev_close = float(yesterday['Close'])
            change_pct = ((close - prev_close) / prev_close) * 100
            
            # 计算均线
            hist['MA5'] = hist['Close'].rolling(window=5).mean()
            hist['MA10'] = hist['Close'].rolling(window=10).mean()
            hist['MA20'] = hist['Close'].rolling(window=20).mean()
            
            ma5 = float(hist['MA5'].iloc[-1])
            ma10 = float(hist['MA10'].iloc[-1])
            ma20 = float(hist['MA20'].iloc[-1])
            
            # 乖离率（与MA20）
            bias_20 = ((close - ma20) / ma20) * 100 if ma20 > 0 else 0
            
            # RSI(6)
            delta = hist['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=6).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=6).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            rsi_6 = float(rsi.iloc[-1]) if not np.isnan(rsi.iloc[-1]) else 50
            
            # 布林带
            hist['BB_Middle'] = hist['Close'].rolling(window=20).mean()
            hist['BB_Std'] = hist['Close'].rolling(window=20).std()
            hist['BB_Upper'] = hist['BB_Middle'] + 2 * hist['BB_Std']
            hist['BB_Lower'] = hist['BB_Middle'] - 2 * hist['BB_Std']
            
            bb_lower = float(hist['BB_Lower'].iloc[-1])
            bb_middle = float(hist['BB_Middle'].iloc[-1])
            
            # 距离布林下轨
            distance_to_lower = ((close - bb_lower) / bb_lower * 100) if bb_lower > 0 else 100
            
            # K线形态
            body = abs(close - open_price)
            total_range = high - low
            body_ratio = (body / total_range * 100) if total_range > 0 else 0
            is_yang = close > open_price
            
            # 上下影线
            upper_shadow = high - max(close, open_price)
            lower_shadow = min(close, open_price) - low
            upper_shadow_ratio = (upper_shadow / total_range * 100) if total_range > 0 else 0
            lower_shadow_ratio = (lower_shadow / total_range * 100) if total_range > 0 else 0
            
            # 金针探底：长下影线（>50%），小实体
            is_hammer = lower_shadow_ratio > 50 and body_ratio < 30
            
            # V型反转（今日大涨）
            is_v_reversal = change_pct > 3 and is_yang
            
            # 计算量比
            hist['VOL_MA5'] = hist['Volume'].rolling(window=5).mean()
            vol_ma5 = float(hist['VOL_MA5'].iloc[-1])
            volume_ratio = volume / vol_ma5 if vol_ma5 > 0 else 0
            
            # 连续下跌天数
            consecutive_down = 0
            for i in range(len(hist)-1, 0, -1):
                if hist.iloc[i]['Close'] < hist.iloc[i-1]['Close']:
                    consecutive_down += 1
                else:
                    break
            
            # 获取股票名称
            try:
                info = stock.info
                name = info.get('longName', '') or info.get('shortName', '') or f'股票{code}'
                if len(name) > 20:
                    name = name[:20]
            except:
                name = f'股票{code}'
            
            return {
                'code': code,
                'name': name,
                'close': close,
                'open': open_price,
                'high': high,
                'low': low,
                'change_pct': change_pct,
                'volume': volume,
                'turnover': turnover,
                'volume_ratio': volume_ratio,
                'ma5': ma5,
                'ma10': ma10,
                'ma20': ma20,
                'bias_20': bias_20,
                'rsi_6': rsi_6,
                'bb_lower': bb_lower,
                'distance_to_lower': distance_to_lower,
                'is_yang': is_yang,
                'body_ratio': body_ratio,
                'upper_shadow_ratio': upper_shadow_ratio,
                'lower_shadow_ratio': lower_shadow_ratio,
                'is_hammer': is_hammer,
                'is_v_reversal': is_v_reversal,
                'consecutive_down': consecutive_down,
            }
            
        except Exception as e:
            return None
    
    def calculate_oversold_score(self, data: Dict) -> Tuple[int, Dict]:
        """
        计算超跌反弹评分
        
        Returns:
            (总分, 详细评分字典)
        """
        score = 0
        details = {}
        
        # 1. 乖离率 (0-3分) - 最重要
        bias_score = 0
        if data['bias_20'] < -20:
            bias_score = 3
            details['乖离率'] = f"✅ 严重超跌{data['bias_20']:.1f}% (+3)"
        elif data['bias_20'] < -15:
            bias_score = 2
            details['乖离率'] = f"✅ 明显超跌{data['bias_20']:.1f}% (+2)"
        elif data['bias_20'] < -10:
            bias_score = 1
            details['乖离率'] = f"🟡 轻度超跌{data['bias_20']:.1f}% (+1)"
        else:
            details['乖离率'] = f"❌ 未超跌{data['bias_20']:.1f}% (0)"
        score += bias_score
        
        # 2. RSI指标 (0-3分)
        rsi_score = 0
        if data['rsi_6'] < 20:
            rsi_score = 3
            details['RSI'] = f"✅ 极度超卖RSI={data['rsi_6']:.1f} (+3)"
        elif data['rsi_6'] < 30:
            rsi_score = 2
            details['RSI'] = f"✅ 超卖RSI={data['rsi_6']:.1f} (+2)"
        elif data['rsi_6'] < 40:
            rsi_score = 1
            details['RSI'] = f"🟡 偏弱RSI={data['rsi_6']:.1f} (+1)"
        else:
            details['RSI'] = f"❌ 正常RSI={data['rsi_6']:.1f} (0)"
        score += rsi_score
        
        # 3. K线形态 (0-2分)
        kline_score = 0
        if data['is_hammer']:
            kline_score = 2
            details['K线'] = f"✅ 金针探底(下影{data['lower_shadow_ratio']:.0f}%) (+2)"
        elif data['is_v_reversal']:
            kline_score = 2
            details['K线'] = f"✅ V型反转{data['change_pct']:+.2f}% (+2)"
        elif data['is_yang'] and data['change_pct'] > 0:
            kline_score = 1
            details['K线'] = f"🟡 阳线反弹{data['change_pct']:+.2f}% (+1)"
        else:
            details['K线'] = f"❌ 继续下跌{data['change_pct']:+.2f}% (0)"
        score += kline_score
        
        # 4. 量能 (0-1分) - 缩量后放量
        volume_score = 0
        if data['volume_ratio'] > 1.5:
            volume_score = 1
            details['量能'] = f"✅ 突然放量{data['volume_ratio']:.2f}x (+1)"
        elif data['volume_ratio'] < 0.5:
            details['量能'] = f"🟡 极度缩量{data['volume_ratio']:.2f}x (等待放量)"
        else:
            details['量能'] = f"❌ 量能平淡{data['volume_ratio']:.2f}x (0)"
        score += volume_score
        
        # 5. 布林带位置 (0-1分)
        bb_score = 0
        if data['distance_to_lower'] < 5:  # 接近或触及下轨
            bb_score = 1
            details['布林带'] = f"✅ 触及下轨 (+1)"
        elif data['distance_to_lower'] < 10:
            details['布林带'] = f"🟡 接近下轨 (0)"
        else:
            details['布林带'] = f"❌ 远离下轨 (0)"
        score += bb_score
        
        return score, details
    
    def scan_market(self, max_workers: int = 10, sample_size: int = None) -> List[Dict]:
        """扫描全市场"""
        stock_list = self.get_stock_list()
        
        if sample_size:
            import random
            stock_list = random.sample(stock_list, min(sample_size, len(stock_list)))
        
        logger.info("=" * 70)
        logger.info(f"🔍 策略B：黄金坑反弹全市场扫描")
        logger.info("=" * 70)
        logger.info(f"🛠️  执行策略: {self.strategy}")
        logger.info(f"📋 扫描范围: {len(stock_list)} 只股票")
        logger.info(f"🧵 并发线程: {max_workers}")
        logger.info("")
        
        results = []
        processed = 0
        valid = 0
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_code = {executor.submit(self.fetch_stock_data, code): code 
                            for code in stock_list}
            
            for future in as_completed(future_to_code):
                processed += 1
                
                if processed % 100 == 0:
                    logger.info(f"📊 进度: {processed}/{len(stock_list)} ({processed/len(stock_list)*100:.1f}%)")
                
                try:
                    data = future.result()
                    if data:
                        valid += 1
                        score, details = self.calculate_oversold_score(data)
                        
                        result = {
                            **data,
                            'oversold_score': score,
                            'oversold_details': details
                        }
                        
                        # 只保留评分≥5的超跌股
                        if score >= 5:
                            results.append(result)
                            
                            # 实时输出高分股票
                            if score >= 7:
                                logger.info(
                                    f"🏆 发现超跌股: {data['name']}({data['code']}) "
                                    f"评分{score}/10 乖离{data['bias_20']:.1f}% RSI{data['rsi_6']:.1f}"
                                )
                except Exception as e:
                    pass
        
        logger.info("")
        logger.info("=" * 70)
        logger.info(f"✅ 扫描完成")
        logger.info(f"📊 总计扫描: {processed} 只")
        logger.info(f"📈 符合基础条件: {valid} 只")
        logger.info(f"🎯 超跌股(≥5分): {len(results)} 只")
        logger.info("=" * 70)
        
        return sorted(results, key=lambda x: -x['oversold_score'])


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='策略B：黄金坑反弹扫描器')
    parser.add_argument('--workers', type=int, default=10, help='并发线程数')
    parser.add_argument('--sample', type=int, help='采样数量（测试用）')
    parser.add_argument('--min-score', type=int, default=5, help='最低评分阈值')
    
    args = parser.parse_args()
    
    # 创建扫描器
    scanner = OversoldBounceScanner()
    
    # 扫描市场
    results = scanner.scan_market(max_workers=args.workers, sample_size=args.sample)
    
    # 统计
    high_score = [r for r in results if r['oversold_score'] >= 7]
    medium_score = [r for r in results if 5 <= r['oversold_score'] < 7]
    
    logger.info("")
    logger.info("📊 评级统计:")
    logger.info(f"   高分超跌 (7-10分): {len(high_score)} 只")
    logger.info(f"   中度超跌 (5-6分): {len(medium_score)} 只")
    
    # 保存结果
    if results:
        today = datetime.now().strftime('%Y-%m-%d')
        output_file = f'data/oversold_bounce_scan_{today}.csv'
        
        df = pd.DataFrame(results)
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        logger.info(f"\n✅ 结果已保存: {output_file}")
        
        # 输出高分详情
        if high_score:
            logger.info("\n" + "=" * 70)
            logger.info("🏆 高分超跌股详情 (7-10分)")
            logger.info("=" * 70)
            
            for i, stock in enumerate(high_score[:20], 1):
                logger.info(f"\n{i}. {stock['name']}({stock['code']}) - {stock['oversold_score']}/10分")
                logger.info(f"   价格: ¥{stock['close']:.2f} | 涨幅: {stock['change_pct']:+.2f}%")
                logger.info(f"   乖离率: {stock['bias_20']:.1f}% | RSI: {stock['rsi_6']:.1f}")
                logger.info(f"   成交额: {stock['turnover']/100000000:.2f}亿")
                logger.info("   评分详情:")
                for dim, detail in stock['oversold_details'].items():
                    logger.info(f"      {dim}: {detail}")
    
    return results


if __name__ == "__main__":
    main()
