#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
六维真强势策略 - 全自动扫描脚本 (优化版)
1. 自动评估市场环境
2. 根据环境调整策略参数
3. 高并发执行全市场扫描
4. 支持实时保存中间结果
"""

import sys
import os
import logging
import pandas as pd
from datetime import datetime
import concurrent.futures

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.strategy_scanner import SixDimensionScanner

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def save_csv(results, filename):
    if not results:
        return
    
    df = pd.DataFrame(results)
    # 确保关键列存在
    cols = ['code', 'name', 'six_dim_score', 'change_pct', 'close', 'volume_ratio', 'six_dim_details']
    # 补充其他列
    for col in df.columns:
        if col not in cols:
            cols.append(col)
    
    # 重排各列，把关键信息放前面
    final_cols = []
    for c in ['code', 'name', 'six_dim_score', 'change_pct', 'volume_ratio', 'close']:
        if c in cols:
            final_cols.append(c)
            cols.remove(c)
    final_cols.extend(cols)
    
    df = df[final_cols]
    df.to_csv(filename, index=False, encoding='utf-8-sig')

def run():
    print("🚀 启动全自动选股流程 (优化版)...")
    print(f"⏰ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. 初始化扫描器
    scanner = SixDimensionScanner(market_score=10)
    
    # 2. 市场环境评估
    print("\n" + "="*50)
    print("🌍 正在评估市场环境...")
    is_market_good, reason = scanner.check_market_environment()
    
    market_score = 0
    if is_market_good:
        print(f"✅ 市场环境: 良好 ({reason})")
        market_score = 9
    else:
        print(f"⚠️ 市场环境: 偏弱 ({reason})")
        if "未站上MA20" in reason and "MA5未上穿MA10" in reason:
            market_score = 4
            print("🛑 策略调整: 防御模式 (仅选取超跌反弹或极强势股)")
        else:
            market_score = 6
            print("🟡 策略调整: 谨慎模式 (提高选股门槛)")
            
    # 3. 重新初始化扫描器
    scanner = SixDimensionScanner(market_score=market_score)
    print(f"🛠️  应用策略: {scanner.strategy}")
    print(f"   - 最低价格: {scanner.min_price}")
    print(f"   - 量比要求: >{scanner.min_volume_ratio}")
    print(f"   - 线程数: 50 (极速扫描)")
    
    # 4. 获取股票列表
    stock_list = scanner.get_stock_list()
    # 简单的去重
    stock_list = sorted(list(set(stock_list)))
    
    print(f"\n📋 准备扫描 {len(stock_list)} 只股票...")
    
    results = []
    processed = 0
    valid_count = 0
    start_time = datetime.now()
    
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
    os.makedirs(output_dir, exist_ok=True)
    today = datetime.now().strftime('%Y-%m-%d')
    output_file = os.path.join(output_dir, f'six_dimension_scan_{today}.csv')
    temp_file = os.path.join(output_dir, f'six_dimension_scan_{today}_temp.csv')

    # 5. 并发扫描
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        future_to_code = {executor.submit(scanner.fetch_stock_data, code): code 
                        for code in stock_list}
        
        for future in concurrent.futures.as_completed(future_to_code):
            processed += 1
            code = future_to_code[future]
            
            try:
                data = future.result()
                if data:
                    valid_count += 1
                    score, details = scanner.calculate_six_dimensions(data)
                    
                    # 只有达到最低分才保存 (通常是6分)
                    if score >= 6:
                        result = {
                            **data,
                            'six_dim_score': score,
                            'six_dim_details': details
                        }
                        results.append(result)
                        
                        # 实时播报 S级
                        if score >= 8:
                            print(f"🏆 发现S级: {data['name']}({code}) {score}分 涨幅{data['change_pct']:+.2f}%")
                            
            except Exception as e:
                # 忽略单个错误
                pass
                
            # 进度提示
            if processed % 200 == 0:
                elapsed = (datetime.now() - start_time).total_seconds()
                speed = processed / elapsed
                percent = processed / len(stock_list) * 100
                print(f"进度: {processed}/{len(stock_list)} ({percent:.1f}%) - 速度: {speed:.1f}只/秒 - 发现: {len(results)}只")
                
            # 自动保存中间结果 (每500只)
            if processed % 500 == 0 and results:
                save_csv(results, temp_file)

    print("\n" + "="*50)
    print("📊 最终统计:")
    s_level = [r for r in results if r['six_dim_score'] >= 8]
    a_level = [r for r in results if 6 <= r['six_dim_score'] < 8] 
    
    print(f"   总扫描: {processed}")
    print(f"   有效数据: {valid_count}")
    print(f"   S级 (8-10分): {len(s_level)} 只")
    print(f"   A级 (6-7分): {len(a_level)} 只")
    
    # 最终保存
    if results:
        # 按分数排序
        results.sort(key=lambda x: -x['six_dim_score'])
        save_csv(results, output_file)
        print(f"✅ 结果已保存至: {output_file}")
        
        # 删除临时文件
        if os.path.exists(temp_file):
            os.remove(temp_file)
    else:
        print("⚠️ 未发现符合条件的股票")

if __name__ == "__main__":
    run()
