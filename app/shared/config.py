"""配置管理"""

import os
import yaml
from pathlib import Path
from dotenv import load_dotenv


class Config:
    """统一配置管理"""
    
    @staticmethod
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
    
    @staticmethod
    def load_yaml(config_path: str = "config.yaml") -> dict:
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
    
    @staticmethod
    def ensure_directories(config: dict):
        """确保所需目录存在
        
        Args:
            config: 包含路径配置的字典
        """
        for dir_name in ['output_dir', 'processed_dir', 'failed_dir', 'logs_dir']:
            if dir_name in config.get('paths', {}):
                Path(config['paths'][dir_name]).mkdir(parents=True, exist_ok=True)
