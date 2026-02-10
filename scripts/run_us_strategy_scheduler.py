#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
美股联动策略定时调度器
每天 05:30 (北京时间) 自动执行，即美股收盘后约30分钟
"""

import sys
import os
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.scheduler import run_with_schedule
from scripts.us_a_cross_market import run as us_strategy_run

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
)

if __name__ == "__main__":
    print("🌐 美股联动策略调度器启动")
    print("⏰ 每日执行时间: 05:30 (北京时间)")
    print("按 Ctrl+C 退出\n")
    
    # 05:30 BJT = after US market close
    # run_immediately=False means it won't run right now, only at the scheduled time
    run_with_schedule(
        task=us_strategy_run,
        schedule_time="05:30",
        run_immediately=False
    )
