"""Elasticsearch 映射定义"""

DISEASE_MAPPING = {
    "settings": {
        "analysis": {
            "analyzer": {
                "disease_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": [
                        "lowercase",
                        "stop",
                        "trim"
                    ]
                }
            }
        }
    },
    "mappings": {
        "properties": {
            "id": {
                "type": "keyword"
            },
            "name": {
                "type": "text",
                "analyzer": "disease_analyzer",
                "fields": {
                    "keyword": {
                        "type": "keyword",
                        "ignore_above": 256
                    }
                }
            },
            "type": {
                "type": "keyword"
            },
            "sub_diseases": {
                "type": "nested",
                "properties": {
                    "name": {
                        "type": "text",
                        "analyzer": "disease_analyzer",
                        "fields": {
                            "keyword": {
                                "type": "keyword",
                                "ignore_above": 256
                            }
                        }
                    },
                    "type": {
                        "type": "keyword"
                    },
                    "attributes": {
                        "type": "object",
                        "enabled": True
                    }
                }
            },
            "related_diseases": {
                "type": "nested",
                "properties": {
                    "name": {
                        "type": "text",
                        "analyzer": "disease_analyzer",
                        "fields": {
                            "keyword": {
                                "type": "keyword",
                                "ignore_above": 256
                            }
                        }
                    },
                    "type": {
                        "type": "keyword"
                    },
                    "relationship": {
                        "type": "keyword"
                    },
                    "attributes": {
                        "type": "object",
                        "enabled": True
                    }
                }
            },
            "confidence_score": {
                "type": "float"
            },
            "sources": {
                "type": "nested",
                "properties": {
                    "drug_id": {
                        "type": "keyword"
                    },
                    "extraction_time": {
                        "type": "date"
                    },
                    "confidence": {
                        "type": "float"
                    }
                }
            },
            "first_seen": {
                "type": "date"
            },
            "last_updated": {
                "type": "date"
            },
            "mention_count": {
                "type": "integer"
            }
        }
    }
}
