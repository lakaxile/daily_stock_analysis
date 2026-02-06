#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
六维真强势策略全市场扫描器
基于复合交易系统：大盘环境 + 六维技术分析
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
import time

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


class SixDimensionScanner:
    """六维真强势策略扫描器"""
    
    def __init__(self, market_score: int = 10, enable_market_filter: bool = True):
        """
        初始化扫描器
        
        Args:
            market_score: 市场环境评分 (0-10)
        """
        self.market_score = market_score
        self.enable_market_filter = enable_market_filter
        self.market_env_ok = True  # 市场环境是否符合条件
        
        # 根据市场环境调整阈值（使用动态成交量比而非固定成交额）
        if market_score >= 8:  # 绿灯
            self.strategy = "策略A-六维真强势"
            self.min_price = 5.0
            self.min_volume_ratio = 0.5  # 要求今日成交量≥5日均量的50%
        elif market_score >= 5:  # 黄灯
            self.strategy = "策略A-六维真强势(谨慎)"
            self.min_price = 8.0
            self.min_volume_ratio = 0.6  # 要求今日成交量≥5日均量的60%
        else:  # 红灯
            self.strategy = "策略B-黄金坑反弹"
            self.min_price = 10.0
            self.min_volume_ratio = 0.8  # 要求今日成交量≥5日均量的80%
    
    def check_market_environment(self) -> Tuple[bool, str]:
        """检查大盘环境是否适合做多
        
        Returns:
            (是否符合条件, 详细说明)
        """
        logger.info("\n" + "="*60)
        logger.info("🌍 检查市场环境")
        logger.info("="*60)
        
        try:
            # 检查上证指数
            sh_index = yf.Ticker("000001.SS")
            sh_hist = sh_index.history(period='60d')
            
            if len(sh_hist) < 20:
                logger.warning("⚠️  上证指数数据不足，跳过市场检查")
                return True, "数据不足，跳过检查"
            
            # 计算均线
            sh_hist['MA5'] = sh_hist['Close'].rolling(window=5).mean()
            sh_hist['MA10'] = sh_hist['Close'].rolling(window=10).mean()
            sh_hist['MA20'] = sh_hist['Close'].rolling(window=20).mean()
            
            sh_close = float(sh_hist['Close'].iloc[-1])
            sh_ma5 = float(sh_hist['MA5'].iloc[-1])
            sh_ma10 = float(sh_hist['MA10'].iloc[-1])
            sh_ma20 = float(sh_hist['MA20'].iloc[-1])
            
            # 判断条件：收盘价站上MA20，且MA5 > MA10
            above_ma20 = sh_close > sh_ma20
            ma5_above_ma10 = sh_ma5 > sh_ma10
            
            logger.info(f"\n上证指数分析:")
            logger.info(f"  收盘价: {sh_close:.2f}")
            logger.info(f"  MA5: {sh_ma5:.2f}")
            logger.info(f"  MA10: {sh_ma10:.2f}")
            logger.info(f"  MA20: {sh_ma20:.2f}")
            logger.info(f"  站上MA20: {'✅' if above_ma20 else '❌'}")
            logger.info(f"  MA5>MA10: {'✅' if ma5_above_ma10 else '❌'}")
            
            if above_ma20 and ma5_above_ma10:
                logger.info(f"\n✅ 市场环境良好，适合做多")
                return True, "大盘站上MA20且MA5>MA10"
            else:
                logger.warning(f"\n⚠️  市场环境偏弱，建议降低仓位或观望")
                reason = []
                if not above_ma20:
                    reason.append("未站上MA20")
                if not ma5_above_ma10:
                    reason.append("MA5未上穿MA10")
                return False, "; ".join(reason)
                
        except Exception as e:
            logger.error(f"❌ 市场环境检查失败: {e}")
            return True, f"检查失败，默认通过: {e}"
    
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
            hist = stock.history(period='60d')  # 获取60天数据
            
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
            
            # 计算量比（用于后续的成交量筛选）
            hist['VOL_MA5'] = hist['Volume'].rolling(window=5).mean()
            vol_ma5 = float(hist['VOL_MA5'].iloc[-1])
            volume_ratio = volume / vol_ma5 if vol_ma5 > 0 else 0
            
            # 动态成交量筛选：今日成交量需要达到5日均量的一定比例
            if volume_ratio < self.min_volume_ratio:
                return None
            
            # 成交额（用于显示）
            turnover = close * volume
            
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
            
            # 量比已在上面计算过，这里不重复
            
            # RSI
            delta = hist['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=6).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=6).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            rsi_6 = float(rsi.iloc[-1]) if not np.isnan(rsi.iloc[-1]) else 50
            
            # 乖离率
            bias_20 = ((close - ma20) / ma20) * 100 if ma20 > 0 else 0
            
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
            
            # 尾盘强度（收盘价在当日区间的位置）
            if total_range > 0:
                close_position = ((close - low) / total_range) * 100
            else:
                close_position = 50
            
            # 振幅
            amplitude = ((high - low) / prev_close) * 100
            
            # 获取股票名称
            try:
                info = stock.info
                name = info.get('longName', '') or info.get('shortName', '') or f'股票{code}'
                # 简化中文名称
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
                'rsi_6': rsi_6,
                'bias_20': bias_20,
                'is_yang': is_yang,
                'body_ratio': body_ratio,
                'upper_shadow_ratio': upper_shadow_ratio,
                'lower_shadow_ratio': lower_shadow_ratio,
                'close_position': close_position,
                'amplitude': amplitude,
            }
            
        except Exception as e:
            return None
    
    def calculate_six_dimensions(self, data: Dict) -> Tuple[int, Dict]:
        """
        计算六维评分
        
        Returns:
            (总分, 详细评分字典)
        """
        score = 0
        details = {}
        
        # 1. 趋势维度 (0-2分)
        trend_score = 0
        if data['ma5'] > data['ma10'] > data['ma20']:
            trend_score += 2
            details['趋势'] = "✅ 多头排列 (+2)"
        elif data['close'] > data['ma5']:
            trend_score += 1
            details['趋势'] = "🟡 站上MA5 (+1)"
        else:
            details['趋势'] = "❌ 均线空头 (0)"
        score += trend_score
        
        # 2. K线维度 (0-2分)
        kline_score = 0
        if data['is_yang'] and data['body_ratio'] > 50 and data['upper_shadow_ratio'] < 25:
            kline_score += 2
            details['K线'] = "✅ 强势阳线 (+2)"
        elif data['is_yang']:
            kline_score += 1
            details['K线'] = "🟡 阳线 (+1)"
        else:
            details['K线'] = "❌ 阴线 (0)"
        score += kline_score
        
        # 3. 量能维度 (0-2分)
        volume_score = 0
        if data['is_yang'] and data['volume_ratio'] > 1.5:
            volume_score += 2
            details['量能'] = f"✅ 放量上涨 量比{data['volume_ratio']:.2f} (+2)"
        elif data['volume_ratio'] > 1.2:
            volume_score += 1
            details['量能'] = f"🟡 温和放量 量比{data['volume_ratio']:.2f} (+1)"
        else:
            details['量能'] = f"❌ 缩量 量比{data['volume_ratio']:.2f} (0)"
        score += volume_score
        
        # 4. 分时维度 (0-1分) - 用收盘价vs开盘价
        intraday_score = 0
        if data['close'] > data['open']:
            intraday_score += 1
            details['分时'] = "✅ 收盘高于开盘 (+1)"
        else:
            details['分时'] = "❌ 收盘低于开盘 (0)"
        score += intraday_score
        
        # 5. 盘口维度 (0-1分) - 用振幅和换手
        orderbook_score = 0
        if 2 < data['amplitude'] < 8:  # 适度振幅
            orderbook_score += 1
            details['盘口'] = f"✅ 振幅适中{data['amplitude']:.1f}% (+1)"
        else:
            details['盘口'] = f"❌ 振幅{data['amplitude']:.1f}% (0)"
        score += orderbook_score
        
        # 6. 尾盘维度 (0-2分) - 收盘价在区间位置
        closing_score = 0
        if data['close_position'] > 80:
            closing_score += 2
            details['尾盘'] = f"✅ 收于高位{data['close_position']:.0f}% (+2)"
        elif data['close_position'] > 60:
            closing_score += 1
            details['尾盘'] = f"🟡 收于中上{data['close_position']:.0f}% (+1)"
        else:
            details['尾盘'] = f"❌ 收于低位{data['close_position']:.0f}% (0)"
        score += closing_score
        
        return score, details
    
    def scan_market(self, max_workers: int = 10, sample_size: int = None) -> List[Dict]:
        """
        扫描全市场
        
        Args:
            max_workers: 并发线程数
            sample_size: 采样数量（测试用）
        """
        stock_list = self.get_stock_list()
        
        if sample_size:
            import random
            stock_list = random.sample(stock_list, min(sample_size, len(stock_list)))
        
        logger.info("=" * 70)
        logger.info(f"🔍 六维真强势策略全市场扫描")
        logger.info("=" * 70)
        logger.info(f"📊 市场环境: {self.market_score}/10 分")
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
                        score, details = self.calculate_six_dimensions(data)
                        
                        result = {
                            **data,
                            'six_dim_score': score,
                            'six_dim_details': details
                        }
                        
                        # 只保留A级以上
                        if score >= 6:
                            results.append(result)
                            
                            # 实时输出S级
                            if score >= 8:
                                logger.info(
                                    f"🏆 发现S级: {data['name']}({data['code']}) "
                                    f"评分{score}/10 涨幅{data['change_pct']:+.2f}%"
                                )
                except Exception as e:
                    pass
        
        logger.info("")
        logger.info("=" * 70)
        logger.info(f"✅ 扫描完成")
        logger.info(f"📊 总计扫描: {processed} 只")
        logger.info(f"📈 符合基础条件: {valid} 只")
        logger.info(f"🎯 A级以上: {len(results)} 只")
        logger.info("=" * 70)
        
        return sorted(results, key=lambda x: -x['six_dim_score'])


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='六维真强势策略扫描器')
    parser.add_argument('--market-score', type=int, default=10, help='市场环境评分 (0-10)')
    parser.add_argument('--workers', type=int, default=10, help='并发线程数')
    parser.add_argument('--sample', type=int, help='采样数量（测试用）')
    parser.add_argument('--min-score', type=int, default=6, help='最低评分阈值')
    
    args = parser.parse_args()
    
    # 创建扫描器
    scanner = SixDimensionScanner(market_score=args.market_score)
    
    # 扫描市场
    results = scanner.scan_market(max_workers=args.workers, sample_size=args.sample)
    
    # 统计
    s_level = [r for r in results if r['six_dim_score'] >= 8]
    a_level = [r for r in results if 6 <= r['six_dim_score'] < 8]
    
    logger.info("")
    logger.info("📊 评级统计:")
    logger.info(f"   S级 (8-10分): {len(s_level)} 只")
    logger.info(f"   A级 (6-7分): {len(a_level)} 只")
    
    # 保存结果
    if results:
        today = datetime.now().strftime('%Y-%m-%d')
        output_file = f'data/six_dimension_scan_{today}.csv'
        
        df = pd.DataFrame(results)
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        logger.info(f"\n✅ 结果已保存: {output_file}")
        
        # 输出S级详情
        if s_level:
            logger.info("\n" + "=" * 70)
            logger.info("🏆 S级股票详情 (8-10分)")
            logger.info("=" * 70)
            
            for i, stock in enumerate(s_level[:20], 1):  # 最多显示20只
                logger.info(f"\n{i}. {stock['name']}({stock['code']}) - {stock['six_dim_score']}/10分")
                logger.info(f"   涨幅: {stock['change_pct']:+.2f}% | 价格: ¥{stock['close']:.2f}")
                logger.info(f"   成交额: {stock['turnover']/100000000:.2f}亿")
                logger.info("   六维评分:")
                for dim, detail in stock['six_dim_details'].items():
                    logger.info(f"      {dim}: {detail}")
    
    return results


if __name__ == "__main__":
    main()
