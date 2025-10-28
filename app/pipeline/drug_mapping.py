"""
定义Elasticsearch的索引映射
"""

DRUG_INDEX_MAPPING = {
    "settings": {
        "analysis": {
            "analyzer": {
                "drug_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": [
                        "lowercase",
                        "stop",
                        "trim"
                    ]
                }
            }
        },
        "number_of_shards": 1,
        "number_of_replicas": 1
    },
    "mappings": {
        "properties": {
            "id": {
                "type": "keyword"
            },
            "name": {
                "type": "text",
                "analyzer": "drug_analyzer",
                "fields": {
                    "keyword": {
                        "type": "keyword",
                        "ignore_above": 256
                    }
                }
            },
            "spec": {
                "type": "text",
                "analyzer": "drug_analyzer"
            },
            "create_time": {
                "type": "date",
                "format": "yyyy-MM-dd||yyyyMMdd||yyyy/MM/dd||yyyy-MM-dd HH:mm:ss||epoch_millis"
            },
            "categories": {
                "type": "keyword"
            },
            "category_hierarchy": {
                "type": "nested",
                "properties": {
                    "category": {
                        "type": "keyword"
                    },
                    "category_id": {
                        "type": "keyword"
                    },
                    "parent_id": {
                        "type": "keyword"
                    }
                }
            },
            "components": {
                "type": "text",
                "analyzer": "drug_analyzer",
                "fields": {
                    "keyword": {
                        "type": "keyword",
                        "ignore_above": 256
                    }
                }
            },
            "indications": {
                "type": "text",
                "analyzer": "drug_analyzer"
            },
            "contraindications": {
                "type": "text",
                "analyzer": "drug_analyzer"
            },
            "adverse_reactions": {
                "type": "text",
                "analyzer": "drug_analyzer"
            },
            "precautions": {
                "type": "text",
                "analyzer": "drug_analyzer"
            },
            "interactions": {
                "type": "text",
                "analyzer": "drug_analyzer"
            },
            "usage": {
                "type": "text",
                "analyzer": "drug_analyzer"
            },
            "approval_number": {
                "type": "keyword"
            },
            "details": {
                "type": "nested",
                "properties": {
                    "tag": {
                        "type": "keyword"
                    },
                    "content": {
                        "type": "text",
                        "analyzer": "drug_analyzer"
                    }
                }
            }
        }
    }
}
