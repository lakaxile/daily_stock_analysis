#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🌐 美股-A股联动策略 (US-A Cross-Market Strategy)

流程:
1. 扫描美股11大板块ETF涨跌幅
2. 识别当天热门板块 (涨幅 TOP 2-3)
3. 映射到A股对应板块的候选股列表
4. 通过 yfinance 获取A股候选股数据 (20线程)
5. AI 精选 5-8 只 + 生成报告
6. 自动发布到网站 (us_watchlist.json + report)
"""

import sys
import os
import json
import re
import logging
import time
import subprocess
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
os.makedirs(DATA_DIR, exist_ok=True)

# ============================================================
# 1. 美股板块 ETF 定义
# ============================================================
US_SECTOR_ETFS = {
    'XLK': {'name': 'Technology', 'cn': '科技', 'a_sectors': ['半导体', 'AI算力', '消费电子', '软件']},
    'XLV': {'name': 'Healthcare', 'cn': '医疗', 'a_sectors': ['创新药', 'CXO', '医疗器械']},
    'XLE': {'name': 'Energy', 'cn': '能源', 'a_sectors': ['石油', '煤炭', '天然气']},
    'XLF': {'name': 'Financials', 'cn': '金融', 'a_sectors': ['券商', '保险', '银行']},
    'XLY': {'name': 'Consumer Disc.', 'cn': '可选消费', 'a_sectors': ['白酒', '家电', '汽车']},
    'XLP': {'name': 'Consumer Staples', 'cn': '必选消费', 'a_sectors': ['食品', '农业', '零售']},
    'XLI': {'name': 'Industrials', 'cn': '工业', 'a_sectors': ['军工', '机械', '航空']},
    'XLB': {'name': 'Materials', 'cn': '材料', 'a_sectors': ['化工', '有色金属', '钢铁']},
    'XLRE': {'name': 'Real Estate', 'cn': '地产', 'a_sectors': ['房地产', '建材']},
    'XLU': {'name': 'Utilities', 'cn': '公用事业', 'a_sectors': ['电力', '水务', '环保']},
    'XLC': {'name': 'Communication', 'cn': '通信', 'a_sectors': ['传媒', '游戏', '通信设备']},
}

# ============================================================
# 2. A股板块成分股映射表
#    每个板块预置核心成分股代码（约50只/板块）
# ============================================================
A_SHARE_SECTOR_STOCKS = {
    '半导体': [
        '688981', '002049', '603986', '300661', '688008', '002371', '688012',
        '300223', '002185', '600584', '688396', '603501', '300666', '688082',
        '002156', '300782', '688521', '603160', '688072', '300373',
    ],
    'AI算力': [
        '002230', '000977', '300474', '688256', '688041', '603019', '300496',
        '002415', '688561', '300124', '002236', '688036', '300418', '603236',
        '002405', '688111', '300308', '002464', '688051', '300033',
    ],
    '消费电子': [
        '002241', '002475', '002938', '300115', '002036', '002600', '603160',
        '002957', '300433', '002456', '300207', '002351', '603501', '002384',
        '300812', '603920', '002833', '300567', '002426', '300780',
    ],
    '软件': [
        '300033', '300188', '300454', '002410', '300378', '688111', '600588',
        '300579', '002279', '300253', '688318', '300479', '002474', '600845',
        '002063', '300339', '600536', '300170', '002368', '688078',
    ],
    '创新药': [
        '688180', '300760', '688276', '300347', '002821', '300529', '300142',
        '688428', '300558', '002422', '300199', '300725', '688177', '002399',
        '002603', '300009', '600276', '000513', '688566', '300601',
    ],
    'CXO': [
        '300347', '603259', '300759', '300363', '002821', '002430', '300725',
        '688526', '300438', '603127', '300497', '688131', '300357', '688180',
        '002252', '603456', '300326', '000661', '688399', '300404',
    ],
    '医疗器械': [
        '300760', '300003', '300015', '002223', '300633', '688289', '300396',
        '002432', '600529', '603290', '002901', '300562', '688580', '300693',
        '688536', '002950', '300677', '300030', '603658', '300206',
    ],
    '石油': [
        '601857', '600028', '600871', '002554', '600688', '002207', '000637',
        '002353', '000407', '601808', '600339', '002828', '000552', '600546',
        '002221', '603619', '000698', '600583', '002629', '603727',
    ],
    '煤炭': [
        '601088', '600188', '601898', '600348', '601699', '601225', '600985',
        '601666', '000983', '600395', '601001', '600121', '600123', '000552',
        '600971', '600508', '601015', '002128', '600740', '600397',
    ],
    '天然气': [
        '600256', '603393', '002267', '300483', '600333', '000593', '002443',
        '603053', '000669', '002911', '002629', '603106', '600635', '600917',
        '002549', '000968', '600777', '600681', '002455', '300164',
    ],
    '券商': [
        '601211', '000776', '600030', '601688', '000166', '600837', '002736',
        '601377', '000617', '601878', '600999', '601901', '601066', '002500',
        '000750', '601198', '600958', '002673', '600369', '002797',
    ],
    '保险': [
        '601318', '601628', '601601', '000627', '601336', '002423', '600291',
    ],
    '银行': [
        '601398', '601939', '601988', '600036', '000001', '601166', '600000',
        '601818', '002142', '600016', '601328', '600015', '601229', '002839',
        '601169', '001227', '601838', '601997', '600919', '601128',
    ],
    '白酒': [
        '600519', '000858', '000568', '002304', '600809', '000799', '603369',
        '600779', '000596', '603198', '600559', '000860', '600702', '600199',
        '000869', '002646', '603589', '600197', '600600', '600690',
    ],
    '家电': [
        '000651', '000333', '002032', '600060', '600690', '002508', '002035',
        '002242', '000921', '002050', '002959', '000418', '600854', '603486',
        '002705', '603868', '002429', '600619', '000521', '000541',
    ],
    '汽车': [
        '002594', '601238', '000625', '600104', '600733', '601633', '000800',
        '002920', '300750', '002074', '603799', '300124', '300014', '002048',
        '002488', '601127', '000338', '002239', '603348', '600006',
    ],
    '食品': [
        '603288', '002557', '600597', '002847', '600887', '603027', '002507',
        '002715', '300146', '600882', '603345', '002330', '600073', '600300',
        '002216', '300741', '603517', '002991', '002570', '603697',
    ],
    '农业': [
        '000998', '600598', '002714', '600438', '002385', '000876', '002157',
        '300087', '600354', '600975', '000895', '002458', '002299', '002215',
        '002100', '600313', '603363', '002548', '300189', '000713',
    ],
    '军工': [
        '600893', '600760', '000768', '600118', '000738', '002179', '002013',
        '600862', '600316', '002414', '600877', '601989', '601698', '002025',
        '600150', '000519', '600685', '600038', '000547', '002190',
    ],
    '机械': [
        '600031', '002008', '601100', '000528', '603596', '601766', '000157',
        '601608', '002353', '603515', '600169', '601669', '002527', '300124',
        '002270', '600320', '603338', '000425', '600815', '002444',
    ],
    '化工': [
        '600309', '000792', '600352', '002064', '000830', '600141', '601216',
        '002601', '600426', '002643', '000525', '600346', '002648', '000698',
        '603260', '300037', '002539', '300409', '600299', '000553',
    ],
    '有色金属': [
        '601899', '600489', '601600', '000878', '002460', '002466', '600362',
        '600547', '601212', '000831', '600311', '002203', '003816', '002340',
        '600259', '600497', '600711', '601168', '000630', '002171',
    ],
    '电力': [
        '600900', '600886', '000027', '601985', '600795', '600011', '000600',
        '600023', '600578', '600905', '601991', '000883', '600310', '600236',
        '001289', '003816', '600969', '600268', '000601', '600505',
    ],
    '传媒': [
        '300413', '002624', '300459', '300251', '002607', '300133', '002555',
        '600373', '000681', '002292', '002354', '300113', '300043', '603533',
        '002174', '600637', '603444', '002343', '300148', '300364',
    ],
    '游戏': [
        '002602', '002555', '300418', '002517', '300315', '002174', '300052',
        '002354', '300031', '603444', '002264', '002027', '600158', '000682',
        '600640', '300148', '002261', '300113', '603000', '300043',
    ],
}

# ============================================================
# 3. 核心逻辑
# ============================================================

def scan_us_sectors():
    """扫描美股11大板块ETF，返回各板块涨跌幅"""
    logger.info("🇺🇸 扫描美股板块 ETF...")
    
    results = []
    etf_symbols = list(US_SECTOR_ETFS.keys())
    
    for symbol in etf_symbols:
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="2d")
            if hist.empty or len(hist) < 2:
                continue
            
            prev_close = hist['Close'].iloc[-2]
            last_close = hist['Close'].iloc[-1]
            change_pct = ((last_close - prev_close) / prev_close) * 100
            
            info = US_SECTOR_ETFS[symbol]
            results.append({
                'etf': symbol,
                'name': info['name'],
                'cn': info['cn'],
                'close': round(last_close, 2),
                'change_pct': round(change_pct, 2),
                'a_sectors': info['a_sectors'],
            })
            logger.info(f"  {symbol} ({info['cn']}): {change_pct:+.2f}%")
        except Exception as e:
            logger.warning(f"  {symbol} 获取失败: {e}")
    
    # Sort by change_pct descending
    results.sort(key=lambda x: x['change_pct'], reverse=True)
    return results


def identify_hot_sectors(us_results):
    """识别热门板块 (涨幅 > 1% 的 Top 2-3 个)"""
    hot = [r for r in us_results if r['change_pct'] > 1.0]
    
    if not hot:
        # 如果没有板块涨幅 > 1%，取涨幅最高的2个（除非全面大跌）
        if us_results and us_results[0]['change_pct'] > -1.0:
            hot = us_results[:2]
            logger.info("⚠️ 无强热门板块，取涨幅靠前的2个板块")
        else:
            logger.warning("❌ 美股全面下跌，今日不推荐")
            return []
    
    # Cap at 3 sectors
    hot = hot[:3]
    
    logger.info(f"\n🔥 识别到 {len(hot)} 个热门板块:")
    for s in hot:
        logger.info(f"  {s['cn']} ({s['etf']}): {s['change_pct']:+.2f}% → A股映射: {', '.join(s['a_sectors'])}")
    
    return hot


def get_candidate_codes(hot_sectors):
    """根据热门板块获取A股候选股代码列表"""
    codes = set()
    for sector in hot_sectors:
        for a_sector in sector['a_sectors']:
            if a_sector in A_SHARE_SECTOR_STOCKS:
                codes.update(A_SHARE_SECTOR_STOCKS[a_sector])
    
    codes = sorted(list(codes))
    logger.info(f"\n📋 候选池: {len(codes)} 只A股")
    return codes


def get_chinese_name(code):
    """从新浪财经获取股票中文名称"""
    try:
        import requests
        prefix = 'sh' if code.startswith('6') else 'sz'
        url = f"http://hq.sinajs.cn/list={prefix}{code}"
        headers = {
            'Referer': 'https://finance.sina.com.cn/',
            'User-Agent': 'Mozilla/5.0'
        }
        resp = requests.get(url, headers=headers, timeout=2)
        if resp.status_code == 200 and '="' in resp.text:
            data_str = resp.text.split('="')[1]
            if data_str:
                name = data_str.split(',')[0]
                if name:
                    return name
    except Exception:
        pass
    return None


def fetch_stock_data(code):
    """获取单只A股数据"""
    suffix = ".SS" if code.startswith("6") else ".SZ"
    ticker_symbol = f"{code}{suffix}"
    
    try:
        ticker = yf.Ticker(ticker_symbol)
        hist = ticker.history(period="20d")
        
        if hist.empty or len(hist) < 5:
            return None
        
        latest = hist.iloc[-1]
        prev = hist.iloc[-2]
        
        close = latest['Close']
        change_pct = ((close - prev['Close']) / prev['Close']) * 100
        volume = latest['Volume']
        avg_volume_5d = hist['Volume'].iloc[-6:-1].mean()
        volume_ratio = volume / avg_volume_5d if avg_volume_5d > 0 else 0
        
        # MA5 trend
        ma5 = hist['Close'].iloc[-5:].mean()
        ma5_prev = hist['Close'].iloc[-6:-1].mean()
        ma5_up = ma5 > ma5_prev
        
        # MA10, MA20
        ma10 = hist['Close'].iloc[-10:].mean() if len(hist) >= 10 else ma5
        ma20 = hist['Close'].iloc[-20:].mean() if len(hist) >= 20 else ma10
        
        # Get stock name (Chinese)
        name = get_chinese_name(code) or ticker.info.get('shortName', code)
        
        # Estimated daily turnover (CNY)
        turnover = close * volume
        
        return {
            'code': code,
            'name': name,
            'close': round(close, 2),
            'change_pct': round(change_pct, 2),
            'volume_ratio': round(volume_ratio, 2),
            'ma5': round(ma5, 2),
            'ma10': round(ma10, 2),
            'ma20': round(ma20, 2),
            'ma5_up': ma5_up,
            'turnover': turnover,
            'bullish': close > ma5 and ma5 > ma10,  # 简单多头判断
        }
    except Exception:
        return None


def scan_a_share_candidates(codes):
    """并发扫描A股候选池 (20线程)"""
    logger.info(f"\n🔍 扫描 {len(codes)} 只A股候选 (20线程)...")
    
    results = []
    processed = 0
    
    with ThreadPoolExecutor(max_workers=20) as executor:
        future_to_code = {executor.submit(fetch_stock_data, code): code for code in codes}
        
        for future in as_completed(future_to_code):
            processed += 1
            try:
                data = future.result()
                if data is None:
                    continue
                
                # 基本筛选
                if data['close'] < 3.0:
                    continue
                if data['turnover'] < 50_000_000:  # 5000万
                    continue
                if not data['ma5_up']:
                    continue
                if 'ST' in str(data['name']):
                    continue
                    
                results.append(data)
            except Exception:
                pass
            
            if processed % 50 == 0:
                logger.info(f"  进度: {processed}/{len(codes)} - 通过筛选: {len(results)}")
    
    # Sort by bullish + change_pct
    results.sort(key=lambda x: (x['bullish'], x['change_pct']), reverse=True)
    
    logger.info(f"\n✅ 初筛通过: {len(results)} 只")
    return results


def ai_select_stocks(candidates, hot_sectors):
    """调用 AI 从候选池中精选 5-8 只"""
    from src.analyzer import GeminiAnalyzer
    
    if not candidates:
        return ""
    
    # 构建候选列表字符串
    stock_lines = []
    for s in candidates[:40]:  # 限制发给 AI 的数量
        bull_tag = "📈多头" if s['bullish'] else "📊"
        stock_lines.append(
            f"{s['code']} {s['name']} ¥{s['close']} ({s['change_pct']:+.2f}%) "
            f"量比{s['volume_ratio']} {bull_tag}"
        )
    stock_list_str = "\n".join(stock_lines)
    
    # 热门板块描述
    sector_desc = ", ".join([f"{s['cn']}({s['etf']} {s['change_pct']:+.2f}%)" for s in hot_sectors])
    
    prompt = f"""
