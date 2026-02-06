"""
自选股池管理模块
Author: AI Assistant
Date: 2026-02-03

功能：
- 按日期分类存储S级股票
- 验证昨日股票是否仍满足买入条件
- 自动移除不合格股票
"""

import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class WatchlistStock:
    """自选股数据结构"""
    code: str
    name: str
    score: int
    trend: str
    operation_advice: str
    added_date: str  # YYYY-MM-DD
    last_check: str  # YYYY-MM-DD
    status: str  # active, removed
    removal_reason: Optional[str] = None
    
    def to_dict(self):
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)


class WatchlistManager:
    """自选股池管理器"""
    
    def __init__(self, data_file: str = "data/watchlist.json"):
        self.data_file = data_file
        self._ensure_data_dir()
        self.watchlist = self._load()
        
    def _ensure_data_dir(self):
        """确保数据目录存在"""
        data_dir = os.path.dirname(self.data_file)
        if data_dir and not os.path.exists(data_dir):
            os.makedirs(data_dir)
            logger.info(f"[Watchlist] 创建数据目录: {data_dir}")
    
    def _load(self) -> Dict[str, List[dict]]:
        """加载自选股数据"""
        if not os.path.exists(self.data_file):
            logger.info(f"[Watchlist] 数据文件不存在，创建新文件: {self.data_file}")
            return {}
        
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info(f"[Watchlist] 加载数据成功，共 {len(data)} 个日期")
                return data
        except Exception as e:
            logger.error(f"[Watchlist] 加载数据失败: {e}")
            return {}
    
    def _save(self):
        """保存自选股数据"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.watchlist, f, ensure_ascii=False, indent=2)
            logger.info(f"[Watchlist] 保存数据成功")
        except Exception as e:
            logger.error(f"[Watchlist] 保存数据失败: {e}")
    
    def add_stocks(self, date: str, stocks: List['ScanResult']):
        """
        添加股票到指定日期池
        
        Args:
            date: YYYY-MM-DD
            stocks: ScanResult 列表
        """
        if date not in self.watchlist:
            self.watchlist[date] = []
        
        existing_codes = {s['code'] for s in self.watchlist[date]}
        added_count = 0
        
        for stock in stocks:
            if stock.code not in existing_codes:
                ws = WatchlistStock(
                    code=stock.code,
                    name=stock.name,
                    score=stock.score,
                    trend=stock.trend_prediction,
                    operation_advice=stock.operation_advice,
                    added_date=date,
                    last_check=date,
                    status="active"
                )
                self.watchlist[date].append(ws.to_dict())
                added_count += 1
        
        self._save()
        logger.info(f"[Watchlist] {date} 添加 {added_count} 只股票（已跳过 {len(stocks) - added_count} 只重复）")
        return added_count
    
    def get_stocks(self, date: str) -> List[WatchlistStock]:
        """获取指定日期的股票"""
        if date not in self.watchlist:
            return []
        
        return [WatchlistStock.from_dict(s) for s in self.watchlist[date]]
    
    def get_yesterday_stocks(self) -> List[WatchlistStock]:
        """获取昨日活跃股票"""
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        stocks = self.get_stocks(yesterday)
        return [s for s in stocks if s.status == "active"]
    
    def get_all_active_stocks(self) -> List[WatchlistStock]:
        """获取所有日期的活跃股票"""
        all_stocks = []
        for date in self.watchlist:
            stocks = self.get_stocks(date)
            all_stocks.extend([s for s in stocks if s.status == "active"])
        return all_stocks
    
    def update_stock_status(self, code: str, date: str, status: str, reason: Optional[str] = None):
        """
        更新股票状态
        
        Args:
            code: 股票代码
            date: 日期
            status: active/removed
            reason: 移除原因
        """
        if date not in self.watchlist:
            logger.warning(f"[Watchlist] 日期 {date} 不存在")
            return False
        
        for stock in self.watchlist[date]:
            if stock['code'] == code:
                stock['status'] = status
                stock['last_check'] = datetime.now().strftime('%Y-%m-%d')
                if reason:
                    stock['removal_reason'] = reason
                self._save()
                logger.info(f"[Watchlist] 更新 {code} 状态: {status}")
                return True
        
        logger.warning(f"[Watchlist] 股票 {code} 在日期 {date} 中未找到")
        return False
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        total_dates = len(self.watchlist)
        total_stocks = sum(len(stocks) for stocks in self.watchlist.values())
        active_stocks = len(self.get_all_active_stocks())
        
        return {
            "total_dates": total_dates,
            "total_stocks": total_stocks,
            "active_stocks": active_stocks,
            "removed_stocks": total_stocks - active_stocks
        }
    
    def cleanup_old_dates(self, keep_days: int = 30):
        """清理旧数据（保留最近N天）"""
        cutoff_date = (datetime.now() - timedelta(days=keep_days)).strftime('%Y-%m-%d')
        dates_to_remove = [d for d in self.watchlist.keys() if d < cutoff_date]
        
        for date in dates_to_remove:
            del self.watchlist[date]
            logger.info(f"[Watchlist] 清理旧数据: {date}")
        
        if dates_to_remove:
            self._save()
            logger.info(f"[Watchlist] 共清理 {len(dates_to_remove)} 个日期的数据")
        
        return len(dates_to_remove)


# 测试代码
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # 创建管理器
    wm = WatchlistManager("data/watchlist_test.json")
    
    # 打印统计
    stats = wm.get_stats()
    print(f"统计: {stats}")
    
    # 获取昨日股票
    yesterday_stocks = wm.get_yesterday_stocks()
    print(f"昨日活跃股票: {len(yesterday_stocks)} 只")
