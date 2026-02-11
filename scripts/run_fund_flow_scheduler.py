
import schedule
import time
import os
import sys
import logging
from datetime import datetime

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from scripts.fund_flow_strategy import FundFlowScanner, save_results

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def run_fund_flow_scan():
    logger.info("⏰ Triggering Scheduled Fund Flow Scan...")
    try:
        scanner = FundFlowScanner()
        results = scanner.run()
        
        today = datetime.now().strftime('%Y-%m-%d')
        save_results(results, today)
        
        # Git Push (Optional)
        if os.environ.get('AUTO_GIT_PUSH') == 'true':
            logger.info("Pushing changes to Git...")
            import subprocess
            subprocess.run(["git", "add", "data/."], check=False)
            subprocess.run(["git", "commit", "-m", f"Auto-update fund flow data {today}"], check=False)
            subprocess.run(["git", "push"], check=False)
            
    except Exception as e:
        logger.error(f"❌ Error in scheduled scan: {e}")

if __name__ == "__main__":
    logger.info("🚀 Fund Flow Scheduler Started")
    logger.info("   Schedule: Daily at 15:30")
    
    # Run immediately if --now flag is passed
    if len(sys.argv) > 1 and sys.argv[1] == '--now':
        run_fund_flow_scan()
    
    # Schedule
    schedule.every().day.at("15:30").do(run_fund_flow_scan)
    
    while True:
        schedule.run_pending()
        time.sleep(60)
