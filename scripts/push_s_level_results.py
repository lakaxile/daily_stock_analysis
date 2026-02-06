import re
import json
import logging
import sys
import os
from typing import List, Dict, Any

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.scanner import ScanResult, MarketScanner
from src.analyzer import AnalysisResult

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

def parse_log_for_s_level(log_path: str) -> List[ScanResult]:
    """
    Parse scan log for S-level stocks.
    Strategy:
    1. Find all '[LLM解析] ... 评分 XX' lines to identify S-level stocks.
    2. Try to capture associated JSON for details, but fallback to summary if JSON fails.
    """
    
    if not os.path.exists(log_path):
        logger.error(f"Log file not found: {log_path}")
        return []

    logger.info(f"Reading log file: {log_path}")
    with open(log_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    s_level_map = {} # code -> ScanResult
    
    # helper to process json buffer
    def process_json(buffer, code, name):
        if not buffer or not code: return None
        try:
            json_str = "".join(buffer)
            # Cleanup markdown
            json_str = json_str.replace("```json", "").replace("```", "")
            data = json.loads(json_str)
            return data
        except:
            return None

    current_code = None
    current_name = None
    json_buffer = []
    in_json_block = False
    
    for line in lines:
        # 1. Check for Basic Result Line (High Priority reliability)
        # 2026-02-03 ... | [LLM解析] 建新股份(300107) 分析完成: 强烈看多, 评分 85
        match_res = re.search(r'\[LLM解析\] (.*?)\((\d+)\) 分析完成: (.*?), 评分 (\d+)', line)
        if match_res:
            name = match_res.group(1)
            code = match_res.group(2)
            trend = match_res.group(3)
            score = int(match_res.group(4))
            
            # If JSON block was open, try to close and parse it for THIS code if it matches
            if in_json_block:
                in_json_block = False
                if current_code == code:
                    details = process_json(json_buffer, code, name)
                    if details:
                        # We have full details!
                        logger.info(f"Captured FULL details for {name}({code})")
                        if score >= 80:
                            s_level_map[code] = create_scan_result(code, name, score, trend, details)
                        continue 

            # If we didn't get JSON details (or parsing failed), but Score is High
            if score >= 80:
                if code not in s_level_map:
                    logger.info(f"Found S-level stock (Basic Info): {name}({code}) - Score: {score}")
                    s_level_map[code] = create_scan_result(code, name, score, trend, None)
            
            # Reset extraction state
            current_code = None
            in_json_block = False
            json_buffer = []
            continue

        # 2. Check for Start of Analysis (Context for JSON)
        match_start = re.search(r'========== AI 分析 (.*?)\((\d+)\) ==========', line)
        if match_start:
            current_name = match_start.group(1)
            current_code = match_start.group(2)
            in_json_block = False
            json_buffer = []
            continue

        # 3. JSON Extraction
        if '[LLM返回 预览]' in line:
            continue
            
        if line.strip().startswith('```json'):
            in_json_block = True
            json_buffer = []
            continue
            
        if in_json_block:
            # Ignore log headers inside JSON
            if re.match(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', line):
                continue
                
            if line.strip().startswith('```') and len(line.strip()) < 5:
                in_json_block = False
                # Try parsing immediately
                data = process_json(json_buffer, current_code, current_name)
                # Store temporarily? No, wait for confirmation line (match_res) to verify score and consistency
                # Actually, we can store it now if we want, but better to link with "Analysis Complete".
                # Let's keep loop going.
            else:
                json_buffer.append(line)

    return list(s_level_map.values())

def create_scan_result(code, name, score, trend, details_data):
    """Create ScanResult object, using details_data if available."""
    
    # Defaults
    op_advice = "买入" if score >= 80 else "观望"
    conf_level = "高"
    dashboard = {}
    
    if details_data:
        op_advice = details_data.get('operation_advice', op_advice)
        conf_level = details_data.get('confidence_level', conf_level)
        trend = details_data.get('trend_prediction', trend)
        dashboard = details_data.get('dashboard', {})
        # Merge basic info into dashboard if missing
        if 'core_conclusion' not in dashboard:
            dashboard['core_conclusion'] = {
                "one_sentence": f"评分 {score}，趋势 {trend}",
                "signal_type": "🟢买入信号"
            }
    else:
        # Construct dummy dashboard for basic info
        dashboard = {
            "core_conclusion": {
                "one_sentence": f"[S级] 评分 {score}，趋势 {trend} (详细数据解析失败，仅显示基础信息)",
                "signal_type": "🟢买入信号",
                "time_sensitivity": "立即行动"
            },
            "battle_plan": {
                 "sniper_points": {
                     "ideal_buy": "请参考技术面",
                     "stop_loss": "MA10或前低"
                 }
            }
        }

    # Reconstruct AnalysisResult
    analysis_result = AnalysisResult(
        code=code,
        name=name,
        sentiment_score=score,
        trend_prediction=trend,
        operation_advice=op_advice,
        confidence_level=conf_level,
        dashboard=dashboard,
        analysis_summary=dashboard.get('core_conclusion', {}).get('one_sentence', '')
    )
    
    # Get price from details or 0
    price = 0
    try:
        price = details_data.get('dashboard', {}).get('data_perspective', {}).get('price_position', {}).get('current_price', 0)
    except:
        pass

    return ScanResult(
        code=code,
        name=name,
        score=score,
        level="S",
        operation_advice=op_advice,
        trend_prediction=trend,
        current_price=price,
        ma5=0, ma10=0, ma20=0,
        analysis_result=analysis_result
    )

def main():
    log_file = "full_scan_log.txt"
    results = parse_log_for_s_level(log_file)
    
    if not results:
        logger.warning("No S-level stocks found in the log.")
        return

    logger.info(f"Total S-level stocks found: {len(results)}")
    
    # Push to Wechat
    scanner = MarketScanner()
    logger.info("Pushing results to notification channels...")
    scanner.notify_s_level(results)
    logger.info("Done.")

if __name__ == "__main__":
    main()
