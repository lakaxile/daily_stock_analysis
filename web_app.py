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
    
    # 获取最新选股
    latest_date = max(watchlist.keys()) if watchlist else None
    latest_picks = watchlist.get(latest_date, []) if latest_date else []
    
    return render_template('index.html', 
                         latest_date=latest_date,
                         picks=latest_picks,
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
    """分析报告"""
    files = get_latest_files()
    
    # 读取综合分析
    analysis_content = ""
    if files['comprehensive_analysis']:
        with open(files['comprehensive_analysis'], 'r', encoding='utf-8') as f:
            content = f.read()
            # 提取日期
            date_match = re.search(r'\((\d{4}-\d{2}-\d{2})\)', content)
            date = date_match.group(1) if date_match else '未知'
            analysis_content = markdown.markdown(content, extensions=['tables', 'fenced_code'])
    
    return render_template('analysis.html', 
                         content=analysis_content,
                         date=date if 'date' in locals() else '未知')


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
    """个股详情"""
    # 查找该股票的最新分析
    pattern = os.path.join(DATA_DIR, f'stock_analysis_{code}_*.md')
    matches = sorted(glob.glob(pattern), reverse=True)
    
    if not matches:
        return "未找到该股票分析", 404
    
    with open(matches[0], 'r', encoding='utf-8') as f:
        content = markdown.markdown(f.read(), extensions=['tables', 'fenced_code'])
    
    return render_template('stock_detail.html', content=content, code=code)


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
        
        # 提取数据
        data = {
            'code': code,
            'name': stock.info.get('longName', code) if hasattr(stock, 'info') else code,
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
