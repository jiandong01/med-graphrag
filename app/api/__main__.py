"""
Medical GraphRAG API 服务
提供超适应症用药分析的 REST API 接口
"""
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import logging
import sys
import os
from datetime import datetime

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.src.utils import get_elastic_client, load_env, setup_logging
from app.src.offlabel_analysis.main import process_case, batch_process
from app.src.offlabel_analysis.entity_recognition import EntityRecognizer
from app.src.offlabel_analysis.knowledge_enhancer import KnowledgeEnhancer

# 加载环境变量
load_env()

# 配置日志
logger = setup_logging("api", log_dir="logs")

# 创建 FastAPI 应用
app = FastAPI(
    title="Medical GraphRAG API",
    description="基于知识图谱的医疗超适应症用药分析系统",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应配置具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局 ES 客户端
es_client = None

# ==================== 数据模型 ====================

class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    timestamp: str
    elasticsearch: str
    version: str

class PatientInfo(BaseModel):
    """患者信息"""
    age: Optional[int] = Field(None, description="年龄")
    gender: Optional[str] = Field(None, description="性别")
    diagnosis: str = Field(..., description="诊断")
    medical_history: Optional[str] = Field(None, description="病史")

class PrescriptionInfo(BaseModel):
    """处方信息"""
    drug_name: str = Field(..., description="药品名称")
    dosage: Optional[str] = Field(None, description="剂量")
    frequency: Optional[str] = Field(None, description="频次")
    duration: Optional[str] = Field(None, description="疗程")

class AnalysisRequest(BaseModel):
    """超适应症分析请求"""
    patient: PatientInfo
    prescription: PrescriptionInfo
    clinical_context: Optional[str] = Field(None, description="临床背景")

    class Config:
        schema_extra = {
            "example": {
                "patient": {
                    "age": 65,
                    "gender": "男",
                    "diagnosis": "心力衰竭",
                    "medical_history": "高血压10年"
                },
                "prescription": {
                    "drug_name": "美托洛尔缓释片",
                    "dosage": "47.5mg",
                    "frequency": "qd",
                    "duration": "长期"
                },
                "clinical_context": "慢性心力衰竭，NYHA II级"
            }
        }

class BatchAnalysisRequest(BaseModel):
    """批量分析请求"""
    cases: List[AnalysisRequest]

class EntityRecognitionRequest(BaseModel):
    """实体识别请求"""
    text: str = Field(..., description="待识别文本")
    context: Optional[str] = Field(None, description="上下文信息")

class SearchRequest(BaseModel):
    """搜索请求"""
    query: str = Field(..., description="搜索关键词")
    size: int = Field(10, description="返回数量", ge=1, le=100)
    filters: Optional[Dict[str, Any]] = Field(None, description="过滤条件")

class DrugDetailRequest(BaseModel):
    """药品详情请求"""
    drug_id: Optional[str] = Field(None, description="药品ID")
    drug_name: Optional[str] = Field(None, description="药品名称")

class DiseaseDetailRequest(BaseModel):
    """疾病详情请求"""
    disease_id: Optional[str] = Field(None, description="疾病ID")
    disease_name: Optional[str] = Field(None, description="疾病名称")

# ==================== 生命周期事件 ====================

@app.on_event("startup")
async def startup_event():
    """应用启动时初始化"""
    global es_client
    try:
        logger.info("正在初始化 Elasticsearch 客户端...")
        es_client = get_elastic_client()
        
        # 测试连接
        if es_client.ping():
            logger.info("Elasticsearch 连接成功")
        else:
            logger.error("Elasticsearch 连接失败")
            raise Exception("无法连接到 Elasticsearch")
            
    except Exception as e:
        logger.error(f"启动失败: {str(e)}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时清理资源"""
    global es_client
    if es_client:
        es_client.close()
        logger.info("Elasticsearch 连接已关闭")

# ==================== API 端点 ====================

@app.get("/", tags=["系统"])
async def root():
    """根路径"""
    return {
        "name": "Medical GraphRAG API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health", response_model=HealthResponse, tags=["系统"])
async def health_check():
    """健康检查"""
    try:
        es_status = "connected" if es_client and es_client.ping() else "disconnected"
        
        return HealthResponse(
            status="healthy" if es_status == "connected" else "unhealthy",
            timestamp=datetime.now().isoformat(),
            elasticsearch=es_status,
            version="1.0.0"
        )
    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )

@app.post("/api/v1/analyze", tags=["分析"])
async def analyze_offlabel(request: AnalysisRequest):
    """
    超适应症用药分析
    
    分析处方药品对于患者诊断疾病的适用性，判断是否为合理超适应症用药。
    """
    try:
        # 构造描述
        description = f"患者{request.patient.age}岁{request.patient.gender}性，诊断为{request.patient.diagnosis}"
        if request.patient.medical_history:
            description += f"，{request.patient.medical_history}"
        description += f"。处方{request.prescription.drug_name}"
        if request.prescription.dosage:
            description += f" {request.prescription.dosage}"
        if request.prescription.frequency:
            description += f" {request.prescription.frequency}"
        if request.clinical_context:
            description += f"。{request.clinical_context}"
        
        # 构造输入数据
        input_data = {
            "description": description,
            "patient_info": {
                "age": request.patient.age,
                "gender": request.patient.gender,
                "diagnosis": request.patient.diagnosis,
                "medical_history": request.patient.medical_history
            },
            "prescription": {
                "drug_name": request.prescription.drug_name,
                "dosage": request.prescription.dosage,
                "frequency": request.prescription.frequency,
                "duration": request.prescription.duration
            },
            "clinical_context": request.clinical_context
        }
        
        # 执行分析
        logger.info(f"开始分析: {request.prescription.drug_name} → {request.patient.diagnosis}")
        result = process_case(input_data)
        
        return {
            "success": True,
            "data": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"分析失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"分析失败: {str(e)}"
        )

@app.post("/api/v1/analyze/batch", tags=["分析"])
async def batch_analyze_offlabel(request: BatchAnalysisRequest):
    """
    批量超适应症用药分析
    
    批量处理多个病例的超适应症用药分析。
    """
    try:
        # 转换输入数据
        input_data_list = []
        for case in request.cases:
            input_data = {
                "patient_info": {
                    "age": case.patient.age,
                    "gender": case.patient.gender,
                    "diagnosis": case.patient.diagnosis,
                    "medical_history": case.patient.medical_history
                },
                "prescription": {
                    "drug_name": case.prescription.drug_name,
                    "dosage": case.prescription.dosage,
                    "frequency": case.prescription.frequency,
                    "duration": case.prescription.duration
                },
                "clinical_context": case.clinical_context
            }
            input_data_list.append(input_data)
        
        # 批量执行分析
        logger.info(f"开始批量分析: {len(input_data_list)} 个病例")
        results = batch_process(input_data_list)
        
        return {
            "success": True,
            "data": results,
            "count": len(results),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"批量分析失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量分析失败: {str(e)}"
        )

@app.post("/api/v1/entity/recognize", tags=["实体识别"])
async def recognize_entities(request: EntityRecognitionRequest):
    """
    医学实体识别
    
    从文本中识别药品和疾病实体。
    """
    try:
        recognizer = EntityRecognizer(es=es_client)
        
        input_data = {
            "text": request.text,
            "context": request.context
        }
        
        logger.info(f"开始实体识别: {request.text[:50]}...")
        result = recognizer.recognize(input_data)
        
        return {
            "success": True,
            "data": {
                "drugs": [drug.dict() for drug in result.drugs],
                "diseases": [disease.dict() for disease in result.diseases],
                "context": result.context.dict() if result.context else None
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"实体识别失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"实体识别失败: {str(e)}"
        )

@app.post("/api/v1/search/drug", tags=["搜索"])
async def search_drugs(request: SearchRequest):
    """
    药品搜索
    
    根据关键词搜索药品信息。
    """
    try:
        query_body = {
            "query": {
                "multi_match": {
                    "query": request.query,
                    "fields": ["name^3", "components^2", "indications", "categories"]
                }
            },
            "size": request.size
        }
        
        if request.filters:
            query_body["query"] = {
                "bool": {
                    "must": [query_body["query"]],
                    "filter": []
                }
            }
            for key, value in request.filters.items():
                query_body["query"]["bool"]["filter"].append({"term": {key: value}})
        
        result = es_client.search(index="drugs_index", body=query_body)
        
        drugs = [hit["_source"] for hit in result["hits"]["hits"]]
        
        return {
            "success": True,
            "data": drugs,
            "total": result["hits"]["total"]["value"],
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"药品搜索失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"药品搜索失败: {str(e)}"
        )

@app.post("/api/v1/search/disease", tags=["搜索"])
async def search_diseases(request: SearchRequest):
    """
    疾病搜索
    
    根据关键词搜索疾病信息。
    """
    try:
        query_body = {
            "query": {
                "multi_match": {
                    "query": request.query,
                    "fields": ["name^3", "category", "synonyms"]
                }
            },
            "size": request.size
        }
        
        if request.filters:
            query_body["query"] = {
                "bool": {
                    "must": [query_body["query"]],
                    "filter": []
                }
            }
            for key, value in request.filters.items():
                query_body["query"]["bool"]["filter"].append({"term": {key: value}})
        
        result = es_client.search(index="diseases_index", body=query_body)
        
        diseases = [hit["_source"] for hit in result["hits"]["hits"]]
        
        return {
            "success": True,
            "data": diseases,
            "total": result["hits"]["total"]["value"],
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"疾病搜索失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"疾病搜索失败: {str(e)}"
        )

@app.post("/api/v1/drug/detail", tags=["详情"])
async def get_drug_detail(request: DrugDetailRequest):
    """
    获取药品详情
    
    根据药品ID或名称获取完整的药品信息。
    """
    try:
        enhancer = KnowledgeEnhancer(es=es_client)
        
        if request.drug_id:
            drug_info = enhancer.get_drug_by_id(request.drug_id)
        elif request.drug_name:
            drug_info = enhancer.get_drug_by_name(request.drug_name)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="必须提供 drug_id 或 drug_name"
            )
        
        if not drug_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="未找到药品信息"
            )
        
        return {
            "success": True,
            "data": drug_info,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取药品详情失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取药品详情失败: {str(e)}"
        )

@app.post("/api/v1/disease/detail", tags=["详情"])
async def get_disease_detail(request: DiseaseDetailRequest):
    """
    获取疾病详情
    
    根据疾病ID或名称获取完整的疾病信息。
    """
    try:
        enhancer = KnowledgeEnhancer(es=es_client)
        
        if request.disease_id:
            disease_info = enhancer.get_disease_by_id(request.disease_id)
        elif request.disease_name:
            disease_info = enhancer.get_disease_by_name(request.disease_name)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="必须提供 disease_id 或 disease_name"
            )
        
        if not disease_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="未找到疾病信息"
            )
        
        return {
            "success": True,
            "data": disease_info,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取疾病详情失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取疾病详情失败: {str(e)}"
        )

# ==================== 错误处理 ====================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全局异常处理"""
    logger.error(f"未处理的异常: {str(exc)}")
    return {
        "success": False,
        "error": str(exc),
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
