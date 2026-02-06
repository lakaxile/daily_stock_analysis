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


if __name__ == '__main__':
    # 从环境变量获取端口，默认5000（Railway使用PORT环境变量）
    import os
    port = int(os.environ.get('PORT', 5000))
    
    # 生产环境关闭debug，开发环境开启
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    
    app.run(debug=debug_mode, host='0.0.0.0', port=port)
