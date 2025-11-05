# utils/logger.py

import logging
import sys

def setup_logger(config):
    """
    配置并返回一个logger实例。
    这个logger会同时将日志信息输出到控制台和文件中。
    """
    log_level = config['logging']['level']
    log_filename = config['logging']['filename']

    # 创建一个logger
    logger = logging.getLogger('TradingBotLogger')
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # 如果logger已经有handlers，就不要重复添加了
    if logger.hasHandlers():
        logger.handlers.clear()

    # 创建一个格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 创建一个handler，用于写入日志文件
    file_handler = logging.FileHandler(log_filename, mode='a', encoding='utf-8')
    file_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    file_handler.setFormatter(formatter)

    # 创建一个handler，用于输出到控制台
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    console_handler.setFormatter(formatter)

    # 给logger添加handler
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger