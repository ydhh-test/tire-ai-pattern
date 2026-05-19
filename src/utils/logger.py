# -*- coding: utf-8 -*-

"""
日志模块

提供标准化的日志系统。
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional


# 项目根目录（logger.py 位于 src/utils/ 下，上溯两级即为项目根）
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _ensure_file_handler(logger: logging.Logger, level: int, formatter: logging.Formatter) -> None:
    """确保 logger 拥有文件 handler，写入 .logs/project.log。"""
    _log_dir = _PROJECT_ROOT / ".logs"
    _log_dir.mkdir(parents=True, exist_ok=True)
    _file_handler = logging.FileHandler(str(_log_dir / "project.log"), encoding="utf-8")
    _file_handler.setLevel(level)
    _file_handler.setFormatter(formatter)
    logger.addHandler(_file_handler)


def setup_logger(
    name: str = "giti_tire",
    level: str = "INFO",
    log_file: Optional[str] = None,
    console_output: bool = True
) -> logging.Logger:
    """
    设置并返回一个配置好的日志记录器。

    所有项目日志统一写入 .logs/project.log（文件 handler 等级为 DEBUG，
    保证 debug 级别日志也能落盘），控制台输出等级由 level 参数控制。

    Args:
        name: 日志记录器名称
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 日志文件路径（可选，不影响默认 .logs/project.log）
        console_output: 是否输出到控制台

    Returns:
        配置好的日志记录器
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    # 避免重复添加处理器
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # —— 默认文件 handler：所有日志统一写入 .logs/project.log ——
    _ensure_file_handler(logger, logging.DEBUG, formatter)

    # 显式指定的 log_file（额外输出）
    if log_file:
        log_path = Path(log_file)
        log_dir = log_path.parent
        if log_dir != Path('.') and not log_dir.exists():
            log_dir.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(str(log_path), encoding='utf-8')
        file_handler.setLevel(getattr(logging, level.upper()))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # 控制台处理器
    if console_output:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, level.upper()))
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger


def get_logger(name: str = "giti_tire") -> logging.Logger:
    """
    获取或创建日志记录器。

    Args:
        name: 日志记录器名称

    Returns:
        日志记录器实例
    """
    if not hasattr(logging.Logger, 'manager'):
        return setup_logger(name)

    logger = logging.getLogger(name)
    if not logger.handlers:
        return setup_logger(name)
    return logger


class LoggerMixin:
    """日志记录器混入类，为类提供日志功能。"""

    @property
    def logger(self) -> logging.Logger:
        """获取当前类的日志记录器。"""
        return get_logger(self.__class__.__name__)


# 创建默认日志记录器
default_logger = get_logger("tire-ai-pattern")