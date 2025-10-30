"""数据模型定义"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class DrugMatch:
    id: str
    standard_name: str
    score: float

@dataclass
class DiseaseMatch:
    id: str
    standard_name: str
    score: float

@dataclass
class RecognizedDrug:
    name: str
    matches: List[DrugMatch]

@dataclass
class RecognizedDisease:
    name: str
    matches: List[DiseaseMatch]

@dataclass
class Context:
    description: str
    raw_data: Dict[str, Any]

@dataclass
class RecognizedEntities:
    drugs: List[RecognizedDrug]
    diseases: List[RecognizedDisease]
    context: Optional[Context] = None
    additional_info: Optional[Dict[str, Any]] = None

@dataclass
class Case:
    """原始病例数据"""
    id: str
    recognized_entities: RecognizedEntities
    analysis_result: Optional[Any] = None
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()

class EnhancedCase:
    """增强的病例实例，包含所有分析所需信息"""
    
    class DrugInfo:
        def __init__(self):
            self.id: str = None
            self.name: str = None
            self.standard_name: str = None
            self.indications: List[str] = []
            self.contraindications: List[str] = []
            self.precautions: List[str] = []
            self.pharmacology: str = None
            self.details: Dict[str, Any] = {}
    
    class DiseaseInfo:
        def __init__(self):
            self.id: str = None
            self.name: str = None
            self.standard_name: str = None
            self.description: str = None
            self.icd_code: str = None
    
    class Evidence:
        def __init__(self):
            self.clinical_guidelines: List[Dict] = []
            self.expert_consensus: List[Dict] = []
            self.research_papers: List[Dict] = []
            
    def __init__(self, case: Case):
        self.original_case = case
        self.drug = self.DrugInfo()
        self.disease = self.DiseaseInfo()
        self.evidence = self.Evidence()
        self.context = case.recognized_entities.context

@dataclass
class IndicationMatch:
    """适应症匹配结果（规则判断）"""
    score: float  # 0.0表示无匹配，1.0表示精确匹配
    matching_indication: str
    reasoning: str

@dataclass
class MechanismSimilarity:
    """机制相似度分析（AI辅助）"""
    score: float
    reasoning: str

@dataclass
class EvidenceSupport:
    """证据支持（AI辅助）"""
    level: str  # A/B/C/D 证据等级
    clinical_guidelines: List[Dict] = None  # 临床指南
    expert_consensus: List[Dict] = None     # 专家共识
    research_papers: List[Dict] = None      # 研究文献
    description: str = ""

@dataclass
class OpenEvidence:
    """开放证据（AI辅助分析）"""
    mechanism_similarity: MechanismSimilarity
    evidence_support: EvidenceSupport

@dataclass
class Recommendation:
    """推荐建议"""
    decision: str
    explanation: str
    risk_assessment: str

@dataclass
class AnalysisDetails:
    """分析详情"""
    indication_match: IndicationMatch     # 规则判断
    open_evidence: OpenEvidence           # AI辅助
    recommendation: Recommendation        # 推荐建议

@dataclass
class DrugInfo:
    """药品信息"""
    id: str
    name: str
    standard_name: str

@dataclass
class DiseaseInfo:
    """疾病信息"""
    id: Optional[str]
    name: str
    standard_name: Optional[str]

@dataclass
class AnalysisResult:
    """分析结果 - 重构后的结构"""
    case_id: str
    analysis_time: str
    drug_info: DrugInfo
    disease_info: DiseaseInfo
    is_offlabel: bool  # 严格规则判断
    analysis_details: AnalysisDetails
    metadata: Dict[str, Any]
