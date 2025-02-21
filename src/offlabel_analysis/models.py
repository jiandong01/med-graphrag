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
    score: float
    matching_indication: str
    reasoning: str

@dataclass
class MechanismSimilarity:
    score: float
    reasoning: str

@dataclass
class EvidenceSupport:
    level: str
    description: str

@dataclass
class Analysis:
    indication_match: IndicationMatch
    mechanism_similarity: MechanismSimilarity
    evidence_support: EvidenceSupport

@dataclass
class Recommendation:
    decision: str
    explanation: str
    risk_assessment: str

@dataclass
class AnalysisResult:
    """分析结果"""
    is_offlabel: bool
    confidence: float
    analysis: Analysis
    recommendation: Recommendation
    evidence_synthesis: Dict[str, Any]
    metadata: Dict[str, Any]
