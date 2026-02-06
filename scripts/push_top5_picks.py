#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
推送今日精选股票到企业微信并保存到选股池
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import pandas as pd
from datetime import datetime
import logging
import requests

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def load_top5_stocks():
    """加载今日精选TOP 5股票"""
    df = pd.read_csv('data/six_dimension_scan_2026-02-05.csv')
    
    # 读取TOP 5（基于综合评分）
    top5_codes = ['002003', '600436', '600754', '600897', '600305']
    
    stocks = []
    for code in top5_codes:
        stock_data = df[df['code'].astype(str) == code]
        if len(stock_data) > 0:
            stocks.append(stock_data.iloc[0])
    
    return stocks


def create_wechat_message(stocks):
    """创建企业微信消息"""
    today = datetime.now().strftime('%Y-%m-%d')
    
    message = f"""# 📊 明日买入精选 ({today})

## 🎯 TOP 5 股票池

"""
    
    stock_names = {
        '002003': '伟星股份',
        '600436': '漳州片仔癀',
        '600754': '锦江酒店',
        '600897': '厦门国贸',
        '600305': '恒顺醋业'
    }
    
    positions = ['🥇 首选', '🥈 稳健', '🥉 趋势', '4️⃣ 均衡', '5️⃣ 防御']
    position_pcts = ['15%', '15%', '10%', '5%', '5%']
    
    for i, stock in enumerate(stocks):
        code = str(stock['code'])
        name = stock_names.get(code, stock['name'])
        market = '[深A]' if code.startswith(('0', '3')) else '[沪A]'
        
        message += f"""
### {positions[i]} {name} ({code}) {market}

- 评分: **{stock['six_dim_score']}/10**
- 涨幅: **{stock['change_pct']:+.2f}%**
- 价格: ¥{stock['close']:.2f}
- 量比: {stock['volume_ratio']:.2f}x
- 建议仓位: **{position_pcts[i]}**
"""
    
    message += """
---

## 📋 操作要点

- **总仓位**: 50% (半仓)
- **止损**: 统一-5%
- **目标**: 组合+5-8%
- **周期**: 3-5个交易日

## ⚠️ 风险提示

1. 等待回调买入，避免追高
2. 分批建仓，留有加仓空间
3. 严格止损纪律
4. 关注大盘走势

---
**市场环境**: 6.4/10 黄灯
**生成时间**: """ + datetime.now().strftime('%Y-%m-%d %H:%M')
    
    return message


def save_to_watchlist(stocks):
    """保存到选股池"""
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 读取现有watchlist
    try:
        with open('data/watchlist.json', 'r', encoding='utf-8') as f:
            watchlist = json.load(f)
    except:
        watchlist = {}
    
    stock_names = {
        '002003': '伟星股份',
        '600436': '漳州片仔癀',
        '600754': '锦江酒店',
        '600897': '厦门国贸',
        '600305': '恒顺醋业'
    }
    
    # 创建今日选股
    today_picks = []
    for stock in stocks:
        code = str(stock['code'])
        today_picks.append({
            'code': code,
            'name': stock_names.get(code, stock['name']),
            'score': int(stock['six_dim_score'] * 10),
            'change_pct': float(stock['change_pct']),
            'price': float(stock['close']),
            'volume_ratio': float(stock['volume_ratio']),
            'trend': '多头排列' if '多头排列' in str(stock.get('six_dim_details', '')) else '站上MA5',
            'operation_advice': '买入',
            'added_date': today,
            'last_check': today,
            'status': 'active',
            'removal_reason': None
        })
    
    # 保存
    watchlist[today] = today_picks
    
    with open('data/watchlist.json', 'w', encoding='utf-8') as f:
        json.dump(watchlist, f, ensure_ascii=False, indent=2)
    
    logger.info(f"✅ 已保存 {len(today_picks)} 只股票到选股池: {today}")
    return today_picks


def send_to_wechat(message):
    """发送消息到企业微信"""
    from dotenv import load_dotenv
    load_dotenv()
    
    # 兼容两种环境变量名
    webhook_url = os.getenv('WECHAT_WEBHOOK_URL') or os.getenv('WECHAT_WEBHOOK')
    
    if not webhook_url:
        logger.warning("⚠️  未配置企业微信 Webhook")
        logger.info("💡 请在.env文件中添加: WECHAT_WEBHOOK=你的webhook地址")
        return False
    
    payload = {
        "msgtype": "markdown",
        "markdown": {
            "content": message
        }
    }  
    
    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if result.get('errcode') == 0:
                return True
            else:
                logger.error(f"企业微信返回错误: {result}")
                return False
        else:
            logger.error(f"HTTP请求失败: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"发送失败: {e}")
        return False


def main():
    logger.info("="*70)
    logger.info("📤 推送今日精选股票")
    logger.info("="*70)
    
    # 1. 加载TOP 5股票
    logger.info("\n📊 加载TOP 5股票...")
    stocks = load_top5_stocks()
    logger.info(f"✅ 加载成功: {len(stocks)} 只股票")
    
    # 2. 保存到选股池
    logger.info("\n💾 保存到选股池...")
    watchlist_stocks = save_to_watchlist(stocks)
    
    # 3. 推送到企业微信
    logger.info("\n📤 推送到企业微信...")
    message = create_wechat_message(stocks)
    
    success = send_to_wechat(message)
    
    if success:
        logger.info("✅ 企业微信推送成功！")
    else:
        logger.warning("⚠️  企业微信推送失败")
    
    logger.info("\n" + "="*70)
    logger.info("✅ 任务完成")
    logger.info(f"   - 选股池: data/watchlist.json")
    logger.info(f"   - 操作计划: data/tomorrow_trading_plan_2026-02-06.md")
    logger.info("="*70)


if __name__ == "__main__":
    main()
