"""日志工具"""

import logging
from pathlib import Path
from datetime import datetime


def setup_logging(name: str, log_dir: str = 'logs', level=logging.INFO):
    """设置日志
    
    Args:
        name: 日志记录器名称
        log_dir: 日志目录路径
        level: 日志级别
        
    Returns:
        logging.Logger: 配置好的日志记录器
    """
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # 配置日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 创建日志文件处理器
    log_file = log_dir / f"{name}.log"
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)
    
    # 配置根日志记录器
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # 防止日志重复
    logger.propagate = False
    
    return logger
