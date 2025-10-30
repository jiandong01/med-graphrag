"""知识增强模块"""

import logging
from typing import Dict, List, Any
from elasticsearch import Elasticsearch, NotFoundError
from app.shared import get_es_client
from .models import Case, EnhancedCase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KnowledgeEnhancer:
    def __init__(self, es: Elasticsearch = None):
        self.es = es or get_es_client()
        self.drugs_index = 'drugs'
        self.diseases_index = 'diseases'
        self.clinical_guidelines_index = 'clinical_guidelines' # TODO
        self.expert_consensus_index = 'expert_consensus' # TODO
        self.research_papers_index = 'research_papers' # TODO

    def enhance_case(self, case: Case) -> EnhancedCase:
        """增强病例信息"""
        enhanced_case = EnhancedCase(case)
        
        # 获取药品信息
        if case.recognized_entities.drugs:
            drug = case.recognized_entities.drugs[0]
            if drug.matches:
                drug_info = self.get_drug_by_id(drug.matches[0].id)
                self._update_drug_info(enhanced_case.drug, drug_info)
        
        # 获取疾病信息
        if case.recognized_entities.diseases:
            disease = case.recognized_entities.diseases[0]
            if disease.matches:
                disease_info = self.get_disease_by_id(disease.matches[0].id)
                self._update_disease_info(enhanced_case.disease, disease_info)
        
        # 获取证据信息
        self._gather_evidence(enhanced_case)
        
        return enhanced_case

    def get_drug_by_id(self, drug_id: str) -> Dict:
        """根据ID获取药品信息"""
        try:
            result = self.es.get(index=self.drugs_index, id=drug_id)
            return result['_source']
        except Exception as e:
            logger.warning(f"获取药品信息失败: {str(e)}")
            return {}

    def get_drug_by_name(self, drug_name: str) -> Dict:
        """根据名称获取药品信息"""
        try:
            query = {
                "query": {
                    "bool": {
                        "should": [
                            {"match": {"name": drug_name}},
                            {"match": {"standard_name": drug_name}},
                            {"match": {"aliases": drug_name}}
                        ]
                    }
                }
            }
            result = self.es.search(index=self.drugs_index, body=query)
            hits = result['hits']['hits']
            return hits[0]['_source'] if hits else {}
        except Exception as e:
            logger.warning(f"获取药品信息失败: {str(e)}")
            return {}

    def get_disease_by_id(self, disease_id: str) -> Dict:
        """根据ID获取疾病信息"""
        try:
            result = self.es.get(index=self.diseases_index, id=disease_id)
            return result['_source']
        except Exception as e:
            logger.warning(f"获取疾病信息失败: {str(e)}")
            return {}

    def get_disease_by_name(self, disease_name: str) -> Dict:
        """根据名称获取疾病信息"""
        try:
            query = {
                "query": {
                    "bool": {
                        "should": [
                            {"match": {"name": disease_name}},
                            {"match": {"standard_name": disease_name}},
                            {"match": {"aliases": disease_name}}
                        ]
                    }
                }
            }
            result = self.es.search(index=self.diseases_index, body=query)
            hits = result['hits']['hits']
            return hits[0]['_source'] if hits else {}
        except Exception as e:
            logger.warning(f"获取疾病信息失败: {str(e)}")
            return {}

    def _gather_evidence(self, enhanced_case: EnhancedCase):
        """收集相关证据"""
        drug_id = enhanced_case.drug.id
        disease_id = enhanced_case.disease.id
        
        # 获取临床指南
        enhanced_case.evidence.clinical_guidelines = self._get_clinical_guidelines(
            drug_id, disease_id
        )
        
        # 获取专家共识
        enhanced_case.evidence.expert_consensus = self._get_expert_consensus(
            drug_id, disease_id
        )
        
        # 获取研究文献
        enhanced_case.evidence.research_papers = self._get_research_papers(
            drug_id, disease_id
        )

    def _get_clinical_guidelines(self, drug_id: str, disease_id: str) -> List[Dict]:
        """获取相关的临床指南"""
        try:
            query = {
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"drug_id": drug_id}},
                            {"term": {"disease_id": disease_id}}
                        ]
                    }
                },
                "size": 5
            }
            result = self.es.search(index=self.clinical_guidelines_index, body=query)
            return [hit['_source'] for hit in result['hits']['hits']]
        except NotFoundError:
            logger.warning(f"临床指南索引不存在: {self.clinical_guidelines_index}")
            return []
        except Exception as e:
            logger.warning(f"获取临床指南失败: {str(e)}")
            return []

    def _get_expert_consensus(self, drug_id: str, disease_id: str) -> List[Dict]:
        """获取相关的专家共识"""
        try:
            query = {
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"drug_id": drug_id}},
                            {"term": {"disease_id": disease_id}}
                        ]
                    }
                },
                "size": 5
            }
            result = self.es.search(index=self.expert_consensus_index, body=query)
            return [hit['_source'] for hit in result['hits']['hits']]
        except NotFoundError:
            logger.warning(f"专家共识索引不存在: {self.expert_consensus_index}")
            return []
        except Exception as e:
            logger.warning(f"获取专家共识失败: {str(e)}")
            return []

    def _get_research_papers(self, drug_id: str, disease_id: str) -> List[Dict]:
        """获取相关的研究文献"""
        try:
            query = {
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"drug_id": drug_id}},
                            {"term": {"disease_id": disease_id}}
                        ]
                    }
                },
                "size": 10
            }
            result = self.es.search(index=self.research_papers_index, body=query)
            return [hit['_source'] for hit in result['hits']['hits']]
        except NotFoundError:
            logger.warning(f"研究文献索引不存在: {self.research_papers_index}")
            return []
        except Exception as e:
            logger.warning(f"获取研究文献失败: {str(e)}")
            return []

    def _update_drug_info(self, drug_info: EnhancedCase.DrugInfo, data: Dict):
        """更新药品信息"""
        drug_info.id = data.get('id')
        drug_info.name = data.get('name')
        # 确保standard_name有值，如果没有则使用name
        drug_info.standard_name = data.get('standard_name') or data.get('name')
        
        # 优先使用indications_list（结构化疾病列表），如果不存在则使用indications
        indications_list = data.get('indications_list', [])
        if indications_list:
            drug_info.indications = indications_list
        else:
            drug_info.indications = data.get('indications', [])
        
        drug_info.contraindications = data.get('contraindications', [])
        drug_info.precautions = data.get('precautions', [])
        drug_info.pharmacology = data.get('pharmacology')
        drug_info.details = data.get('details', {})

    def _update_disease_info(self, disease_info: EnhancedCase.DiseaseInfo, data: Dict):
        """更新疾病信息"""
        disease_info.id = data.get('id')
        disease_info.name = data.get('name')
        # 确保standard_name有值，如果没有则使用name
        disease_info.standard_name = data.get('standard_name') or data.get('name')
        disease_info.description = data.get('description')
        disease_info.icd_code = data.get('icd_code')
