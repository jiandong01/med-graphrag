# utils.py
import yaml
from pathlib import Path
import logging
from dotenv import load_dotenv
import os
from elasticsearch import Elasticsearch

def load_env():
    """加载环境变量"""
    load_dotenv()
    
    # 验证必要的环境变量是否存在
    required_vars = [
        'HF_API_KEY',
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

def get_db_configs():
    """获取数据库配置"""
    return {
        'postgresql': {
            'dbname': os.getenv('POSTGRES_DB'),
            'user': os.getenv('POSTGRES_USER'),
            'password': os.getenv('POSTGRES_PASSWORD'),
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': int(os.getenv('POSTGRES_PORT', 5432))
        },
        'neo4j': {
            'uri': os.getenv('NEO4J_URI'),
            'auth': (os.getenv('NEO4J_USER'), os.getenv('NEO4J_PASSWORD'))
        }
    }

def load_config(config_path: str = "config.yaml") -> dict:
    """加载配置文件"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def setup_logging(name: str, config: dict) -> logging.Logger:
    """设置日志"""
    log_dir = Path(config['paths']['logs_dir'])
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / f'{name}.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(name)

def ensure_directories(config: dict):
    """确保所需目录存在"""
    for dir_name in ['output_dir', 'processed_dir', 'failed_dir', 'logs_dir']:
        Path(config['paths'][dir_name]).mkdir(parents=True, exist_ok=True)

def get_elastic_client() -> Elasticsearch:
    """获取 Elasticsearch 客户端实例"""
    load_dotenv()
    return Elasticsearch(
        hosts=['http://localhost:9200'],
        basic_auth=('elastic', os.getenv('ELASTIC_PASSWORD', 'changeme'))
    )

def setup_logging_v2(name: str, log_dir: str = 'logs'):
    """设置日志"""
    import logging
    from pathlib import Path
    from datetime import datetime
    
    # 创建日志目录
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # 配置日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 创建日志文件处理器
    log_file = log_dir / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    
    # 创建错误日志文件处理器
    error_file = log_dir / f"{name}_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    error_handler = logging.FileHandler(error_file)
    error_handler.setFormatter(formatter)
    error_handler.setLevel(logging.ERROR)
    
    return file_handler, error_handler