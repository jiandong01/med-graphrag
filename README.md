# 医疗超适应症智能分析系统

基于大语言模型和Elasticsearch的智能超适应症用药分析系统。

## 🎯 核心功能

- **实体识别**: 自动识别并标准化药品和疾病（LLM + ES双重验证）
- **规则判断**: 基于indications_list的精确字符串匹配
- **AI辅助**: LLM提供机制分析和证据评估
- **风险评估**: 完整的推理链和安全性建议

## 🏗️ 项目结构

```
med-graphrag/
├── app/
│   ├── pipeline/          # 数据建库 (MySQL → ES)
│   ├── inference/         # 推理分析 (核心)
│   ├── shared/            # 共享工具
│   └── api/               # REST API
├── services/              # ES/PostgreSQL配置
├── tests/                 # 测试用例
├── examples/              # 示例病例
├── docs/                  # 文档
└── scripts/               # 工具脚本
```

## 🚀 快速开始

### 1. 环境配置

```bash
cp .env.example .env
# 编辑 .env，配置 DEEPSEEK_API_KEY 和 ELASTIC_PASSWORD
```

### 2. 启动服务

```bash
make all up          # 启动所有服务
# 或
make es up           # 只启动 Elasticsearch
make api up          # 只启动 API
```

### 3. 访问服务

- **API**: http://localhost:8000/docs
- **Elasticsearch**: http://localhost:9200
- **Kibana**: http://localhost:5601

## 📖 使用示例

### API调用

```bash
curl -X POST "http://localhost:8000/api/v1/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "患者诊断为心力衰竭，拟使用美托洛尔治疗",
    "patient_info": {"age": 65, "gender": "男"},
    "prescription": {"drug": "美托洛尔"}
  }'
```

### Python SDK

```python
from app.inference.engine import InferenceEngine

engine = InferenceEngine()
result = engine.analyze({
    "description": "患者诊断为心力衰竭，拟使用美托洛尔治疗",
    "patient_info": {"age": 65, "gender": "男"},
    "prescription": {"drug": "美托洛尔"}
})

print(result["is_offlabel"])  # True/False
```

## 🔍 系统流程

```
输入病例
   ↓
实体识别 (LLM + ES)
   ↓
知识增强 (ES indications_list)
   ↓
规则分析 (精确匹配) + LLM推理 (机制分析)
   ↓
结果综合 (规则判断 + AI辅助)
   ↓
输出结果
```

## 📊 判断逻辑

### 规则判断（严格）
```python
if 患者疾病 IN 药品适应症列表:
    is_offlabel = False  # 标准用药
else:
    is_offlabel = True   # 超适应症
```

### AI辅助（参考）
```python
{
  "mechanism_similarity": 0.9,    # 机制相似度
  "evidence_support": {           # 证据支持
    "level": "D",
    "clinical_guidelines": [],
    "description": "..."
  }
}
```

## 💾 数据基础

| 组件 | 规模 | 说明 |
|------|------|------|
| Elasticsearch | 1.9M+ 药品 | 全文检索 |
| indications_list | 67.9k | 结构化适应症 ✨ |
| diseases | 108k | 疾病索引 |

## 📝 示例病例

`examples/cases/` 包含三个完整示例：

1. **标准用药**: 阿司匹林 → 心梗预防
2. **合理超适应症**: 美托洛尔 → 心力衰竭  
3. **不合理超适应症**: 利巴韦林 → 普通感冒

## 🧪 测试

```bash
make test                              # 所有测试
pytest tests/test_inference_e2e.py     # 端到端测试
```

## 📚 文档

- **模块架构**: `docs/INFERENCE_MODULE_OVERVIEW.md`
- **系统设计**: `docs/系统设计及实现.md`
- **研究总结**: `docs/医疗超适应症分析系统研究总结.md`

## 🔧 Makefile命令

```bash
make help           # 查看所有命令

# 服务管理
make es up          # 启动 Elasticsearch
make api up         # 启动 API
make all up         # 启动所有服务
make status         # 查看状态
make logs           # 查看日志

# 开发工具
make test           # 运行测试
make clean          # 清理临时文件
```

## 🎉 最新优化 (2025-10-30)

### 判断逻辑严格化
- ✅ is_offlabel只基于精确匹配（confidence=1.0）
- ✅ AI分析作为辅助信息，不影响判断

### 数据结构优化
- ✅ 67,939个药品的indications_list
- ✅ 支持精确字符串匹配
- ✅ 数据质量优秀（LLM提取）

### 输出结构清晰化
```json
{
  "is_offlabel": true,           // 规则判断
  "analysis_details": {
    "indication_match": {...},   // 规则依据  
    "open_evidence": {...},      // AI辅助
    "recommendation": {...}      // 综合建议
  }
}
```

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License
