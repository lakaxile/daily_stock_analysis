#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
改进版选股策略 - 加入AI建议的改进
1. 市场环境过滤
2. AI风险分析优化
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yfinance as yf
from datetime import datetime
import argparse
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def check_market_environment():
    """检查大盘环境是否适合做多"""
    logger.info("\n" + "="*60)
    logger.info("🌍 检查市场环境")
    logger.info("="*60)
    
    try:
        # 检查上证指数
        sh_index = yf.Ticker("000001.SS")
        sh_hist = sh_index.history(period='60d')
        
        if len(sh_hist) < 20:
            logger.warning("⚠️  上证指数数据不足")
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
        return True, f"检查失败: {e}"


def main():
    parser = argparse.ArgumentParser(description='改进版选股策略 - 先检查市场环境')
    parser.add_argument('--market-score', type=int, default=6, help='市场环境评分 (0-10)')
    parser.add_argument('--skip-check', action='store_true', help='跳过市场环境检查')
    
    args = parser.parse_args()
    
    logger.info("="*70)
    logger.info("🚀 改进版选股策略")
    logger.info("="*70)
    
    # AI建议1: 检查市场环境
    if not args.skip_check:
        market_ok, reason = check_market_environment()
        
        if not market_ok:
            logger.warning(f"\n❌ 市场环境不适合做多: {reason}")
            logger.warning("建议：观望或降低仓位至20%以下")
            logger.info("\n如仍要继续扫描，请使用 --skip-check 参数")
            return
    
    # 调用原有扫描器
    logger.info("\n市场环境检查通过，开始扫描...")
    from scripts.strategy_scanner import main as scanner_main
    scanner_main()


if __name__ == '__main__':
    main()
