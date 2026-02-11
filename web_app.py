#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票分析Web应用 - 展示选股策略和分析报告
"""

from flask import Flask, render_template, send_from_directory, jsonify
import os
import json
import glob
from datetime import datetime
import markdown
import re

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')

# 导入股票名称映射
try:
    from src.analyzer import STOCK_NAME_MAP
except ImportError:
    STOCK_NAME_MAP = {}


def is_contain_chinese(check_str):
    """判断字符串是否包含中文字符"""
    if not check_str:
        return False
    for ch in check_str:
        if u'\u4e00' <= ch <= u'\u9fff':
            return True
    return False


def get_stock_name_from_sina(code):
    """从新浪财经获取股票中文名称"""
    try:
        import requests
        # 判断市场前缀
        prefix = 'sh' if code.startswith('6') else 'sz'
        url = f"http://hq.sinajs.cn/list={prefix}{code}"
        
        # 设置Headers防止反爬
        headers = {
            'Referer': 'https://finance.sina.com.cn/',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=2)
        if response.status_code == 200:
            content = response.text
            # 格式: var hq_str_sh600897="厦门空港,18.850,..."
            if '="' in content:
                data_str = content.split('="')[1]
                if data_str:
                    name = data_str.split(',')[0]
                    if is_contain_chinese(name):
                        return name
    except Exception as e:
        print(f"Error fetching from Sina: {e}")
    return None


def get_chinese_stock_name(code):
    """获取股票的中文名称"""
    # 1. 先从STOCK_NAME_MAP查找
    if code in STOCK_NAME_MAP:
        return STOCK_NAME_MAP[code]
    
    # 2. 从watchlist.json查找
    try:
        watchlist_file = os.path.join(DATA_DIR, 'watchlist.json')
        if os.path.exists(watchlist_file):
            with open(watchlist_file, 'r', encoding='utf-8') as f:
                watchlist = json.load(f)
                for date_stocks in watchlist.values():
                    for stock in date_stocks:
                        if str(stock.get('code')) == str(code) and stock.get('name'):
                            name = stock['name']
                            if is_contain_chinese(name):
                                return name
    except Exception as e:
        print(f"Error reading watchlist: {e}")
    
    # 3. 从CSV扫描结果查找
    try:
        import pandas as pd
        # 获取最新的CSV文件
        csv_files = sorted(glob.glob(os.path.join(DATA_DIR, 'six_dimension_scan_*.csv')), reverse=True)
        for csv_file in csv_files:
            try:
                df = pd.read_csv(csv_file)
                # 确保code列是字符串类型以便比较
                df['code'] = df['code'].astype(str)
                match = df[df['code'] == str(code)]
                
                if not match.empty:
                    # 尝试获取 'name' 或 '股票名称' 列
                    name = None
                    if 'name' in df.columns:
                        name = match.iloc[0]['name']
                    elif '股票名称' in df.columns:
                        name = match.iloc[0]['股票名称']
                    
                    if name and is_contain_chinese(str(name)):
                        return name
            except:
                continue
    except Exception as e:
        print(f"Error reading CSV: {e}")
        
    # 4. 从新浪财经尝试获取
    sina_name = get_stock_name_from_sina(code)
    if sina_name:
        return sina_name
    
    return None


def get_latest_files():
    """获取最新的分析文件"""
    files = {
        'comprehensive_analysis': None,
        'strategy_review': None,
        'strategy_improvements': None,
        'stock_analysis': [],
        'scan_results': None,
    }
    
    # 获取最新综合分析
    pattern = os.path.join(DATA_DIR, 'comprehensive_analysis_*.md')
    matches = sorted(glob.glob(pattern), reverse=True)
    if matches:
        files['comprehensive_analysis'] = matches[0]
    
    # 获取最新策略回顾
    pattern = os.path.join(DATA_DIR, 'strategy_review_*.md')
    matches = sorted(glob.glob(pattern), reverse=True)
    if matches:
        files['strategy_review'] = matches[0]
    
    # 获取策略改进
    pattern = os.path.join(DATA_DIR, 'strategy_improvements_*.md')
    matches = sorted(glob.glob(pattern), reverse=True)
    if matches:
        files['strategy_improvements'] = matches[0]
    
    # 获取个股分析（最新3个）
    pattern = os.path.join(DATA_DIR, 'stock_analysis_*.md')
    matches = sorted(glob.glob(pattern), reverse=True)[:3]
    files['stock_analysis'] = matches
    
    # 获取扫描结果CSV
    pattern = os.path.join(DATA_DIR, 'six_dimension_scan_*.csv')
    matches = sorted(glob.glob(pattern), reverse=True)
    if matches:
        files['scan_results'] = matches[0]
    
    return files


def get_available_report_dates():
    """获取所有可用的综合分析报告日期"""
    dates = set()
    
    # 扫描 comprehensive_analysis_*.md 和 daily_comprehensive_report_*.md
    patterns = [
        os.path.join(DATA_DIR, 'comprehensive_analysis_*.md'),
        os.path.join(DATA_DIR, 'daily_comprehensive_report_*.md'),
    ]
    
    for pattern in patterns:
        for filepath in glob.glob(pattern):
            # 从文件名提取日期
            filename = os.path.basename(filepath)
            match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
            if match:
                dates.add(match.group(1))
    
    # 按日期降序排序
    return sorted(dates, reverse=True)


def load_watchlist():
    """加载选股池"""
    watchlist_file = os.path.join(DATA_DIR, 'watchlist.json')
    try:
        with open(watchlist_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}


@app.route('/')
def index():
    """首页 - 策略概览"""
    files = get_latest_files()
    watchlist = load_watchlist()
    
    # 获取最新选股（六维策略）
    latest_date = max(watchlist.keys()) if watchlist else None
    latest_picks = watchlist.get(latest_date, []) if latest_date else []
    
    # 获取美股联动选股
    us_watchlist = load_us_watchlist()
    us_latest_date = max(us_watchlist.keys()) if us_watchlist else None
    us_picks = us_watchlist.get(us_latest_date, []) if us_latest_date else []
    
    return render_template('index.html', 
                         latest_date=latest_date,
                         picks=latest_picks,
                         us_latest_date=us_latest_date,
                         us_picks=us_picks,
                         files=files)


@app.route('/strategy')
def strategy():
    """策略详情"""
    files = get_latest_files()
    
    # 读取策略改进文档
    strategy_content = ""
    if files['strategy_improvements']:
        with open(files['strategy_improvements'], 'r', encoding='utf-8') as f:
            strategy_content = markdown.markdown(f.read(), extensions=['tables', 'fenced_code'])
    
    return render_template('strategy.html', content=strategy_content)


@app.route('/analysis')
def analysis():
    """分析报告 - 支持按日期查看"""
    from flask import request
    
    # 获取可用日期列表
    available_dates = get_available_report_dates()
    
    # 获取请求的日期，默认最新
    selected_date = request.args.get('date', available_dates[0] if available_dates else None)
    
    # 读取综合分析
    analysis_content = ""
    date = selected_date or '未知'
    
    if selected_date:
        # 尝试两种文件名格式
        possible_files = [
            os.path.join(DATA_DIR, f'comprehensive_analysis_{selected_date}.md'),
            os.path.join(DATA_DIR, f'daily_comprehensive_report_{selected_date}.md'),
        ]
        
        for filepath in possible_files:
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    analysis_content = markdown.markdown(content, extensions=['tables', 'fenced_code'])
                break
    
    return render_template('analysis.html', 
                         content=analysis_content,
                         date=date,
                         available_dates=available_dates,
                         selected_date=selected_date)


def load_us_watchlist():
    """加载美股联动选股池"""
    filepath = os.path.join(DATA_DIR, 'us_watchlist.json')
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def get_us_report_dates():
    """获取美股联动报告可用日期"""
    pattern = os.path.join(DATA_DIR, 'us_sector_report_*.md')
    files = glob.glob(pattern)
    dates = []
    for f in files:
        basename = os.path.basename(f)
        date_str = basename.replace('us_sector_report_', '').replace('.md', '')
        dates.append(date_str)
    dates.sort(reverse=True)
    return dates


@app.route('/us-strategy')
def us_strategy():
    """美股联动选股"""
    from flask import request

    us_watchlist = load_us_watchlist()
    available_dates = get_us_report_dates()

    # 也从 watchlist 的 keys 中补充日期
    for d in us_watchlist.keys():
        if d not in available_dates:
            available_dates.append(d)
    available_dates = sorted(list(set(available_dates)), reverse=True)

    selected_date = request.args.get('date', available_dates[0] if available_dates else None)

    picks = us_watchlist.get(selected_date, []) if selected_date else []

    # 读取对应日期的报告
    report_content = ""
    if selected_date:
        report_file = os.path.join(DATA_DIR, f'us_sector_report_{selected_date}.md')
        if os.path.exists(report_file):
            with open(report_file, 'r', encoding='utf-8') as f:
                report_content = markdown.markdown(f.read(), extensions=['tables', 'fenced_code'])

    return render_template('us_strategy.html',
                         picks=picks,
                         report_content=report_content,
                         available_dates=available_dates,
                         selected_date=selected_date)


def get_fund_flow_dates():
    """获取资金流向报告可用日期"""
    pattern = os.path.join(DATA_DIR, 'fund_flow_report_*.md')
    files = glob.glob(pattern)
    dates = []
    for f in files:
        basename = os.path.basename(f)
        date_str = basename.replace('fund_flow_report_', '').replace('.md', '')
        dates.append(date_str)
    dates.sort(reverse=True)
    return dates


@app.route('/fund-flow')
def fund_flow():
    """资金流向策略页面"""
    from flask import request
    
    available_dates = get_fund_flow_dates()
    selected_date = request.args.get('date', available_dates[0] if available_dates else None)
    
    report_content = ""
    if selected_date:
        report_file = os.path.join(DATA_DIR, f'fund_flow_report_{selected_date}.md')
        if os.path.exists(report_file):
            with open(report_file, 'r', encoding='utf-8') as f:
                report_content = markdown.markdown(f.read(), extensions=['tables', 'fenced_code'])
                
    return render_template('fund_flow.html',
                         report_content=report_content,
                         available_dates=available_dates,
                         selected_date=selected_date)


@app.route('/review')
def review():
    """策略回顾"""
    files = get_latest_files()
    
    # 读取策略回顾
    review_content = ""
    if files['strategy_review']:
        with open(files['strategy_review'], 'r', encoding='utf-8') as f:
            review_content = markdown.markdown(f.read(), extensions=['tables', 'fenced_code'])
    
    return render_template('review.html', content=review_content)


@app.route('/stock/<code>')
def stock_detail(code):
    """个股详情 - 实时分析展示"""
    try:
        import sys
        sys.path.insert(0, BASE_DIR)
        
        import yfinance as yf
        from src.analyzer import GeminiAnalyzer
        
        # 确定股票后缀
        ticker = f"{code}.SS" if code.startswith('6') else f"{code}.SZ"
        
        # 获取股票数据
        stock = yf.Ticker(ticker)
        hist = stock.history(period='60d')
        
        if len(hist) < 20:
            return render_template('stock_detail.html', error= f"股票 {code} 数据不足", code=code)
        
        # 计算技术指标
        today = hist.iloc[-1]
        yesterday = hist.iloc[-2]
        
        hist['MA5'] = hist['Close'].rolling(window=5).mean()
        hist['MA10'] = hist['Close'].rolling(window=10).mean()
        hist['MA20'] = hist['Close'].rolling(window=20).mean()
        hist['VOL_MA5'] = hist['Volume'].rolling(window=5).mean()
        
        # 获取中文股票名称
        chinese_name = get_chinese_stock_name(code)
        if not chinese_name:
            # 回退到yfinance的名称
            chinese_name = stock.info.get('longName', code) if hasattr(stock, 'info') else code
        
        # 提取数据
        data = {
            'code': code,
            'name': chinese_name,
            'yesterday_close': float(yesterday['Close']),
            'today_open': float(today['Open']),
            'today_high': float(today['High']),
            'today_low': float(today['Low']),
            'today_close': float(today['Close']),
            'today_volume': float(today['Volume']),
            'ma5': float(hist['MA5'].iloc[-1]),
            'ma10': float(hist['MA10'].iloc[-1]),
            'ma20': float(hist['MA20'].iloc[-1]),
            'volume_ratio': float(today['Volume'] / hist['VOL_MA5'].iloc[-1]) if hist['VOL_MA5'].iloc[-1] > 0 else 0,
        }
        
        # 计算衍生指标
        data['change_pct'] = ((data['today_close'] - data['yesterday_close']) / data['yesterday_close']) * 100
        data['amplitude'] = ((data['today_high'] - data['today_low']) / data['yesterday_close']) * 100
        
        if data['today_high'] != data['today_low']:
            data['close_position'] = ((data['today_close'] - data['today_low']) / (data['today_high'] - data['today_low'])) * 100
        else:
            data['close_position'] = 50
        
        # AI分析
        analyzer = GeminiAnalyzer()
        if analyzer.is_available():
            context = f"""
