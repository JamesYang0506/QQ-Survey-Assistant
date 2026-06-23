"""
日志工具模块 - 提供统一的日志记录功能
日志输出到文件和控制台，支持不同级别
"""
import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime


def setup_logger(
    name: str = "QQSurveyAssistant",
    log_dir: str = None,
    level: int = logging.INFO
) -> logging.Logger:
    """
    配置并返回一个logger实例。

    Args:
        name: logger名称
        log_dir: 日志文件目录，默认为 %APPDATA%/QQSurveyAssistant/logs/
        level: 日志级别

    Returns:
        配置好的Logger实例
    """
    if log_dir is None:
        appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
        log_dir = os.path.join(appdata, "QQSurveyAssistant", "logs")

    os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 避免重复添加handler
    if logger.handlers:
        return logger

    # 文件Handler - 按日期命名，自动轮转（最大5MB，保留5个备份）
    log_file = os.path.join(log_dir, f"{datetime.now().strftime('%Y-%m-%d')}.log")
    file_handler = RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(level)
    file_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # 控制台Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_formatter = logging.Formatter(
        "[%(levelname)s] %(name)s - %(message)s"
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    return logger


# 默认全局logger
_logger = None


def get_logger() -> logging.Logger:
    """获取全局默认logger实例"""
    global _logger
    if _logger is None:
        _logger = setup_logger()
    return _logger
