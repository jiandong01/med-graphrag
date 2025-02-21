from unittest.mock import MagicMock
from typing import Dict, Any

class MockElasticsearch:
    def __init__(self, *args, **kwargs):
        self.indices = MagicMock()
        self.search = MagicMock(side_effect=self._mock_search)
        self.get = MagicMock(side_effect=self._mock_get)

    def _mock_search(self, index: str, body: Dict[str, Any]) -> Dict[str, Any]:
        # Mock search results based on the query
        hits = []
        if index == 'drugs':
            if "阿莫西林" in str(body):
                hits = [self._create_amoxicillin_hit()]
            elif "西地那非" in str(body):
                hits = [self._create_sildenafil_hit()]
            else:
                hits = [self._create_drug_hit()]
        elif index == 'diseases':
            if "链球菌性咽炎" in str(body):
                hits = [self._create_pharyngitis_hit()]
            elif "肺动脉高压" in str(body):
                hits = [self._create_pah_hit()]
            else:
                hits = [self._create_disease_hit()]
        elif index in ['clinical_guidelines', 'expert_consensus', 'research_papers']:
            hits = [self._create_evidence_hit(index) for _ in range(3)]

        return {
            "hits": {
                "hits": hits
            }
        }

    def _mock_get(self, index: str, id: str) -> Dict[str, Any]:
        # Mock get results based on the ID
        if index == 'drugs':
            if "amoxicillin" in id.lower():
                return {"_source": self._create_amoxicillin_hit()["_source"]}
            elif "sildenafil" in id.lower():
                return {"_source": self._create_sildenafil_hit()["_source"]}
            else:
                return {"_source": self._create_drug_hit()["_source"]}
        elif index == 'diseases':
            if "pharyngitis" in id.lower():
                return {"_source": self._create_pharyngitis_hit()["_source"]}
            elif "pah" in id.lower():
                return {"_source": self._create_pah_hit()["_source"]}
            else:
                return {"_source": self._create_disease_hit()["_source"]}
        else:
            return {"_source": {}}

    def _create_amoxicillin_hit(self) -> Dict[str, Any]:
        return {
            "_source": {
                "id": "drug_001",
                "name": "阿莫西林",
                "standard_name": "阿莫西林片",
                "indications": ["急性链球菌性咽炎", "中耳炎", "肺炎"],
                "contraindications": ["青霉素过敏"],
                "precautions": ["注意观察过敏反应"],
                "pharmacology": "β-内酰胺类抗生素，通过抑制细菌细胞壁合成发挥作用",
                "details": {"drug_class": "青霉素类"}
            }
        }

    def _create_sildenafil_hit(self) -> Dict[str, Any]:
        return {
            "_source": {
                "id": "drug_002",
                "name": "西地那非",
                "standard_name": "枸橼酸西地那非片",
                "indications": ["勃起功能障碍"],
                "contraindications": ["硝酸酯类药物同时使用"],
                "precautions": ["心血管疾病患者慎用"],
                "pharmacology": "PDE5抑制剂，通过抑制PDE5来增加cGMP水平",
                "details": {"drug_class": "PDE5抑制剂"}
            }
        }

    def _create_pharyngitis_hit(self) -> Dict[str, Any]:
        return {
            "_source": {
                "id": "disease_001",
                "name": "急性链球菌性咽炎",
                "standard_name": "化脓性链球菌咽炎",
                "description": "由A组β溶血性链球菌引起的急性咽部感染",
                "icd_code": "J02.0"
            }
        }

    def _create_pah_hit(self) -> Dict[str, Any]:
        return {
            "_source": {
                "id": "disease_002",
                "name": "肺动脉高压",
                "standard_name": "肺动脉高压",
                "description": "肺动脉压力持续升高的疾病",
                "icd_code": "I27.0"
            }
        }

    def _create_drug_hit(self) -> Dict[str, Any]:
        return {
            "_source": {
                "id": "mock_drug_id",
                "name": "Mock Drug",
                "standard_name": "Mock Drug Standard Name",
                "indications": ["Mock Indication 1", "Mock Indication 2"],
                "contraindications": ["Mock Contraindication"],
                "precautions": ["Mock Precaution"],
                "pharmacology": "Mock Pharmacology",
                "details": {"mock_key": "mock_value"}
            }
        }

    def _create_disease_hit(self) -> Dict[str, Any]:
        return {
            "_source": {
                "id": "mock_disease_id",
                "name": "Mock Disease",
                "standard_name": "Mock Disease Standard Name",
                "description": "Mock Disease Description",
                "icd_code": "M00.0"
            }
        }

    def _create_evidence_hit(self, evidence_type: str) -> Dict[str, Any]:
        if evidence_type == 'clinical_guidelines':
            return {
                "_source": {
                    "id": f"mock_{evidence_type}_id",
                    "title": "临床指南",
                    "content": "推荐使用阿莫西林治疗急性链球菌性咽炎",
                    "recommendation_level": "A",
                    "drug_id": "drug_001",
                    "disease_id": "disease_001"
                }
            }
        elif evidence_type == 'expert_consensus':
            return {
                "_source": {
                    "id": f"mock_{evidence_type}_id",
                    "title": "专家共识",
                    "content": "专家一致认为阿莫西林是治疗急性链球菌性咽炎的一线用药",
                    "consensus_level": "强烈推荐",
                    "drug_id": "drug_001",
                    "disease_id": "disease_001"
                }
            }
        else:  # research_papers
            return {
                "_source": {
                    "id": f"mock_{evidence_type}_id",
                    "title": "研究论文",
                    "content": "随机对照试验证实阿莫西林在治疗急性链球菌性咽炎中的有效性",
                    "study_type": "RCT",
                    "drug_id": "drug_001",
                    "disease_id": "disease_001"
                }
            }

def get_mock_elastic_client():
    return MockElasticsearch()
