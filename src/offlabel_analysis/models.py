"""数据模型定义"""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, ConfigDict
from datetime import datetime

class DrugMatch(BaseModel):
    """ES 匹配的药品信息"""
    id: str
    standard_name: str
    score: Optional[float] = None  # ES 匹配分数

class DiseaseMatch(BaseModel):
    """ES 匹配的疾病信息"""
    id: str
    standard_name: str
    score: Optional[float] = None  # ES 匹配分数

class Drug(BaseModel):
    """药品实体"""
    name: str  # LLM 识别的原始名称
    matches: List[DrugMatch] = []  # ES 匹配的结果列表

class Disease(BaseModel):
    """疾病实体"""
    name: str  # LLM 识别的原始名称
    matches: List[DiseaseMatch] = []  # ES 匹配的结果列表

class Context(BaseModel):
    """病例上下文"""
    description: str
    raw_data: Optional[Dict] = None

class RecognizedEntities(BaseModel):
    """识别出的实体"""
    drugs: List[Drug] = []  # 支持多个药品
    diseases: List[Disease] = []  # 支持多个疾病
    context: Context
    additional_info: Dict[str, Any] = {
        "think": None
    }

class IndicationMatch(BaseModel):
    """适应症匹配结果"""
    score: float
    matching_indication: str
    reasoning: str

class MechanismSimilarity(BaseModel):
    """机制相似性分析"""
    score: float
    reasoning: str

class EvidenceSupport(BaseModel):
    """证据支持"""
    level: str  # A/B/C/D
    description: str

class Recommendation(BaseModel):
    """用药建议"""
    decision: str  # "建议使用"/"谨慎使用"/"不建议使用"
    explanation: str
    risk_assessment: str

class Analysis(BaseModel):
    """分析结果"""
    indication_match: IndicationMatch
    mechanism_similarity: MechanismSimilarity
    evidence_support: EvidenceSupport

class AnalysisResult(BaseModel):
    """完整分析结果"""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    is_offlabel: bool
    analysis: Analysis
    recommendation: Recommendation
    metadata: Dict[str, Any]

class Case(BaseModel):
    """病例数据"""
    id: str
    recognized_entities: RecognizedEntities
    analysis_result: Optional[AnalysisResult] = None
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()
