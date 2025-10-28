"""Elasticsearch客户端管理"""

import os
from elasticsearch import Elasticsearch
from dotenv import load_dotenv


def get_es_client() -> Elasticsearch:
    """获取 Elasticsearch 客户端实例
    
    Returns:
        Elasticsearch: ES客户端实例
        
    Raises:
        Exception: 连接ES失败时抛出异常
    """
    load_dotenv()
    
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
        raise Exception(f"Failed to connect to Elasticsearch: {str(e)}")
