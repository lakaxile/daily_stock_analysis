import requests
import json
import os
import datetime
import time
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

# Configuration
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
OUTPUT_JSON = os.path.join(DATA_DIR, 'fund_flow.json')
OUTPUT_MD = os.path.join(DATA_DIR, 'fund_flow_report_{date}.md')

class FundFlowScanner:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    def get_top_sectors(self, top_n=5):
        """Fetch all sectors and return top N by Net Inflow (f62)"""
        url = "http://push2.eastmoney.com/api/qt/clist/get"
        params = {
            "pn": 1,
            "pz": 100,  # Get top 100 sectors
            "po": 1,
            "np": 1,
            "fltt": 2,
            "invt": 2,
            "fid": "f62",
            "fs": "m:90+t:2",
            "fields": "f12,f14,f2,f3,f62,f10"  # Code, Name, Price, Change%, NetInflow, VolumeRatio?
        }
        try:
            resp = requests.get(url, params=params, headers=self.headers, timeout=10)
            data = resp.json()
            if not data.get('data'):
                return []
            
            sectors = data['data']['diff']
            # Sort by Net Inflow (f62) descending
            # Note: f62 might be '-' for some
            valid_sectors = [s for s in sectors if isinstance(s.get('f62'), (int, float))]
            valid_sectors.sort(key=lambda x: x['f62'], reverse=True)
            
            return valid_sectors[:top_n]
        except Exception as e:
            print(f"Error fetching sectors: {e}")
            return []

    def get_sector_stocks(self, sector_code, top_n=5):
        """Fetch stocks in a sector, sorted by Net Inflow"""
        url = "http://push2.eastmoney.com/api/qt/clist/get"
        # fs for block: b:BKxxxx
        params = {
            "pn": 1,
            "pz": 20, # Get top 20 to filter
            "po": 1,
            "np": 1,
            "fltt": 2,
            "invt": 2,
            "fid": "f62",
            "fs": f"b:{sector_code}",
            "fields": "f12,f14,f2,f3,f62,f10"
        }
        try:
            resp = requests.get(url, params=params, headers=self.headers, timeout=10)
            data = resp.json()
            if not data.get('data'):
                return []
            
            stocks = data['data']['diff']
            # Filter valid stocks
            valid_stocks = []
            for s in stocks:
                # Basic filter: exclude ST, Price < 2, Change < 0?
                name = s.get('f14', '')
                price = s.get('f2', 0)
                inflow = s.get('f62', 0)
                
                if 'ST' in name or '退' in name:
                    continue
                if price == '-' or float(price) < 2.0:
                    continue
                if not isinstance(inflow, (int, float)):
                    continue
                    
                valid_stocks.append(s)
            
            valid_stocks.sort(key=lambda x: x['f62'], reverse=True)
            return valid_stocks[:top_n]
        except Exception as e:
            print(f"Error fetching stocks for {sector_code}: {e}")
            return []

    def run(self):
        print("🚀 Starting Sector Fund Flow Scan...")
        top_sectors = self.get_top_sectors(top_n=5)
        
        results = []
        for rank, sec in enumerate(top_sectors, 1):
            sec_name = sec['f14']
            sec_code = sec['f12']
            inflow = sec['f62']
            change = sec['f3']
            
            print(f"Analyzing Sector #{rank}: {sec_name} (Inflow: {inflow/100000000:.2f}亿, Change: {change}%)")
            
            stocks = self.get_sector_stocks(sec_code, top_n=5)
            
            stock_list = []
            for s in stocks:
                stock_list.append({
                    "code": s['f12'],
                    "name": s['f14'],
                    "price": s['f2'],
                    "change_pct": s['f3'],
                    "net_inflow": s['f62']
                })
                
            results.append({
                "rank": rank,
                "code": sec_code,
                "name": sec_name,
                "net_inflow": inflow,
                "change_pct": change,
                "stocks": stock_list
            })
            
            time.sleep(0.5) # Courtesy delay
            
        return results

def save_results(results, date_str):
    # 1. Save JSON
    final_data = {}
    if os.path.exists(OUTPUT_JSON):
        try:
            with open(OUTPUT_JSON, 'r') as f:
                final_data = json.load(f)
        except:
            pass
    
    final_data[date_str] = results
    
    with open(OUTPUT_JSON, 'w') as f:
        json.dump(final_data, f, indent=2, ensure_ascii=False)
        
    print(f"✅ Saved results to {OUTPUT_JSON}")

    # 2. Generate Markdown Report
    md_file = OUTPUT_MD.format(date=date_str)
    with open(md_file, 'w') as f:
        f.write(f"# 💸 资金流向策略报告 ({date_str})\n\n")
        f.write(f"**策略逻辑**: 捕捉全市场主力资金净流入前5的板块，并精选板块内净流入前5的龙头股。\n\n")
        f.write(f"---\n\n")
        
        for sec in results:
            inflow_yi = sec['net_inflow'] / 100000000
            f.write(f"## {sec['rank']}. {sec['name']} (BK{sec['code']})\n")
            f.write(f"- **主力净流入**: {inflow_yi:.2f} 亿\n")
            f.write(f"- **板块涨跌**: {sec['change_pct']}%\n\n")
            
            f.write(f"| 代码 | 名称 | 现价 | 涨跌幅 | 主力净流入 | \n")
            f.write(f"|---|---|---|---|---| \n")
            for s in sec['stocks']:
                s_inflow_yi = s['net_inflow'] / 100000000
                change_color = "red" if s['change_pct'] > 0 else "green"
                f.write(f"| {s['code']} | {s['name']} | {s['price']} | {s['change_pct']}% | {s_inflow_yi:.2f} 亿 |\n")
            f.write("\n---\n\n")
            
    print(f"✅ Generated report: {md_file}")
    return md_file

if __name__ == "__main__":
    scanner = FundFlowScanner()
    results = scanner.run()
    
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    report_file = save_results(results, today)
