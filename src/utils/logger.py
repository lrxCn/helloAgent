"""日志模块 — 提供统一的日志配置、过期清理和函数装饰器。

工业标准做法：
1. 使用 Python 内置 logging 模块（不要用 print）
2. 每个模块用 logging.getLogger(__name__) 获取自己的 logger
3. 在入口处统一配置 handler（控制台 + 文件）
4. 用装饰器自动记录函数的进入、退出和耗时
"""

import functools
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path

from config.settings import LOG_DIR, LOG_RETENTION_DAYS


def _cleanup_expired_logs():
    """删除过期的日志文件。"""
    if not LOG_DIR.exists():
        return

    cutoff = datetime.now() - timedelta(days=LOG_RETENTION_DAYS)
    for log_file in LOG_DIR.glob("*.log"):
        # 从文件名解析日期，格式：2026-04-23.log
        try:
            file_date = datetime.strptime(log_file.stem, "%Y-%m-%d")
            if file_date < cutoff:
                log_file.unlink()
                print(f"🗑️  已清理过期日志: {log_file.name}")
        except ValueError:
            # 文件名不符合日期格式，跳过
            continue


def setup_logging(name: str = "helloagent") -> logging.Logger:
    """配置并返回 logger。

    首次调用时会：
    1. 清理过期日志文件
    2. 创建日志目录
    3. 配置控制台和文件两个 handler

    Args:
        name: logger 名称，通常传 __name__。

    Returns:
        配置好的 Logger 实例。
    """
    logger = logging.getLogger()  # 根 logger，所有子 logger 自动继承

    # 避免重复添加 handler
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # ─── 清理过期日志 ───
    _cleanup_expired_logs()

    # ─── 确保日志目录存在 ───
    LOG_DIR.mkdir(exist_ok=True)

    # ─── 控制台 Handler（INFO 级别，简洁格式）───
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    ))

    # ─── 文件 Handler（DEBUG 级别，详细格式，按天一个文件）───
    today = datetime.now().strftime("%Y-%m-%d")
    file_handler = logging.FileHandler(
        LOG_DIR / f"{today}.log",
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    ))

    logger.addHandler(console)
    logger.addHandler(file_handler)

    return logger


def log_function(func=None, *, logger_name: str = None):
    """装饰器：自动记录函数的进入、退出和耗时。

    用法：
        @log_function
        def my_func():
            ...

        @log_function(logger_name="custom")
        def my_func():
            ...
    """
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            log = logging.getLogger(logger_name or fn.__module__)
            log.info(f"▶ {fn.__name__} 开始")
            start = time.time()
            try:
                result = fn(*args, **kwargs)
                elapsed = time.time() - start
                log.info(f"✔ {fn.__name__} 完成 ({elapsed:.2f}s)")
                return result
            except Exception as e:
                elapsed = time.time() - start
                log.error(f"✘ {fn.__name__} 失败 ({elapsed:.2f}s): {e}")
                raise
        return wrapper

    # 支持 @log_function 和 @log_function(...) 两种写法
    if func is not None:
        return decorator(func)
    return decorator