You are a Chinese stock market expert specializing in US-China cross-market analysis.

**Today's US Market Hot Sectors**: {sector_desc}

**A-Share Candidate Stocks** (filtered from sectors correlated with US hot sectors):
{stock_list_str}

**Task**: Select the **best 5-8 stocks** from the candidate list that are most likely to benefit from today's US sector momentum. Consider:
1. Direct correlation to the US hot sector theme
2. Technical strength (bullish MA alignment, volume ratio > 1)
3. Near-term catalyst potential

**Output Requirements**:
1. Output a Markdown table with columns: 代码, 名称, 现价, 涨幅, 关联板块, 推荐理由
2. After the table, write a brief 2-3 sentence market outlook in Chinese
3. Do NOT output JSON or code blocks
4. Write content in Chinese
"""
    
    analyzer = GeminiAnalyzer()
    response = analyzer._call_api_with_retry(prompt, {'temperature': 0.5})
    
    # Cleanup
    response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL).strip()
    return response


def generate_detailed_report(selected_text, hot_sectors, candidates, us_results):
    """生成完整的每日报告"""
    today = datetime.now().strftime('%Y-%m-%d')
    gen_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # US sector table
    us_table = "| ETF | 板块 | 涨跌幅 |\n|---|---|---|\n"
    for r in us_results:
        emoji = "🔥" if r['change_pct'] > 1 else ("🟢" if r['change_pct'] > 0 else "🔴")
        us_table += f"| {r['etf']} | {r['cn']} | {emoji} {r['change_pct']:+.2f}% |\n"
    
    hot_desc = "、".join([f"**{s['cn']}**({s['change_pct']:+.2f}%)" for s in hot_sectors])
    
    report = f"""# 🌐 美股联动选股报告 - {today}

