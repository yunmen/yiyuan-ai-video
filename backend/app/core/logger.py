# -*- coding: utf-8 -*-
'''
@文件    :logger.py
@说明    :日志处理器
@时间    :2025/08/10 03:54:58
@作者    :睿
@版本    :1.0
'''
from app.core.plugin import logger
from app.core.plugin import ctx
from app.utils.commonFunc import get_network_interfaces
from app.settings import config


def x_requests_id(record):
    record['extra']['x_requests_id'] = f"{ctx.get('stack') or '918e3662-85ed-42bc-8ca4-be1b172552dd'}"
    return record


async def init_logger_config():
    logger.add(patcher=x_requests_id)
    logger.info("初始化日志完成...")


async def close_logger_config():
    logger.info("关闭日志完成...")
    logger.remove()


async def print_welcome_banner():
    """使用 loguru 打印精美的欢迎横幅"""
    

    port = config.SERVER_PORT
    interfaces = get_network_interfaces()
    
    separator = "=" * 68
    
    # 收集所有非回环IP用于访问链接
    all_ips = []
    for ips in interfaces.values():
        for ip in ips:
            if not ip.startswith('127.'):
                all_ips.append(ip)
    all_ips = sorted(set(all_ips)) if all_ips else ["127.0.0.1"]
    
    local_urls = [f"http://localhost:{port}", f"http://127.0.0.1:{port}"]
    network_urls = [f"http://{ip}:{port}" for ip in all_ips if not ip.startswith('127.')]
    
    # 定义颜色
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BLUE = "\033[94m"
    WHITE = "\033[97m"
    DIM = "\033[90m"
    RESET = "\033[0m"
    BOLD = "\033[1m"
    # 主标题
    title = (
        f"{GREEN}{BOLD}╔═══════════════════════════════════════════════════════════════╗{RESET}",
        f"{GREEN}║{RESET}  {YELLOW}🚀{RESET}  {CYAN}My Awesome API{CYAN}{' ' * 43}{GREEN}║{RESET}",
        f"{GREEN}{BOLD}╠═══════════════════════════════════════════════════════════════╣{RESET}"
    )
    for t in title:
        logger.info(t)
    # 基本信息
    logger.info(f"{BLUE}🌐 监听端口:{RESET}  {WHITE}{port}{RESET}")
    logger.info(f"{BLUE}📍 本地访问:{RESET}  {WHITE}{', '.join(local_urls)}{RESET}")
    logger.info(f"{BLUE}📡 局域网访问:{RESET}  {WHITE}{', '.join(network_urls)}{RESET}")
    logger.info(f"{BLUE}📚 Swagger文档:{RESET}   {CYAN}http://localhost:{port}/docs{RESET}")
    logger.info(f"{BLUE}🔧 ReDoc文档:{RESET}  {CYAN}http://localhost:{port}/redoc{RESET}")
    logger.info(f"{BLUE}🔧 自定义文档(推荐):{RESET}  {CYAN}http://localhost:{port}/ljdoc{RESET}")
    # 网络接口详情
    logger.info(f"{GREEN}{BOLD}╟───────────────────────────────────────────────────────────────╢{RESET}")
    # 底部
    footer = (
        f"{GREEN}{BOLD}╚═══════════════════════════════════════════════════════════════╝{RESET}",
        f"{DIM}💡 提示: 按 Ctrl+C 停止服务{RESET}"
    )
    for f in footer:
        logger.info(f)
    logger.info(separator)
