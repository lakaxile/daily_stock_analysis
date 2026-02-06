# -*- coding: utf-8 -*-
"""
===================================
上证全市场扫描器
===================================

功能：
1. 获取上证全部股票列表
2. 技术面预筛选（多头排列+量价健康）
3. 批量AI深度分析
4. S级过滤和微信推送
"""

import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


@dataclass
class ScanResult:
    """扫描结果"""
    code: str
    name: str
    score: int
    level: str  # S/A/B/C
    operation_advice: str
    trend_prediction: str
    current_price: float
    ma5: float
    ma10: float
    ma20: float
    analysis_result: Optional[any] = None  # 完整的 AnalysisResult 对象


class MarketScanner:
    """
    全市场扫描器
    
    流程：
    1. 获取上证股票列表
    2. 技术面预筛选（多头排列）
    3. AI深度分析候选股
    4. 筛选S级推送微信
    """
    
    def __init__(self, max_workers: int = 3, enable_watchlist: bool = True):
        self.max_workers = max_workers
        self._results: List[ScanResult] = []
        self.enable_watchlist = enable_watchlist
        
        # 初始化自选股管理器
        if self.enable_watchlist:
            from src.watchlist import WatchlistManager
            self.watchlist = WatchlistManager()
            logger.info("[Scanner] 自选股管理器已启用")
        else:
            self.watchlist = None
    
    def get_sh_stock_list(self) -> List[str]:
        """
        获取上证全部股票代码
        
        Returns:
            上证股票代码列表（60xxxx, 68xxxx）
        """
        import time
        
        for attempt in range(3):
            try:
                import akshare as ak
                
                logger.info(f"[Scanner] 尝试获取上证股票列表(第{attempt+1}次)...")
                
                try:
                    df = ak.stock_info_a_code_name()
                    sh_stocks = df[df['code'].str.startswith('6')]['code'].tolist()
                except:
                    df = ak.stock_zh_a_spot_em()
                    sh_stocks = df[df['代码'].str.startswith('6')]['代码'].tolist()
                
                logger.info(f"[Scanner] 获取上证股票列表: {len(sh_stocks)} 只")
                return sh_stocks
                
            except Exception as e:
                logger.warning(f"[Scanner] 获取股票列表失败(尝试{attempt+1}/3): {e}")
                if attempt < 2:
                    time.sleep(5)
                    continue
                logger.error(f"[Scanner] 获取股票列表失败，已重试3次")
                return []
        
        return []
    
    def get_sz_stock_list(self) -> List[str]:
        """
        获取深证全部股票代码
        
        Returns:
            深证股票代码列表（00xxxx 主板, 30xxxx 创业板）
        """
        import time
        
        for attempt in range(3):
            try:
                import akshare as ak
                
                logger.info(f"[Scanner] 尝试获取深证股票列表(第{attempt+1}次)...")
                
                try:
                    df = ak.stock_info_a_code_name()
                    # 筛选深证（代码以0或3开头）
                    sz_stocks = df[df['code'].str.match(r'^(0|3)')]['code'].tolist()
                except:
                    df = ak.stock_zh_a_spot_em()
                    sz_stocks = df[df['代码'].str.match(r'^(0|3)')]['代码'].tolist()
                
                logger.info(f"[Scanner] 获取深证股票列表: {len(sz_stocks)} 只")
                return sz_stocks
                
            except Exception as e:
                logger.warning(f"[Scanner] 获取深证股票列表失败(尝试{attempt+1}/3): {e}")
                if attempt < 2:
                    time.sleep(5)
                    continue
                logger.error(f"[Scanner] 获取深证股票列表失败，已重试3次")
                return []
        
        return []
    
    def technical_prefilter(self, stock_list: List[str], batch_size: int = 50) -> List[Dict]:
        """
        技术面预筛选（使用 yfinance 获取数据）
        
        严格筛选条件：
        1. MA5 > MA10 > MA20（多头排列）
        2. MA5/MA20 发散度 > 1%（趋势明确）
        3. 乖离率 < 5%（不追高）
        4. 最近3日至少有2根阳线
        5. 近5日量比 > 0.5（有成交活跃度）
        6. 价格站稳MA5之上
        
        Args:
            stock_list: 股票代码列表
            batch_size: 批量获取大小
            
        Returns:
            符合条件的股票信息列表
        """
        import time
        import yfinance as yf
        import pandas as pd
        
        candidates = []
        total = len(stock_list)
        
        logger.info(f"[Scanner] 开始技术面预筛选 {total} 只股票（yfinance严格模式）...")
        
        processed = 0
        failed = 0
        
        for code in stock_list:
            processed += 1  # 移到循环开始
            
            try:
                # 自动识别市场：6开头=上证(.SS)，0/3开头=深证(.SZ)
                if code.startswith('6'):
                    yf_symbol = f"{code}.SS"
                else:
                    yf_symbol = f"{code}.SZ"
                
                # 获取K线数据
                df_k = None
                try:
                    ticker = yf.Ticker(yf_symbol)
                    df_k = ticker.history(period="3mo")  # 获取3个月数据
                except Exception as e:
                    failed += 1
                    continue
                
                if df_k is None or len(df_k) < 20:
                    failed += 1
                    continue
                
                # 重命名列以适配后续逻辑
                df_k = df_k.rename(columns={
                    'Open': '开盘', 'Close': '收盘', 'Volume': '成交量'
                })
                
                # 计算均线
                df_k['MA5'] = df_k['收盘'].rolling(5).mean()
                df_k['MA10'] = df_k['收盘'].rolling(10).mean()
                df_k['MA20'] = df_k['收盘'].rolling(20).mean()
                
                latest = df_k.iloc[-1]
                ma5 = latest['MA5']
                ma10 = latest['MA10']
                ma20 = latest['MA20']
                close = latest['收盘']
                
                # 检查NaN
                if pd.isna(ma5) or pd.isna(ma10) or pd.isna(ma20):
                    continue
                
                # 计算 RSI (6日)
                delta = df_k['收盘'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=6).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=6).mean()
                rs = gain / loss
                df_k['RSI6'] = 100 - (100 / (1 + rs))
                rsi6 = df_k['RSI6'].iloc[-1]
                
                # ===== 严格筛选条件 (V2) =====
                
                # 条件1: 多头排列 MA5 > MA10 > MA20
                if not (ma5 > ma10 > ma20):
                    continue
                
                # 条件2: MA发散度 > 1%（趋势明确）
                ma_spread = (ma5 - ma20) / ma20 * 100
                if ma_spread < 1:
                    continue
                
                # 条件3: 乖离率 < 6%（稍微放宽一点点，因为加了RSI）
                bias = (close - ma5) / ma5 * 100
                if bias > 6:
                    continue
                
                # 条件4: 价格必须站稳MA5之上
                if close < ma5:
                    continue
                
                # 条件5: 近3日至少有2根阳线
                recent_3 = df_k.tail(3)
                yang_count = sum(recent_3['收盘'] > recent_3['开盘'])
                if yang_count < 2:
                    continue
                
                # 条件6: 量能健康（近5日量比 > 0.6）
                vol_ma5 = df_k['成交量'].tail(5).mean()
                vol_ma20 = df_k['成交量'].tail(20).mean()
                vol_ratio = vol_ma5 / vol_ma20 if vol_ma20 > 0 else 0
                if vol_ratio < 0.6:  # 稍微提高量能要求
                    continue
                
                # 条件7: MA20 趋势向上 (当前MA20 > 前一日MA20)
                if ma20 <= df_k['MA20'].iloc[-2]:
                    continue
                
                # 条件8: RSI 指标过滤 (50 < RSI6 < 85)
                # 50以上是强势区，85以上不仅超买而且往往伴随高风险
                if pd.isna(rsi6) or not (50 < rsi6 < 85):
                    continue
                
                # 通过所有条件，添加到候选列表
                candidates.append({
                    'code': code,
                    'name': code,
                    'price': round(close, 2),
                    'ma5': round(ma5, 2),
                    'ma10': round(ma10, 2),
                    'ma20': round(ma20, 2),
                    'bias': round(bias, 2),
                    'ma_spread': round(ma_spread, 2),
                    'vol_ratio': round(vol_ratio, 2),
                    'rsi6': round(rsi6, 2),
                    'change_pct': round((close - df_k.iloc[-2]['收盘']) / df_k.iloc[-2]['收盘'] * 100, 2) if len(df_k) > 1 else 0
                })
                
            except Exception as e:
                failed += 1
                continue
            
            # 每100只输出一次进度
            if processed % 100 == 0:
                logger.info(f"[Scanner] 预筛进度: {processed}/{total}, 候选: {len(candidates)}, 失败: {failed}")
            
            # 每处理50只休息一下，避免限流
            if processed % 50 == 0:
                time.sleep(0.5)
        
        logger.info(f"[Scanner] 技术面预筛完成: {len(candidates)} 只候选股 (失败: {failed}, 共处理: {processed})")
        return candidates
    
    def batch_analyze(
        self, 
        candidates: List[Dict],
        min_score: int = 80
    ) -> List[ScanResult]:
        """
        批量AI分析
        
        Args:
            candidates: 候选股票列表
            min_score: 最低分数阈值（S级=80）
            
        Returns:
            分析结果列表
        """
        from src.config import get_config
        from src.core.pipeline import StockAnalysisPipeline
        
        config = get_config()
        results = []
        total = len(candidates)
        
        logger.info(f"[Scanner] 开始AI深度分析 {total} 只候选股...")
        
        # 提取股票代码列表
        stock_codes = [c['code'] for c in candidates]
        
        # 创建分析管道
        pipeline = StockAnalysisPipeline(
            config=config,
            max_workers=self.max_workers,
            source_message=None
        )
        
        # 使用 run() 方法批量分析，不发送通知
        analysis_results = pipeline.run(
            stock_codes=stock_codes,
            dry_run=False,
            send_notification=False  # 扫描器自己发通知
        )
        
        # 筛选S级
        for result in analysis_results:
            if result is None:
                continue
                
            score = result.sentiment_score
            
            # 确定级别
            if score >= 80:
                level = "S"
            elif score >= 60:
                level = "A"
            elif score >= 40:
                level = "B"
            else:
                level = "C"
            
            # 只保留达到阈值的
            if score >= min_score:
                scan_result = ScanResult(
                    code=result.code,
                    name=result.name,
                    score=score,
                    level=level,
                    operation_advice=result.operation_advice,
                    trend_prediction=result.trend_prediction,
                    current_price=result.dashboard.get('data_perspective', {}).get('price_position', {}).get('current_price', 0),
                    ma5=result.dashboard.get('data_perspective', {}).get('price_position', {}).get('ma5', 0),
                    ma10=result.dashboard.get('data_perspective', {}).get('price_position', {}).get('ma10', 0),
                    ma20=result.dashboard.get('data_perspective', {}).get('price_position', {}).get('ma20', 0),
                    analysis_result=result  # 保存完整分析结果
                )
                results.append(scan_result)
                logger.info(f"[Scanner] S级发现: {result.code} {result.name} - {score}分")
        
        logger.info(f"[Scanner] AI分析完成，S级股票: {len(results)} 只")
        return results
    
    def notify_s_level(self, results: List[ScanResult]) -> bool:
        """
        推送S级股票到企业微信（包含详细分析报告）
        
        Args:
            results: S级扫描结果
            
        Returns:
            是否发送成功
        """
        if not results:
            logger.info("[Scanner] 无S级股票，跳过推送")
            return True
        
        from src.notification import NotificationService
        
        notifier = NotificationService()
        
        # 1. 先发送概览消息
        overview_lines = [
            "🎯 **全市场扫描 - S级强势股**",
            f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"📊 共发现 **{len(results)}** 只S级股票",
            "",
            "---",
            ""
        ]
        
        for r in results:
            overview_lines.append(f"🟢 **{r.name}({r.code})** | {r.score}分")
            overview_lines.append(f"  · {r.operation_advice} | {r.trend_prediction}")
            overview_lines.append(f"  · 价格: {r.current_price} | MA5: {r.ma5}")
            overview_lines.append("")
        
        overview_lines.append("---")
        overview_lines.append("*详细分析报告将逐个发送*")
        
        overview_msg = "\n".join(overview_lines)
        
        try:
            notifier.send(overview_msg)
            logger.info(f"[Scanner] S级股票概览已推送")
        except Exception as e:
            logger.error(f"[Scanner] 概览推送失败: {e}")
        
        # 2. 为每只S级股票发送详细分析报告
        for r in results:
            try:
                if r.analysis_result and hasattr(r.analysis_result, 'dashboard'):
                    dashboard = r.analysis_result.dashboard
                    
                    # 构建详细报告
                    report_lines = [
                        f"📊 **{r.name}({r.code})** 详细分析",
                        f"评分: {r.score}分 | 级别: {r.level}级",
                        "",
                        "---",
                        ""
                    ]
                    
                    # 核心结论
                    core = dashboard.get('core_conclusion', {})
                    if core:
                        report_lines.append("### 💡 核心结论")
                        report_lines.append(f"**{core.get('signal_type', '')}**")
                        report_lines.append(f"{core.get('one_sentence', '')}")
                        report_lines.append(f"时效性: {core.get('time_sensitivity', '')}")
                        report_lines.append("")
                    
                    # 买入信号
                    buy_signal = dashboard.get('buy_signal', {})
                    if buy_signal:
                        report_lines.append("### 🎯 买入信号")
                        report_lines.append(f"信号强度: {buy_signal.get('signal_strength', '')}/10")
                        report_lines.append(f"买入区间: {buy_signal.get('ideal_buy_range', '')}")
                        report_lines.append(f"目标价: {buy_signal.get('target_price', '')}")
                        report_lines.append(f"止损价: {buy_signal.get('stop_loss', '')}")
                        report_lines.append("")
                    
                    # 六维评估
                    six_dim = dashboard.get('six_dimensional_analysis', {})
                    if six_dim:
                        report_lines.append("### 📈 六维评估")
                        for dim_name, dim_data in six_dim.items():
                            if isinstance(dim_data, dict):
                                score = dim_data.get('score', 'N/A')
                                signal = dim_data.get('signal', '')
                                report_lines.append(f"· {dim_name}: {score}分 | {signal}")
                        report_lines.append("")
                    
                    # 风险提示
                    risk = dashboard.get('risk_warning', {})
                    if risk:
                        report_lines.append("### ⚠️ 风险提示")
                        main_risks = risk.get('main_risks', [])
                        if main_risks:
                            for r_item in main_risks[:3]:
                                report_lines.append(f"· {r_item}")
                        report_lines.append("")
                    
                    report_lines.append("---")
                    report_lines.append("*六维战法分析，仅供参考*")
                    
                    report_msg = "\n".join(report_lines)
                    notifier.send(report_msg)
                    logger.info(f"[Scanner] {r.name}({r.code}) 详细报告已推送")
                    
            except Exception as e:
                logger.error(f"[Scanner] {r.code} 详细报告推送失败: {e}")
        
        return True

    def validate_yesterday_watchlist(self, min_score: int = 80) -> List[Dict]:
        """
        验证昨日自选股是否仍满足买入条件
        
        Args:
            min_score: 最低分数阈值
            
        Returns:
            被移除的股票列表 [{"code": ..., "name": ..., "reason": ...}]
        """
        if not self.enable_watchlist:
            return []
        
        yesterday_stocks = self.watchlist.get_yesterday_stocks()
        if not yesterday_stocks:
            logger.info("[Scanner] 昨日自选股为空，无需验证")
            return []
        
        logger.info(f"[Scanner] 开始验证昨日自选股: 共 {len(yesterday_stocks)} 只")
        
        removed_stocks = []
        
        # 导入分析器
        from src.analyzer import GeminiAnalyzer
        analyzer = GeminiAnalyzer()
        
        for i, stock in enumerate(yesterday_stocks):
            logger.info(f"[Scanner] 验证进度: {i+1}/{len(yesterday_stocks)} - {stock.name}({stock.code})")
            
            try:
                # 重新分析
                suffix = ".SS" if stock.code.startswith('6') else ".SZ"
                result = analyzer.analyze(stock.code + suffix)
                
                # 检查是否仍满足条件
                if result.sentiment_score < min_score:
                    reason = f"评分下降至 {result.sentiment_score} 分 (原{stock.score}分)"
                    removed_stocks.append({
                        "code": stock.code,
                        "name": stock.name,
                        "reason": reason,
                        "original_score": stock.score,
                        "current_score": result.sentiment_score
                    })
                    self.watchlist.update_stock_status(
                        stock.code,
                        stock.added_date,
                        "removed",
                        reason
                    )
                    logger.info(f"[Scanner] ❌ {stock.name}({stock.code}) 不再满足条件: {reason}")
                    
                elif result.operation_advice not in ["买入", "加仓", "持有"]:
                    reason = f"操作建议变为 {result.operation_advice}"
                    removed_stocks.append({
                        "code": stock.code,
                        "name": stock.name,
                        "reason": reason,
                        "original_score": stock.score,
                        "current_score": result.sentiment_score
                    })
                    self.watchlist.update_stock_status(
                        stock.code,
                        stock.added_date,
                        "removed",
                        reason
                    )
                    logger.info(f"[Scanner] ❌ {stock.name}({stock.code}) 不再满足条件: {reason}")
                    
                else:
                    logger.info(f"[Scanner] ✅ {stock.name}({stock.code}) 仍满足条件 (评分: {result.sentiment_score})")
                    
            except Exception as e:
                logger.error(f"[Scanner] 验证 {stock.code} 失败: {e}")
                continue
        
        return removed_stocks

    def notify_with_watchlist_update(self, new_results: List[ScanResult], removed_stocks: List[Dict]):
        """
        发送包含自选股更新的通知
        
        Args:
            new_results: 新发现的S级股票
            removed_stocks: 被移除的股票列表
        """
        from src.notification import NotificationService
        notifier = NotificationService()
        
        # 构建综合报告
        report_lines = [
            "🎯 **全市场扫描 - 自选股更新**",
            f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "---",
            ""
        ]
        
        # 1. 昨日股票验证结果
        if removed_stocks:
            report_lines.append("### ⚠️ 移除清单")
            report_lines.append(f"昨日自选股验证: **{len(removed_stocks)} 只**不再满足条件")
            report_lines.append("")
            for stock in removed_stocks[:10]:  # 最多显示10只
                report_lines.append(f"❌ **{stock['name']}({stock['code']})**")
                report_lines.append(f"   原评分: {stock['original_score']} → 当前: {stock['current_score']}")
                report_lines.append(f"   移除原因: {stock['reason']}")
                report_lines.append("")
            if len(removed_stocks) > 10:
                report_lines.append(f"... 及其他 {len(removed_stocks) - 10} 只")
            report_lines.append("---")
            report_lines.append("")
        else:
            if self.enable_watchlist:
                report_lines.append("✅ 昨日自选股全部满足条件")
                report_lines.append("")
                report_lines.append("---")
                report_lines.append("")
        
        # 2. 今日新增S级股票
        if new_results:
            report_lines.append("### 🟢 今日新增")
            report_lines.append(f"共发现 **{len(new_results)}** 只S级股票")
            report_lines.append("")
            for r in new_results[:10]:
                report_lines.append(f"🟢 **{r.name}({r.code})** | {r.score}分")
                report_lines.append(f"  · {r.operation_advice} | {r.trend_prediction}")
                if r.current_price:
                    report_lines.append(f"  · 价格: {r.current_price}")
                report_lines.append("")
            if len(new_results) > 10:
                report_lines.append(f"... 及其他 {len(new_results) - 10} 只")
            report_lines.append("")
            report_lines.append("---")
            report_lines.append("*详细分析报告将逐个发送*")
        else:
            report_lines.append("### 📊 今日扫描")
            report_lines.append("暂无新增S级股票")
        
        # 发送综合报告
        report_msg = "\n".join(report_lines)
        try:
            notifier.send(report_msg)
            logger.info("[Scanner] 自选股更新报告已推送")
        except Exception as e:
            logger.error(f"[Scanner] 更新报告推送失败: {e}")
        
        # 发送新股详细报告（复用原有逻辑）
        if new_results:
            self.notify_s_level(new_results)

    

    def scan(self, min_score: int = 80) -> List[ScanResult]:
        """
        执行全市场扫描
        
        Args:
            min_score: 最低分数阈值（默认80=S级）
            
        Returns:
            扫描结果列表
        """
        logger.info("=" * 60)
        logger.info("[Scanner] 开始上证全市场扫描")
        logger.info("=" * 60)
        
        start_time = datetime.now()
        
        # 1. 获取股票列表
        stock_list = self.get_sh_stock_list()
        if not stock_list:
            logger.error("[Scanner] 获取股票列表失败，终止扫描")
            return []
        
        # 2. 技术面预筛
        candidates = self.technical_prefilter(stock_list)
        if not candidates:
            logger.info("[Scanner] 无符合条件的候选股，终止扫描")
            return []
        
        # 3. AI深度分析
        results = self.batch_analyze(candidates, min_score=min_score)
        
        # 4. 推送S级
        self.notify_s_level(results)
        
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"[Scanner] 扫描完成，耗时 {elapsed:.1f} 秒")
        logger.info(f"[Scanner] 结果: {len(stock_list)} 只股票 → {len(candidates)} 候选 → {len(results)} 只S级")
        
        self._results = results
        return results

    def scan_oversold_support(self, min_score: int = 80) -> List[ScanResult]:
        """
        超跌反弹扫描（大跌 + 充分换手 + 底部支撑）
        
        筛选条件：
        1. 深度下跌：距离60日高点回撤 > 25%
        2. 充分换手：下跌以来区间换手率 > 80% (需要获取流通股本)
        3. 底部支撑：
           - RSI(6) < 35 (超卖) OR
           - 出现长下影线 OR
           - 量能温和放大 (今日量比 > 1.2)
        
        Args:
            min_score: 最低分数阈值
            
        Returns:
            扫描结果列表
        """
        logger.info("=" * 60)
        logger.info("[Scanner] 开始超跌反弹机会扫描")
        logger.info("=" * 60)
        
        import yfinance as yf
        import akshare as ak
        import pandas as pd
        import time
        
        start_time = datetime.now()
        
        # 1. 获取全市场股票及流通股本信息
        logger.info("[Scanner] 获取全市场实时行情及股本数据...")
        float_shares_map = {}
        has_float_data = False
        
        # 尝试获取流通股本数据（带重试）
        for attempt in range(3):
            try:
                # 使用 akshare 获取实时行情，包含 '流通市值' 和 '最新价'
                df_spot = ak.stock_zh_a_spot_em()
                
                # 建立映射: code -> float_shares (股)
                for _, row in df_spot.iterrows():
                    try:
                        code = str(row['代码'])
                        price = float(row['最新价'])
                        mkt_cap_float = float(row['流通市值']) # 单位：元
                        if price > 0:
                            float_shares_map[code] = mkt_cap_float / price
                    except:
                        continue
                
                has_float_data = True
                logger.info(f"[Scanner] 成功获取股本数据，共 {len(float_shares_map)} 条")
                break
            except Exception as e:
                logger.warning(f"[Scanner] 获取股本数据失败(尝试{attempt+1}/3): {e}")
                time.sleep(3)
        
        stock_list = []
        if has_float_data:
            stock_list = list(float_shares_map.keys())
            stock_list = [c for c in stock_list if c.startswith(('60', '00', '30'))]
        else:
            logger.warning("[Scanner] ⚠️ 无法获取流通股本数据，将跳过'换手率'筛选，仅根据'回撤'和'底部信号'筛选")
            # 降级：分别获取沪深列表
            sh_list = self.get_sh_stock_list()
            sz_list = self.get_sz_stock_list()
            stock_list = sh_list + sz_list
            logger.info(f"[Scanner] 已降级模式获取股票列表: {len(stock_list)} 只")

        if not stock_list:
            logger.error("[Scanner] 无法获取股票列表，终止扫描")
            return []

        candidates = []
        processed = 0
        failed = 0
        
        logger.info(f"[Scanner] 开始技术面筛选 (条件: 回撤>25% + {'换手>80% + ' if has_float_data else ''}底部信号)...")
        
        # 遍历股票
        for code in stock_list:
            processed += 1
            
            try:
                # 识别市场并获取K线
                if code.startswith('6'):
                    yf_symbol = f"{code}.SS"
                else:
                    yf_symbol = f"{code}.SZ"
                
                # 获取历史数据
                try:
                    ticker = yf.Ticker(yf_symbol)
                    df_k = ticker.history(period="3mo")
                except:
                    failed += 1
                    continue
                
                if df_k is None or len(df_k) < 60:
                    failed += 1
                    continue
                
                # 重命名
                df_k = df_k.rename(columns={'Open': '开盘', 'Close': '收盘', 'High': '最高', 'Low': '最低', 'Volume': '成交量'})
                
                close = df_k['收盘'].iloc[-1]
                open_p = df_k['开盘'].iloc[-1]
                low = df_k['最低'].iloc[-1]
                high = df_k['最高'].iloc[-1]
                
                # === 条件1: 深度下跌 ===
                # 计算60日最高点
                high_60 = df_k['最高'].tail(60).max()
                if high_60 == 0: continue
                
                drawdown = (high_60 - close) / high_60
                
                if drawdown < 0.25:  # 回撤不足25%，跳过
                    continue
                    
                # === 条件2: 充分换手 (仅当有股本数据时) ===
                turnover_rate = 0
                if has_float_data:
                    # 找到高点所在的日期索引
                    high_idx = df_k['最高'].tail(60).idxmax()
                    # 计算从高点到现在的累计成交量
                    df_decline = df_k.loc[high_idx:]
                    total_vol = df_decline['成交量'].sum() # 单位：股
                    
                    float_shares = float_shares_map.get(code, 0)
                    if float_shares == 0:
                        turnover_rate = 0
                    else:
                        turnover_rate = (total_vol / float_shares) * 100
                    
                    if turnover_rate < 80:  # 下跌过程换手率不足80%
                        continue
                
                # === 条件3: 底部支撑信号 ===
                has_support = False
                support_reasons = []
                
                # 3.1 RSI 超卖
                delta = df_k['收盘'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=6).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=6).mean()
                rs = gain / loss
                rsi6 = 100 - (100 / (1 + rs))
                current_rsi = rsi6.iloc[-1]
                
                if current_rsi < 35:
                    has_support = True
                    support_reasons.append(f"RSI超卖({current_rsi:.1f})")
                
                # 3.2 长下影线 (下影线长度 > 实体长度 * 1.5 且 下影线 > 股价的1.5%)
                body_size = abs(close - open_p)
                lower_shadow = min(close, open_p) - low
                if lower_shadow > body_size * 1.5 and lower_shadow > close * 0.015:
                    has_support = True
                    support_reasons.append("长下影线")
                
                # 3.3 量能异动 (量比 > 1.5)
                vol_ma5 = df_k['成交量'].tail(5).mean()
                if vol_ma5 > 0:
                    vol_ratio = df_k['成交量'].iloc[-1] / vol_ma5
                    if vol_ratio > 1.5:
                        has_support = True
                        support_reasons.append(f"放量(量比{vol_ratio:.1f})")
                
                # 3.4 连跌后的阳线 (之前主要跌，今天阳)
                recent_5 = df_k.tail(5)
                # 如果前4天跌了至少3天，且今天是阳线
                drops = sum(recent_5['收盘'].diff() < 0)
                if drops >= 3 and close > open_p:
                    has_support = True
                    support_reasons.append("连跌后红盘")

                if not has_support:
                    continue
                
                # 满足所有条件
                candidates.append({
                    'code': code,
                    'name': code, # 暂时只存code
                    'price': round(close, 2),
                    'drawdown': round(drawdown * 100, 2),
                    'turnover_rate': round(turnover_rate, 2),
                    'support_reason': ",".join(support_reasons)
                })
                
            except Exception as e:
                failed += 1
                continue
            
            if processed % 100 == 0:
                logger.info(f"[Scanner] 扫描进度: {processed}/{len(stock_list)}, 候选: {len(candidates)}")
                
            # 限流
            if processed % 100 == 0:
                time.sleep(0.2)
        
        logger.info(f"[Scanner] 超跌扫描完成: {len(candidates)} 只候选股 (共{processed}, 失败{failed})")
        
        # 3. AI深度分析 (复用 batch_analyze)
        if not candidates:
            return []
            
        results = self.batch_analyze(candidates, min_score=min_score)
        
        # 4. 推送S级 (复用)
        self.notify_s_level(results)
        
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"[Scanner] 扫描全部完成，耗时 {elapsed:.1f} 秒")
        
        self._results = results
        return results
    
    def scan_sz(self, min_score: int = 80) -> List[ScanResult]:
        """
        执行深证全市场扫描
        
        Args:
            min_score: 最低分数阈值（默认80=S级）
            
        Returns:
            扫描结果列表
        """
        logger.info("=" * 60)
        logger.info("[Scanner] 开始深证全市场扫描")
        logger.info("=" * 60)
        
        start_time = datetime.now()
        
        # 1. 获取深圳股票列表
        stock_list = self.get_sz_stock_list()
        if not stock_list:
            logger.error("[Scanner] 获取深证股票列表失败，终止扫描")
            return []
        
        # 2. 技术面预筛
        candidates = self.technical_prefilter(stock_list)
        if not candidates:
            logger.info("[Scanner] 无符合条件的候选股，终止扫描")
            return []
        
        # 3. AI深度分析
        results = self.batch_analyze(candidates, min_score=min_score)
        
        # 4. 推送S级
        self.notify_s_level(results)
        
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"[Scanner] 深证扫描完成，耗时 {elapsed:.1f} 秒")
        logger.info(f"[Scanner] 结果: {len(stock_list)} 只股票 → {len(candidates)} 候选 → {len(results)} 只S级")
        
        self._results = results
        return results

    def scan_all(self, min_score: int = 80, validate_watchlist: bool = True) -> List[ScanResult]:
        """
        执行全市场（沪深）扫描
        
        Args:
            min_score: 最低分数阈值
            validate_watchlist: 是否验证昨日自选股
            
        Returns:
            扫描结果列表
        """
        logger.info("=" * 60)
        logger.info("[Scanner] 开始全市场（沪+深）扫描 - 六维真强势股战法")
        logger.info("=" * 60)
        
        start_time = datetime.now()
        removed_stocks = []
        
        # 0. 验证昨日自选股（盘后优先执行）
        if self.enable_watchlist and validate_watchlist:
            logger.info("[Scanner] ========== 开始验证昨日自选股 ==========")
            removed_stocks = self.validate_yesterday_watchlist(min_score)
            logger.info(f"[Scanner] 昨日自选股验证完成: 共移除 {len(removed_stocks)} 只")
        
        # 1. 获取所有股票列表
        sh_list = self.get_sh_stock_list()
        sz_list = self.get_sz_stock_list()
        
        if not sh_list and not sz_list:
            logger.error("[Scanner] 获取股票列表失败，终止扫描")
            return []
            
        full_list = sh_list + sz_list
        logger.info(f"[Scanner] 获取到股票列表: 沪市 {len(sh_list)} + 深市 {len(sz_list)} = 总计 {len(full_list)} 只")
        
        # 2. 技术面预筛
        # 注意: technical_prefilter 内部会自动根据代码前缀识别 .SS / .SZ
        candidates = self.technical_prefilter(full_list)
        if not candidates:
            logger.info("[Scanner] 无符合条件的候选股，终止扫描")
            return []
        
        # 3. AI深度分析
        results = self.batch_analyze(candidates, min_score=min_score)
        
        # 4. 保存到今日自选股池
        if self.enable_watchlist and results:
            today = datetime.now().strftime('%Y-%m-%d')
            added = self.watchlist.add_stocks(today, results)
            logger.info(f"[Scanner] 今日S级股票已保存到自选股池: {added} 只")
        
        # 5. 推送S级（包含自选股更新）
        self.notify_with_watchlist_update(results, removed_stocks)
        
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"[Scanner] 全市场扫描完成，耗时 {elapsed:.1f} 秒")
        logger.info(f"[Scanner] 结果: {len(full_list)} 只股票 → {len(candidates)} 候选 → {len(results)} 只S级")
        
        self._results = results
        return results


