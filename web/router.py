# -*- coding: utf-8 -*-
"""
===================================
Web 路由层 - 请求分发
===================================

职责：
1. 解析请求路径
2. 分发到对应的处理器
3. 支持路由注册和扩展
"""

from __future__ import annotations

import logging
from http import HTTPStatus
from typing import Callable, Dict, List, Optional, TYPE_CHECKING, Tuple
from urllib.parse import parse_qs, urlparse

from web.handlers import (
    Response, HtmlResponse, JsonResponse,
    get_page_handler, get_api_handler, get_bot_handler
)
from web.templates import render_error_page

if TYPE_CHECKING:
    from http.server import BaseHTTPRequestHandler

logger = logging.getLogger(__name__)


# ============================================================
# 路由定义
# ============================================================

# 路由处理函数类型: (query_params) -> Response
RouteHandler = Callable[[Dict[str, list]], Response]


class Route:
    """路由定义"""
    
    def __init__(
        self,
        path: str,
        method: str,
        handler: RouteHandler,
        description: str = ""
    ):
        self.path = path
        self.method = method.upper()
        self.handler = handler
        self.description = description


class Router:
    """
    路由管理器
    
    负责：
    1. 注册路由
    2. 匹配请求路径
    3. 分发到处理器
    """
    
    def __init__(self):
        self._routes: Dict[str, Dict[str, Route]] = {}  # {path: {method: Route}}
    
    def register(
        self,
        path: str,
        method: str,
        handler: RouteHandler,
        description: str = ""
    ) -> None:
        """
        注册路由
        
        Args:
            path: 路由路径
            method: HTTP 方法 (GET, POST, etc.)
            handler: 处理函数
            description: 路由描述
        """
        method = method.upper()
        if path not in self._routes:
            self._routes[path] = {}
        
        self._routes[path][method] = Route(path, method, handler, description)
        logger.debug(f"[Router] 注册路由: {method} {path}")
    
    def get(self, path: str, description: str = "") -> Callable:
        """装饰器：注册 GET 路由"""
        def decorator(handler: RouteHandler) -> RouteHandler:
            self.register(path, "GET", handler, description)
            return handler
        return decorator
    
    def post(self, path: str, description: str = "") -> Callable:
        """装饰器：注册 POST 路由"""
        def decorator(handler: RouteHandler) -> RouteHandler:
            self.register(path, "POST", handler, description)
            return handler
        return decorator
    
    def match(self, path: str, method: str) -> Optional[Route]:
        """
        匹配路由
        
        Args:
            path: 请求路径
            method: HTTP 方法
            
        Returns:
            匹配的路由，或 None
        """
        method = method.upper()
        routes_for_path = self._routes.get(path)
        
        if routes_for_path is None:
            return None
        
        return routes_for_path.get(method)
    
    def dispatch(
        self,
        request_handler: 'BaseHTTPRequestHandler',
        method: str
    ) -> None:
        """
        分发请求
        
        Args:
            request_handler: HTTP 请求处理器
            method: HTTP 方法
        """
        # 解析 URL
        parsed = urlparse(request_handler.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        
        # 处理根路径
        if path == "":
            path = "/"
        
        # 匹配路由
        route = self.match(path, method)
        
        if route is None:
            # 404 Not Found
            self._send_not_found(request_handler, path)
            return
        
        try:
            # 调用处理器
            response = route.handler(query)
            response.send(request_handler)
            
        except Exception as e:
            logger.error(f"[Router] 处理请求失败: {method} {path} - {e}")
            self._send_error(request_handler, str(e))
    
    def dispatch_post(
        self,
        request_handler: 'BaseHTTPRequestHandler'
    ) -> None:
        """
        分发 POST 请求（需要读取 body）
        
        Args:
            request_handler: HTTP 请求处理器
        """
        parsed = urlparse(request_handler.path)
        path = parsed.path
        
        # 读取 POST body（保留原始字节用于 Bot Webhook）
        content_length = int(request_handler.headers.get("Content-Length", "0") or "0")
        raw_body_bytes = request_handler.rfile.read(content_length)
        raw_body = raw_body_bytes.decode("utf-8", errors="replace")
        
        # 检查是否是 Bot Webhook 路由
        if path.startswith("/bot/"):
            self._dispatch_bot_webhook(request_handler, path, raw_body_bytes)
            return
        
        # 普通 POST 请求
        form_data = parse_qs(raw_body)
        
        # 匹配路由
        route = self.match(path, "POST")
        
        if route is None:
            self._send_not_found(request_handler, path)
            return
        
        try:
            # 调用处理器（传入 form_data）
            response = route.handler(form_data)
            response.send(request_handler)
            
        except Exception as e:
            logger.error(f"[Router] 处理 POST 请求失败: {path} - {e}")
            self._send_error(request_handler, str(e))
    
    def _dispatch_bot_webhook(
        self,
        request_handler: 'BaseHTTPRequestHandler',
        path: str,
        body: bytes
    ) -> None:
        """
        分发 Bot Webhook 请求
        
        Bot Webhook 需要原始 body 和 headers，与普通路由处理不同。
        
        Args:
            request_handler: HTTP 请求处理器
            path: 请求路径
            body: 原始请求体字节
        """
        # 提取平台名称：/bot/feishu -> feishu
        parts = path.strip('/').split('/')
        if len(parts) < 2:
            self._send_not_found(request_handler, path)
            return
        
        platform = parts[1]
        
        # 获取请求头
        headers = {key: value for key, value in request_handler.headers.items()}
        
        try:
            bot_handler = get_bot_handler()
            response = bot_handler.handle_webhook(platform, {}, headers, body)
            response.send(request_handler)
            
        except Exception as e:
            logger.error(f"[Router] 处理 Bot Webhook 失败: {path} - {e}")
            self._send_error(request_handler, str(e))
    
    def list_routes(self) -> List[Tuple[str, str, str]]:
        """
        列出所有路由
        
        Returns:
            [(method, path, description), ...]
        """
        routes = []
        for path, methods in self._routes.items():
            for method, route in methods.items():
                routes.append((method, path, route.description))
        return sorted(routes, key=lambda x: (x[1], x[0]))
    
    def _send_not_found(
        self,
        request_handler: 'BaseHTTPRequestHandler',
        path: str
    ) -> None:
        """发送 404 响应"""
        body = render_error_page(404, "页面未找到", f"路径 {path} 不存在")
        response = HtmlResponse(body, status=HTTPStatus.NOT_FOUND)
        response.send(request_handler)
    
    def _send_error(
        self,
        request_handler: 'BaseHTTPRequestHandler',
        message: str
    ) -> None:
        """发送 500 响应"""
        body = render_error_page(500, "服务器内部错误", message)
        response = HtmlResponse(body, status=HTTPStatus.INTERNAL_SERVER_ERROR)
        response.send(request_handler)


# ============================================================
# 默认路由注册
# ============================================================

def create_default_router() -> Router:
    """创建并配置默认路由"""
    router = Router()
    
    # 获取处理器
    page_handler = get_page_handler()
    api_handler = get_api_handler()
    
    # === 页面路由 ===
    router.register(
        "/", "GET",
        lambda q: page_handler.handle_index(),
        "配置首页"
    )
    
    router.register(
        "/update", "POST",
        lambda form: page_handler.handle_update(form),
        "更新配置"
    )
    
    # === API 路由 ===
    router.register(
        "/health", "GET",
        lambda q: api_handler.handle_health(),
        "健康检查"
    )
    
    router.register(
        "/analysis", "GET",
        lambda q: api_handler.handle_analysis(q),
        "触发股票分析"
    )
    
    router.register(
        "/tasks", "GET",
        lambda q: api_handler.handle_tasks(q),
        "查询任务列表"
    )
    
    router.register(
        "/task", "GET",
        lambda q: api_handler.handle_task_status(q),
        "查询任务状态"
    )
    
    router.register(
        "/stock_results", "GET",
        lambda q: api_handler.handle_stock_results(),
        "获取今日分析结果"
    )
    
    router.register(
        "/report", "GET",
        lambda q: api_handler.handle_report(q),
        "查看分析报告"
    )
    
    # === Bot Webhook 路由 ===
    # 注意：Bot Webhook 路由在 dispatch_post 中特殊处理
    # 这里只是为了在路由列表中显示
    # 实际请求会被 _dispatch_bot_webhook 方法处理
    
    # 飞书机器人 Webhook
    router.register(
        "/bot/feishu", "POST",
        lambda form: JsonResponse({"error": "Use POST with JSON body"}),
        "飞书机器人 Webhook"
    )
    
    # 钉钉机器人 Webhook
    router.register(
        "/bot/dingtalk", "POST",
        lambda form: JsonResponse({"error": "Use POST with JSON body"}),
        "钉钉机器人 Webhook"
    )
    
    # 企业微信机器人 Webhook（开发中）
    # router.register(
    #     "/bot/wecom", "POST",
    #     lambda form: JsonResponse({"error": "Use POST with JSON body"}),
    #     "企业微信机器人 Webhook"
    # )
    
    # Telegram 机器人 Webhook（开发中）
    # router.register(
    #     "/bot/telegram", "POST",
    #     lambda form: JsonResponse({"error": "Use POST with JSON body"}),
    #     "Telegram 机器人 Webhook"
    # )
    
    return router


# 全局默认路由实例
_default_router: Router | None = None


def get_router() -> Router:
    """获取默认路由实例"""
    global _default_router
    if _default_router is None:
        _default_router = create_default_router()
    return _default_router