请分析股票{data['name']}({code})：

今日行情：昨收¥{data['yesterday_close']:.2f}，今开¥{data['today_open']:.2f}，今收¥{data['today_close']:.2f}，涨跌{data['change_pct']:+.2f}%，振幅{data['amplitude']:.2f}%，量比{data['volume_ratio']:.2f}x

技术指标：MA5 ¥{data['ma5']:.2f}，MA10 ¥{data['ma10']:.2f}，MA20 ¥{data['ma20']:.2f}，{'多头排列' if data['ma5'] > data['ma10'] > data['ma20'] else '非多头排列'}

请用简洁的语言（200字以内）回答：
1. 技术形态：当前是强势/弱势/震荡？
2. 操作建议：买入/观望/卖出？给出理由
3. 风险提示：最大风险是什么？

直接给出分析结果，不要JSON格式。
"""
            
            generation_config = {
                'temperature': 0.3,
                'max_output_tokens': 512,
            }
            
            try:
                ai_response = analyzer._call_api_with_retry(context, generation_config)
                data['ai_analysis'] = ai_response
            except Exception as e:
                data['ai_analysis'] = f'AI分析暂时不可用: {str(e)}'
        else:
            data['ai_analysis'] = 'AI分析未配置'
        
        return render_template('stock_detail.html', data=data, code=code)
        
    except Exception as e:
        return render_template('stock_detail.html', error=str(e), code=code)


@app.route('/api/watchlist')
def api_watchlist():
    """API - 获取选股池"""
    watchlist = load_watchlist()
    return jsonify(watchlist)


@app.route('/api/latest')
def api_latest():
    """API - 获取最新数据"""
    files = get_latest_files()
    watchlist = load_watchlist()
    
    latest_date = max(watchlist.keys()) if watchlist else None
    
    return jsonify({
        'date': latest_date,
        'picks': watchlist.get(latest_date, []) if latest_date else [],
        'files': {k: os.path.basename(v) if isinstance(v, str) else [os.path.basename(f) for f in v] 
                 for k, v in files.items()}
    })

@app.route('/api/realtime')
def api_realtime():
    """API - 批量获取实时行情 (Sina Finance)"""
    from flask import request as req
    import requests as http_requests
    
    codes = req.args.get('codes', '')
    if not codes:
        return jsonify({})
    
    code_list = [c.strip() for c in codes.split(',') if c.strip()]
    
    # 构建 Sina 查询字符串
    sina_codes = []
    for code in code_list:
        prefix = 'sh' if code.startswith('6') else 'sz'
        sina_codes.append(f"{prefix}{code}")
    
    url = f"http://hq.sinajs.cn/list={','.join(sina_codes)}"
    headers = {
        'Referer': 'https://finance.sina.com.cn/',
        'User-Agent': 'Mozilla/5.0'
    }
    
    result = {}
    try:
        resp = http_requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            for line in resp.text.strip().split('\n'):
                if '="' not in line:
                    continue
                # 提取代码
                var_part = line.split('="')[0]
                sina_code = var_part.split('_')[-1]
                raw_code = sina_code[2:]  # 去掉 sh/sz
                
                data_str = line.split('="')[1].rstrip('";')
                if not data_str:
                    continue
                
                fields = data_str.split(',')
                if len(fields) >= 4:
                    name = fields[0]
                    current_price = float(fields[3]) if fields[3] else 0
                    prev_close = float(fields[2]) if fields[2] else 0
                    
                    if prev_close > 0 and current_price > 0:
                        change_pct = ((current_price - prev_close) / prev_close) * 100
                        result[raw_code] = {
                            'name': name,
                            'price': round(current_price, 2),
                            'prev_close': round(prev_close, 2),
                            'change_pct': round(change_pct, 2),
                        }
    except Exception as e:
        print(f"Sina API error: {e}")
    
    return jsonify(result)


@app.route('/api/analyze/<code>')
def api_analyze_stock(code):
    """API - 实时分析股票"""
    try:
        import sys
        sys.path.insert(0, BASE_DIR)
        
        import yfinance as yf
        from src.analyzer import GeminiAnalyzer
        
        # 确定股票后缀
        ticker = f"{code}.SS" if code.startswith('6') else f"{code}.SZ"
        
        # 获取股票数据
        stock = yf.Ticker(ticker)
        hist = stock.history(period='60d')
        
        if len(hist) < 20:
            return jsonify({'error': '数据不足', 'code': code}), 400
        
        # 计算技术指标
        today = hist.iloc[-1]
        yesterday = hist.iloc[-2]
        
        hist['MA5'] = hist['Close'].rolling(window=5).mean()
        hist['MA10'] = hist['Close'].rolling(window=10).mean()
        hist['MA20'] = hist['Close'].rolling(window=20).mean()
        hist['VOL_MA5'] = hist['Volume'].rolling(window=5).mean()
        
        # 获取中文股票名称
        chinese_name = get_chinese_stock_name(code)
        if not chinese_name:
            # 回退到yfinance的名称
            chinese_name = stock.info.get('longName', code) if hasattr(stock, 'info') else code
        
        # 提取数据
        data = {
            'code': code,
            'name': chinese_name,
            'yesterday_close': float(yesterday['Close']),
            'today_open': float(today['Open']),
            'today_high': float(today['High']),
            'today_low': float(today['Low']),
            'today_close': float(today['Close']),
            'today_volume': float(today['Volume']),
            'ma5': float(hist['MA5'].iloc[-1]),
            'ma10': float(hist['MA10'].iloc[-1]),
            'ma20': float(hist['MA20'].iloc[-1]),
            'volume_ratio': float(today['Volume'] / hist['VOL_MA5'].iloc[-1]) if hist['VOL_MA5'].iloc[-1] > 0 else 0,
        }
        
        # 计算衍生指标
        data['change_pct'] = ((data['today_close'] - data['yesterday_close']) / data['yesterday_close']) * 100
        data['amplitude'] = ((data['today_high'] - data['today_low']) / data['yesterday_close']) * 100
        
        if data['today_high'] != data['today_low']:
            data['close_position'] = ((data['today_close'] - data['today_low']) / (data['today_high'] - data['today_low'])) * 100
        else:
            data['close_position'] = 50
        
        # AI分析
        analyzer = GeminiAnalyzer()
        if analyzer.is_available():
            context = f"""