def run_market_scan(min_score: int = 80) -> List[ScanResult]:
    """
    便捷函数：执行上证全市场扫描
    
    Args:
        min_score: 最低分数阈值
        
    Returns:
        扫描结果
    """
    scanner = MarketScanner(max_workers=3)
    return scanner.scan(min_score=min_score)


def run_sz_market_scan(min_score: int = 80) -> List[ScanResult]:
    """
    便捷函数：执行深证全市场扫描
    
    Args:
        min_score: 最低分数阈值
        
    Returns:
        扫描结果
    """
    scanner = MarketScanner(max_workers=3)
    return scanner.scan_sz(min_score=min_score)


def run_oversold_scan(min_score: int = 80) -> List[ScanResult]:
    """
    便捷函数：执行超跌反弹机会扫描
    
    Args:
        min_score: 最低分数阈值
        
    Returns:
        扫描结果
    """
    scanner = MarketScanner(max_workers=3)
    return scanner.scan_oversold_support(min_score=min_score)


def run_all_market_scan(min_score: int = 80) -> List[ScanResult]:
    """
    便捷函数：执行全市场（沪深）扫描
    
    Args:
        min_score: 最低分数阈值
        
    Returns:
        扫描结果
    """
    scanner = MarketScanner(max_workers=3)
    return scanner.scan_all(min_score=min_score)

