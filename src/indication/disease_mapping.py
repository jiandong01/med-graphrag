"""疾病索引映射配置"""

from typing import Dict, Any

def get_disease_mapping() -> Dict[str, Any]:
    """获取疾病索引的映射配置
    
    Returns:
        Dict[str, Any]: 疾病索引映射
    """
    return {
        "settings": {
            "analysis": {
                "analyzer": {
                    "disease_analyzer": {
                        "type": "custom",
                        "tokenizer": "standard",
                        "filter": [
                            "lowercase",
                            "stop",
                            "synonym"
                        ]
                    }
                },
                "filter": {
                    "synonym": {
                        "type": "synonym",
                        "synonyms": []  # 可以从外部文件加载同义词
                    }
                }
            }
        },
        "mappings": {
            "properties": {
                "id": {
                    "type": "keyword"  # 疾病ID，用于唯一标识
                },
                "name": {
                    "type": "text",  # 疾病名称，支持全文搜索
                    "analyzer": "disease_analyzer",
                    "fields": {
                        "raw": {
                            "type": "keyword"  # 用于精确匹配和聚合
                        }
                    }
                },
                "type": {
                    "type": "keyword"  # 实体类型，通常是 "disease"
                },
                "sub_diseases": {  # 子疾病
                    "type": "nested",
                    "properties": {
                        "name": {
                            "type": "text",
                            "analyzer": "disease_analyzer",
                            "fields": {
                                "raw": {
                                    "type": "keyword"
                                }
                            }
                        },
                        "type": {
                            "type": "keyword"
                        },
                        "confidence_score": {
                            "type": "float"
                        }
                    }
                },
                "related_diseases": {  # 相关疾病
                    "type": "nested",
                    "properties": {
                        "name": {
                            "type": "text",
                            "analyzer": "disease_analyzer",
                            "fields": {
                                "raw": {
                                    "type": "keyword"
                                }
                            }
                        },
                        "relationship": {
                            "type": "keyword"  # 关系类型，如 "cause"
                        },
                        "attributes": {
                            "type": "object",  # 额外属性，保持灵活性
                            "enabled": True
                        }
                    }
                },
                "confidence_score": {
                    "type": "float"  # 置信度分数
                },
                "sources": {  # 来源信息
                    "type": "nested",
                    "properties": {
                        "drug_id": {
                            "type": "keyword"  # 药品ID
                        },
                        "extraction_time": {
                            "type": "date"  # 提取时间
                        },
                        "confidence": {
                            "type": "float"  # 该来源的置信度
                        }
                    }
                },
                "first_seen": {
                    "type": "date"  # 首次发现时间
                },
                "last_updated": {
                    "type": "date"  # 最后更新时间
                },
                "mention_count": {
                    "type": "integer"  # 被提及次数
                }
            }
        }
    }