请分析股票{data['name']}({code})：

今日行情：昨收¥{data['yesterday_close']:.2f}，今开¥{data['today_open']:.2f}，今收¥{data['today_close']:.2f}，涨跌{data['change_pct']:+.2f}%，振幅{data['amplitude']:.2f}%，量比{data['volume_ratio']:.2f}x

技术指标：MA5 ¥{data['ma5']:.2f}，MA10 ¥{data['ma10']:.2f}，MA20 ¥{data['ma20']:.2f}，{'多头排列' if data['ma5'] > data['ma10'] > data['ma20'] else '非多头排列'}

请用简洁的语言（150字以内）回答：
1. 技术形态：当前是强势/弱势/震荡？
2. 操作建议：买入/观望/卖出？给出理由
3. 风险提示：最大风险是什么？

直接给出分析结果，不要JSON格式。
"""
            
            generation_config = {
                'temperature': 0.3,
                'max_output_tokens': 512,
            }
            
            try:
                ai_response = analyzer._call_api_with_retry(context, generation_config)
                data['ai_analysis'] = ai_response
            except Exception as e:
                data['ai_analysis'] = f'AI分析暂时不可用: {str(e)}'
        else:
            data['ai_analysis'] = 'AI分析未配置'
        
        return jsonify({
            'success': True,
            'data': data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'code': code
        }), 500


if __name__ == '__main__':
    # 从环境变量获取端口，默认5000（Railway使用PORT环境变量）
    import os
    port = int(os.environ.get('PORT', 5000))
    
    # 生产环境关闭debug，开发环境开启
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    
    app.run(debug=debug_mode, host='0.0.0.0', port=port)
