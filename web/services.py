# -*- coding: utf-8 -*-
"""
===================================
Web 服务层 - 业务逻辑
===================================

职责：
1. 配置管理服务 (ConfigService)
2. 分析任务服务 (AnalysisService)
"""

from __future__ import annotations

import os
import re
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Optional, Dict, Any, List, Union

from src.enums import ReportType
from bot.models import BotMessage

logger = logging.getLogger(__name__)

# ============================================================
# 配置管理服务
# ============================================================

_ENV_PATH = os.getenv("ENV_FILE", ".env")

_STOCK_LIST_RE = re.compile(
    r"^(?P<prefix>\s*STOCK_LIST\s*=\s*)(?P<value>.*?)(?P<suffix>\s*)$"
)


class ConfigService:
    """
    配置管理服务
    
    负责 .env 文件中 STOCK_LIST 的读写操作
    """
    
    def __init__(self, env_path: Optional[str] = None):
        self.env_path = env_path or _ENV_PATH
    
    def read_env_text(self) -> str:
        """读取 .env 文件内容"""
        try:
            with open(self.env_path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            return ""
    
    def write_env_text(self, text: str) -> None:
        """写入 .env 文件内容"""
        with open(self.env_path, "w", encoding="utf-8") as f:
            f.write(text)
    
    def get_stock_list(self) -> str:
        """获取当前自选股列表字符串"""
        env_text = self.read_env_text()
        return self._extract_stock_list(env_text)
    
    def set_stock_list(self, stock_list: str) -> str:
        """
        设置自选股列表
        
        Args:
            stock_list: 股票代码字符串（逗号或换行分隔）
            
        Returns:
            规范化后的股票列表字符串
        """
        env_text = self.read_env_text()
        normalized = self._normalize_stock_list(stock_list)
        updated = self._update_stock_list(env_text, normalized)
        self.write_env_text(updated)
        return normalized
    
    def get_env_filename(self) -> str:
        """获取 .env 文件名"""
        return os.path.basename(self.env_path)
    
    def _extract_stock_list(self, env_text: str) -> str:
        """从环境文件中提取 STOCK_LIST 值"""
        for line in env_text.splitlines():
            m = _STOCK_LIST_RE.match(line)
            if m:
                raw = m.group("value").strip()
                # 去除引号
                if (raw.startswith('"') and raw.endswith('"')) or \
                   (raw.startswith("'") and raw.endswith("'")):
                    raw = raw[1:-1]
                return raw
        return ""
    
    def _normalize_stock_list(self, value: str) -> str:
        """规范化股票列表格式"""
        parts = [p.strip() for p in value.replace("\n", ",").split(",")]
        parts = [p for p in parts if p]
        return ",".join(parts)
    
    def _update_stock_list(self, env_text: str, new_value: str) -> str:
        """更新环境文件中的 STOCK_LIST"""
        lines = env_text.splitlines(keepends=False)
        out_lines: List[str] = []
        replaced = False
        
        for line in lines:
            m = _STOCK_LIST_RE.match(line)
            if not m:
                out_lines.append(line)
                continue
            
            out_lines.append(f"{m.group('prefix')}{new_value}{m.group('suffix')}")
            replaced = True
        
        if not replaced:
            if out_lines and out_lines[-1].strip() != "":
                out_lines.append("")
            out_lines.append(f"STOCK_LIST={new_value}")
        
        trailing_newline = env_text.endswith("\n") if env_text else True
        out = "\n".join(out_lines)
        return out + ("\n" if trailing_newline else "")


# ============================================================
# 分析任务服务
# ============================================================

class AnalysisService:
    """
    分析任务服务
    
    负责：
    1. 管理异步分析任务
    2. 执行股票分析
    3. 触发通知推送
    """
    
    _instance: Optional['AnalysisService'] = None
    _lock = threading.Lock()
    
    def __init__(self, max_workers: int = 3):
        self._executor: Optional[ThreadPoolExecutor] = None
        self._max_workers = max_workers
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._tasks_lock = threading.Lock()
    
    @classmethod
    def get_instance(cls) -> 'AnalysisService':
        """获取单例实例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    @property
    def executor(self) -> ThreadPoolExecutor:
        """获取或创建线程池"""
        if self._executor is None:
            self._executor = ThreadPoolExecutor(
                max_workers=self._max_workers,
                thread_name_prefix="analysis_"
            )
        return self._executor
    
    def submit_analysis(
        self, 
        code: str, 
        report_type: Union[ReportType, str] = ReportType.SIMPLE,
        source_message: Optional[BotMessage] = None
    ) -> Dict[str, Any]:
        """
        提交异步分析任务
        
        Args:
            code: 股票代码
            report_type: 报告类型枚举
            
        Returns:
            任务信息字典
        """
        # 确保 report_type 是枚举类型
        if isinstance(report_type, str):
            report_type = ReportType.from_str(report_type)
        
        task_id = f"{code}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        # 提交到线程池
        self.executor.submit(self._run_analysis, code, task_id, report_type, source_message)
        
        logger.info(f"[AnalysisService] 已提交股票 {code} 的分析任务, task_id={task_id}, report_type={report_type.value}")
        
        return {
            "success": True,
            "message": "分析任务已提交，将异步执行并推送通知",
            "code": code,
            "task_id": task_id,
            "report_type": report_type.value
        }
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        with self._tasks_lock:
            return self._tasks.get(task_id)
    
    def list_tasks(self, limit: int = 20) -> List[Dict[str, Any]]:
        """列出最近的任务"""
        with self._tasks_lock:
            tasks = list(self._tasks.values())
        # 按开始时间倒序
        tasks.sort(key=lambda x: x.get('start_time', ''), reverse=True)
        return tasks[:limit]
    
    def _run_analysis(
        self, 
        code: str, 
        task_id: str, 
        report_type: ReportType = ReportType.SIMPLE,
        source_message: Optional[BotMessage] = None
    ) -> Dict[str, Any]:
        """
        执行单只股票分析
        
        内部方法，在线程池中运行
        
        Args:
            code: 股票代码
            task_id: 任务ID
            report_type: 报告类型枚举
        """
        # 初始化任务状态
        with self._tasks_lock:
            self._tasks[task_id] = {
                "task_id": task_id,
                "code": code,
                "status": "running",
                "start_time": datetime.now().isoformat(),
                "result": None,
                "error": None,
                "report_type": report_type.value
            }
        
        try:
            # 延迟导入避免循环依赖
            from src.config import get_config
            from main import StockAnalysisPipeline
            
            logger.info(f"[AnalysisService] 开始分析股票: {code}")
            
            # 创建分析管道
            config = get_config()
            pipeline = StockAnalysisPipeline(
                config=config,
                max_workers=1,
                source_message=source_message
            )
            
            # 执行单只股票分析（启用单股推送）
            result = pipeline.process_single_stock(
                code=code,
                skip_analysis=False,
                single_stock_notify=True,
                report_type=report_type
            )
            
            if result:
                result_data = {
                    "code": result.code,
                    "name": result.name,
                    "sentiment_score": result.sentiment_score,
                    "operation_advice": result.operation_advice,
                    "trend_prediction": result.trend_prediction,
                    "analysis_summary": result.analysis_summary,
                }
                
                with self._tasks_lock:
                    self._tasks[task_id].update({
                        "status": "completed",
                        "end_time": datetime.now().isoformat(),
                        "result": result_data
                    })
                
                logger.info(f"[AnalysisService] 股票 {code} 分析完成: {result.operation_advice}")
                return {"success": True, "task_id": task_id, "result": result_data}
            else:
                with self._tasks_lock:
                    self._tasks[task_id].update({
                        "status": "failed",
                        "end_time": datetime.now().isoformat(),
                        "error": "分析返回空结果"
                    })
                
                logger.warning(f"[AnalysisService] 股票 {code} 分析失败: 返回空结果")
                return {"success": False, "task_id": task_id, "error": "分析返回空结果"}
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"[AnalysisService] 股票 {code} 分析异常: {error_msg}")
            
            with self._tasks_lock:
                self._tasks[task_id].update({
                    "status": "failed",
                    "end_time": datetime.now().isoformat(),
                    "error": error_msg
                })
            
            return {"success": False, "task_id": task_id, "error": error_msg}


# ============================================================
# 分析结果服务
# ============================================================

class StockResultsService:
    """
    分析结果服务
    
    负责解析今日报告文件，提取股票分析结果
    """
    
    _REPORT_DIR = "src/reports"
    
    # 解析报告摘要行的正则
    # 匹配格式: 🟢 **四方股份(601126)**: 买入 | 评分 75 | 看多
    _SUMMARY_RE = re.compile(
        r'^[🟢🟡🔴⚪🟠]\s*\*\*(.+?)\((\w+)\)\*\*:\s*(.+?)\s*\|\s*评分\s*(\d+)\s*\|\s*(.+)$'
    )
    
    def get_today_results(self) -> List[Dict[str, Any]]:
        """
        获取今日分析结果
        
        Returns:
            股票结果列表，每项包含: code, name, operation_advice, sentiment_score, trend_prediction
        """
        today = datetime.now().strftime('%Y%m%d')
        report_path = os.path.join(self._REPORT_DIR, f"report_{today}.md")
        
        if not os.path.exists(report_path):
            logger.warning(f"[StockResultsService] 今日报告不存在: {report_path}")
            return []
        
        results = []
        try:
            with open(report_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    m = self._SUMMARY_RE.match(line)
                    if m:
                        results.append({
                            'name': m.group(1),
                            'code': m.group(2),
                            'operation_advice': m.group(3).strip(),
                            'sentiment_score': int(m.group(4)),
                            'trend_prediction': m.group(5).strip()
                        })
            
            logger.info(f"[StockResultsService] 解析到 {len(results)} 只股票的今日分析结果")
        except Exception as e:
            logger.error(f"[StockResultsService] 解析报告失败: {e}")
        
        return results

    def get_report_content(self, date_str: str = None) -> Optional[str]:
        """
        获取指定日期的报告内容
        
        Args:
            date_str: 日期字符串 YYYYMMDD，默认今天
        """
        if not date_str:
            date_str = datetime.now().strftime('%Y%m%d')
        
        report_path = os.path.join(self._REPORT_DIR, f"report_{date_str}.md")
        
        if not os.path.exists(report_path):
            return None
        
        try:
            with open(report_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"[StockResultsService] 读取报告失败: {e}")
            return None

    def list_reports(self, limit: int = 7) -> List[Dict[str, str]]:
        """
        列出最近的报告文件
        """
        import glob
        pattern = os.path.join(self._REPORT_DIR, "report_*.md")
        files = sorted(glob.glob(pattern), reverse=True)[:limit]
        
        reports = []
        for f in files:
            basename = os.path.basename(f)
            # report_20260129.md -> 20260129
            date_str = basename.replace("report_", "").replace(".md", "")
            reports.append({
                "date": date_str,
                "filename": basename,
                "size": os.path.getsize(f)
            })
        return reports


# ============================================================
# 便捷函数
# ============================================================

def get_config_service() -> ConfigService:
    """获取配置服务实例"""
    return ConfigService()


def get_analysis_service() -> AnalysisService:
    """获取分析服务单例"""
    return AnalysisService.get_instance()


def get_stock_results_service() -> StockResultsService:
    """获取分析结果服务实例"""
    return StockResultsService()
