# utils.py
import yaml
from pathlib import Path
import logging
from dotenv import load_dotenv
import os
from elasticsearch import Elasticsearch
from datetime import datetime

def load_env():
    """加载环境变量"""
    load_dotenv()
    
    # 验证必要的环境变量是否存在
    required_vars = [
        'DEEPSEEK_API_KEY',
        'ELASTIC_PASSWORD',
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

def get_elastic_client() -> Elasticsearch:
    """获取 Elasticsearch 客户端实例
    
    Returns:
        Elasticsearch: ES客户端实例
        
    Raises:
        Exception: 连接ES失败时抛出异常
    """
    load_env()
    try:
        return Elasticsearch(
            hosts=[os.getenv('ES_HOST', 'http://localhost:9200')],
            basic_auth=(
                os.getenv('ES_USERNAME', 'elastic'),
                os.getenv('ELASTIC_PASSWORD', 'elastic')
            ),
            request_timeout=30,
            retry_on_timeout=True,
            max_retries=3
        )
    except Exception as e:
        logging.error(f"Failed to connect to Elasticsearch: {str(e)}")
        raise

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
    log_file = log_dir / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)
    
    # 创建错误日志文件处理器
    error_file = log_dir / f"{name}_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    error_handler = logging.FileHandler(error_file, encoding='utf-8')
    error_handler.setFormatter(formatter)
    error_handler.setLevel(logging.ERROR)
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)
    
    # 配置根日志记录器
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(file_handler)
    logger.addHandler(error_handler)
    logger.addHandler(console_handler)
    
    # 防止日志重复
    logger.propagate = False
    
    return logger

def load_config(config_path: str = "config.yaml") -> dict:
    """加载配置文件
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        dict: 配置信息字典
        
    Raises:
        FileNotFoundError: 配置文件不存在时抛出
        yaml.YAMLError: YAML解析错误时抛出
    """
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Error parsing YAML file: {str(e)}")

def ensure_directories(config: dict):
    """确保所需目录存在
    
    Args:
        config: 包含路径配置的字典
    """
    for dir_name in ['output_dir', 'processed_dir', 'failed_dir', 'logs_dir']:
        if dir_name in config.get('paths', {}):
            Path(config['paths'][dir_name]).mkdir(parents=True, exist_ok=True)
        else:
            logging.warning(f"Directory '{dir_name}' not found in config paths")
