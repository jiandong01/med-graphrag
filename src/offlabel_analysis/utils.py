from datetime import datetime
from src.offlabel_analysis.models import (
    Case, AnalysisResult, RecognizedEntities, Context,
    RecognizedDrug, RecognizedDisease, DrugMatch, DiseaseMatch
)


def create_case_from_entity_recognition(data: dict) -> Case:
    """从实体识别结果创建Case对象"""
    # 创建药品列表
    drugs = [
        RecognizedDrug(
            name=drug['name'],
            matches=[
                DrugMatch(
                    id=match['id'],
                    standard_name=match['standard_name'],
                    score=match['score']
                )
                for match in drug.get('matches', [])
            ]
        )
        for drug in data.get('drugs', [])
    ]
    
    # 创建疾病列表
    diseases = [
        RecognizedDisease(
            name=disease['name'],
            matches=[
                DiseaseMatch(
                    id=match['id'],
                    standard_name=match['standard_name'],
                    score=match['score']
                )
                for match in disease.get('matches', [])
            ]
        )
        for disease in data.get('diseases', [])
    ]
    
    # 创建上下文
    context = None
    if 'context' in data:
        context = Context(
            description=data['context']['description'],
            raw_data=data['context']['raw_data']
        )
    
    # 创建RecognizedEntities
    recognized_entities = RecognizedEntities(
        drugs=drugs,
        diseases=diseases,
        context=context
    )
    
    # 创建Case
    return Case(
        id=f"case_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        recognized_entities=recognized_entities
    )