**生成时间**: {gen_time}
**策略**: 美股板块热度 → A股联动选股

> **风险提示**: 本报告由 AI 自动生成，仅供参考，不构成投资建议。

---

## 📊 美股板块全景

{us_table}

**今日热门板块**: {hot_desc}

---

## 🎯 A股精选推荐

{selected_text}

---

## 📝 策略说明

本策略基于"美股板块轮动领先A股"的逻辑：
1. 每日美股收盘后扫描11大板块ETF
2. 识别涨幅最强的2-3个板块
3. 映射到A股对应行业，筛选技术面健康的个股
4. AI综合评估后精选推荐

**候选池统计**: 初筛 {len(candidates)} 只 → AI精选 5-8 只
"""
    return report


def publish_results(selected_text, hot_sectors, candidates, us_results):
    """发布结果到网站"""
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 1. Generate report
    report = generate_detailed_report(selected_text, hot_sectors, candidates, us_results)
    report_file = os.path.join(DATA_DIR, f'us_sector_report_{today}.md')
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    logger.info(f"✅ 报告已保存: {report_file}")
    
    # 2. Update us_watchlist.json
    # Parse the AI response table to extract stock entries
    watchlist_file = os.path.join(DATA_DIR, 'us_watchlist.json')
    
    # Load existing
    if os.path.exists(watchlist_file):
        with open(watchlist_file, 'r', encoding='utf-8') as f:
            watchlist = json.load(f)
    else:
        watchlist = {}
    
    # Extract entries from candidates that were in the AI selection
    # Simple approach: use top candidates as watchlist entries
    entries = []
    for s in candidates[:8]:
        sector_names = []
        for hs in hot_sectors:
            sector_names.extend(hs['a_sectors'])
        
        entries.append({
            "code": s['code'],
            "name": s['name'],
            "score": 8 if s['bullish'] else 6,
            "change_pct": s['change_pct'],
            "price": s['close'],
            "reason": f"🌐 美股联动 - 量比{s['volume_ratio']}"
        })
    
    watchlist[today] = entries
    
    with open(watchlist_file, 'w', encoding='utf-8') as f:
        json.dump(watchlist, f, indent=2, ensure_ascii=False)
    logger.info(f"✅ us_watchlist.json 已更新 ({len(entries)} 只)")
    
    return report_file


def git_push():
    """自动推送到 GitHub"""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        subprocess.run(['git', 'add', 'data/us_watchlist.json', f'data/us_sector_report_{today}.md'],
                       cwd=project_root, check=True)
        subprocess.run(['git', 'commit', '-m', f'[Auto] US-A Cross-Market picks for {today}'],
                       cwd=project_root, check=True)
        subprocess.run(['git', 'push', 'origin', 'main'],
                       cwd=project_root, check=True)
        logger.info("✅ Git push 成功，Railway 将自动部署")
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Git push 失败: {e}")


# ============================================================
# 4. 主入口
# ============================================================

def run():
    """执行完整的美股联动选股流程"""
    logger.info("=" * 60)
    logger.info("🌐 美股-A股联动策略 启动")
    logger.info(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    
    # Step 1: 扫描美股板块
    us_results = scan_us_sectors()
    if not us_results:
        logger.error("美股板块数据获取失败，终止")
        return
    
    # Step 2: 识别热门板块
    hot_sectors = identify_hot_sectors(us_results)
    if not hot_sectors:
        logger.warning("今日无推荐板块，终止")
        return
    
    # Step 3: 获取A股候选代码
    codes = get_candidate_codes(hot_sectors)
    if not codes:
        logger.warning("无候选股票，终止")
        return
    
    # Step 4: 扫描A股候选池
    candidates = scan_a_share_candidates(codes)
    if not candidates:
        logger.warning("无通过初筛的候选股，终止")
        return
    
    # Step 5: AI 精选
    logger.info("\n🤖 AI 精选中...")
    selected_text = ai_select_stocks(candidates, hot_sectors)
    
    if not selected_text:
        logger.warning("AI 精选失败")
        return
    
    # Step 6: 发布
    publish_results(selected_text, hot_sectors, candidates, us_results)
    
    # Step 7: Git push (可选，在 Railway 环境中可能不需要)
    if os.environ.get('AUTO_GIT_PUSH', '').lower() == 'true':
        git_push()
    
    logger.info("\n" + "=" * 60)
    logger.info("🏁 美股联动策略执行完毕")
    logger.info("=" * 60)


if __name__ == "__main__":
    run()
