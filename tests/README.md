# 测试文档

Med-GraphRAG项目的测试套件，包含两个核心端到端测试。

## 📋 测试文件

### 1. test_pipeline_e2e.py - Pipeline端到端测试 ⭐
**目的**: 验证数据ETL流程的完整性  
**测试范围**: MySQL → processed_drugs.json → Elasticsearch → disease_extraction → diseases索引  
**运行**: `PYTHONPATH=. pytest tests/test_pipeline_e2e.py -v -s`

#### 测试类

##### TestDrugETL - 药品ETL流程测试

**步骤1: 验证处理后的药品文件**
```
输入: data/raw/drugs/processed_drugs.json
输出: 
  ✅ 药品总数: 86,000+
  ✅ 数据结构完整（id, name, indications等）
```

**步骤2: 验证Elasticsearch中的drugs索引**
```
输入: ES连接 + drugs索引
输出:
  ✅ 药品总数: 1,953,754
  ✅ 有indications_list: 67,939
  ✅ 示例药品包含完整信息
```

**步骤3: 验证药品搜索功能**
```
输入: 查询词（美托洛尔、阿莫西林等）
输出:
  ✅ 搜索结果
  ✅ 匹配分数
  ✅ 完整药品信息
```

##### TestDiseaseETL - 疾病ETL流程测试

**步骤1: 验证疾病提取批次文件**
```
输入: data/processed/diseases/diseases_search_after/
输出:
  ✅ 批次文件数: 300+
  ✅ 每批次包含：药品数、成功数、失败数、提取记录
```

**步骤2: 验证提取状态文件**
```
输入: extraction_search_after_state.json
输出:
  ✅ 总药品数、已处理数、进度
  ✅ 成功率统计
```

**步骤3: 验证diseases索引**
```
输入: ES diseases索引
输出:
  ✅ 疾病总数: 108,000+
  ✅ Top疾病（按提及次数）
```

**步骤4: 验证疾病-药品双向关联**
```
输入: 疾病记录
输出:
  ✅ 关联药品列表
  ✅ 反向验证药品存在于drugs索引
```

##### TestETLDataFlow - 完整数据流测试

**端到端数据流跟踪**
```
跟踪一个药品的完整流程:
  步骤1: 在drugs索引中查询 → 找到药品+详细信息
  步骤2: 查找疾病提取记录 → 找到提取的疾病列表
  步骤3: 在diseases索引中查找 → 验证关联关系
```

---

### 2. test_inference_e2e.py - Inference端到端测试 ⭐
**目的**: 验证推理分析流程的完整性  
**测试范围**: 输入 → 实体识别 → 知识增强 → 规则分析 → LLM推理 → 结果综合  
**运行**: `PYTHONPATH=. pytest tests/test_inference_e2e.py -v -s`

#### 测试类

##### TestInferenceWorkflow - 完整推理工作流程

**案例1: 标准用药**
```
案例: 溴吡斯的明 + 重症肌无力

步骤1: 原始输入
  {description, patient_info, prescription}

步骤2: 实体识别
  输入: 原始描述
  输出: 
    - 识别的药品：溴吡斯的明
    - ES匹配：溴吡斯的明片 (ID: xxx, score: 16.5)
    - 识别的疾病：重症肌无力
    - ES匹配：重症肌无力 (ID: xxx, score: 15.2)

步骤3: 执行完整分析
  输入: recognized_entities
  输出:
    - 超适应症判断: False/True
    - 匹配分数: 1.0/0.0
    - 匹配的适应症: "重症肌无力"

步骤4: 最终输出
  {
    is_offlabel: false,
    drug_info: {indications_list, indications, contraindications},
    analysis_details: {indication_match, open_evidence, recommendation}
  }
```

**案例2: 合理的超适应症用药（快速模式）**
```
案例: 美托洛尔 + 心力衰竭

步骤1: 原始输入（快速模式）
  {drug_name, disease_name, description}

步骤2: 严格ES匹配
  输入: "美托洛尔"
  输出: 酒石酸美托洛尔片 (score: 15.6)

步骤3: 获取药品详情
  输出:
    - 适应症列表: ["高血压", "心绞痛", "心肌梗死"]
    - 禁忌症列表: [...]

步骤4: 规则判断
  输入: 适应症列表 vs "心力衰竭"
  输出: 匹配分数=0.0 (未精确匹配)

步骤5: AI辅助分析
  输出:
    - 机制相似度: 0.85
    - 证据等级: C
    - 推理: β受体阻滞作用合理

最终输出:
  - is_offlabel: true (规则判断)
  - 建议: 谨慎使用 (AI辅助)
```

**案例3: 药物类别名过滤**
```
案例: 抗代谢药 + 恶性肿瘤

步骤1: 原始输入
  drug_name: "抗代谢药"

步骤2: 严格匹配验证
  输入: "抗代谢药"
  输出: 0个匹配（✅ 正确过滤）

步骤3: 分析结果
  输出:
    - is_offlabel: null
    - match_status: not_found
    - 友好错误信息

最终输出:
  {
    is_offlabel: null,
    drug_info: {match_status: "not_found"},
    analysis_details: {
      error: "药品信息缺失",
      message: "可能原因：...",
      suggestion: "请使用具体药品名称"
    }
  }
```

##### TestInferenceStepByStep - 分步测试

**完整分步分析示例**
```
案例: 羟基脲 + 真性红细胞增多症

步骤1: 实体识别
  输入: 原始描述
  输出: {原始名, 标准名, ID, 匹配分数}

步骤2: 知识增强
  输入: {药品ID, 疾病ID}
  输出: {
    药品详情: {适应症, 禁忌症, 药理学},
    疾病详情: {标准名, ICD编码}
  }

步骤3: 规则分析
  输入: {药品适应症列表, 患者疾病}
  输出: {is_offlabel, confidence, reasoning}

步骤4: 完整推理（包含LLM）
  输出: 完整的结构化分析结果
```

##### TestInferenceOutputStructure - 输出结构验证

验证输出包含所有必需字段：
- ✅ 顶层字段：case_id, analysis_time, drug_info, disease_info, is_offlabel, analysis_details, metadata
- ✅ drug_info字段：id, name, standard_name, indications_list, indications, contraindications
- ✅ analysis_details字段：indication_match, open_evidence, recommendation

##### TestInferenceBatchProcessing - 批量处理测试

测试批量分析功能的正确性和错误处理

---

## 🎯 测试策略

### Pipeline测试 (test_pipeline_e2e.py)
- **目的**: 验证数据建库流程
- **关键点**: 
  - 药品数据完整性（195万+）
  - 疾病提取正确性（10.8万+）
  - 双向关联准确性
- **每个步骤都输出详细的输入和输出**

### Inference测试 (test_inference_e2e.py)
- **目的**: 验证推理分析流程
- **关键点**:
  - 实体识别准确性（严格匹配）
  - 规则判断正确性（精确匹配）
  - AI辅助合理性（机制分析）
  - 错误处理友好性（药品未匹配）
- **每个步骤都输出详细的输入和输出**

---

## 🚀 运行测试

### 使用 uv 运行（推荐）

```bash
# 运行所有测试
uv run python -m pytest tests/ -v -s

# 单独运行Pipeline测试
uv run python -m pytest tests/test_pipeline_e2e.py -v -s

# 单独运行Inference测试
uv run python -m pytest tests/test_inference_e2e.py -v -s

# 运行特定测试类
uv run python -m pytest tests/test_pipeline_e2e.py::TestDrugETL -v -s

# 运行特定测试用例
uv run python -m pytest tests/test_inference_e2e.py::TestInferenceWorkflow::test_case1_standard_use -v -s
```

### 或者使用 make 命令

```bash
# 在项目根目录添加到 Makefile
make test           # 运行所有测试
make test-pipeline  # 运行Pipeline测试
make test-inference # 运行Inference测试
```

### 使用传统方式运行

```bash
# 需要设置PYTHONPATH
PYTHONPATH=. pytest tests/ -v -s
PYTHONPATH=. pytest tests/test_pipeline_e2e.py -v -s
PYTHONPATH=. pytest tests/test_inference_e2e.py -v -s
```

### 快速测试（不显示详细输出）

```bash
# 只看测试结果，不显示print输出
uv run pytest tests/ -v

# 只运行失败的测试
uv run pytest tests/ --lf -v -s
```

---

## 📊 测试覆盖

### Pipeline流程
```
PostgreSQL 
    ↓ drug_etl
processed_drugs.json (✅ test_pipeline_e2e)
    ↓ drug_indexer
ES drugs索引 (✅ test_pipeline_e2e)
    ↓ disease_extraction
批次文件 (✅ test_pipeline_e2e)
    ↓ disease_indexer
ES diseases索引 (✅ test_pipeline_e2e)
```

### Inference流程
```
输入数据
    ↓ entity_matcher (✅ test_inference_e2e)
识别的实体
    ↓ knowledge_enhancer (✅ test_inference_e2e)
增强的病例
    ↓ rule_checker (✅ test_inference_e2e)
规则判断
    ↓ llm_reasoner (✅ test_inference_e2e)
LLM分析
    ↓ result_synthesizer (✅ test_inference_e2e)
最终结果
```

---

## 📈 成功指标

### Pipeline测试
- ✅ 药品数量 > 1,900,000
- ✅ 有indications_list > 67,000
- ✅ 疾病数量 > 108,000
- ✅ 疾病提取批次 > 300
- ✅ 双向关联完整

### Inference测试
- ✅ 实体识别准确（严格匹配）
- ✅ 规则判断正确（精确字符串匹配）
- ✅ AI辅助合理（机制分析）
- ✅ 错误处理友好（返回结构化信息）
- ✅ 输出结构完整（所有必需字段）

---

## ✨ 测试价值

### Pipeline测试确保
1. ✅ 数据完整性：195万药品、10.8万疾病都在ES中
2. ✅ 数据质量：67,939个药品有结构化适应症列表
3. ✅ 关联正确性：药品-疾病双向可查
4. ✅ ETL流程可追溯：每个步骤都有输入输出

### Inference测试确保
1. ✅ 匹配严格性：消除"驴唇不对马嘴"的错误
2. ✅ 判断准确性：规则+AI双重保障
3. ✅ 错误处理：友好的信息，不中断流程
4. ✅ 输出完整性：包含药品详细信息便于分析

---

## 📝 测试输出说明

### Pipeline测试输出
- 每个步骤的数据量统计
- 数据结构示例
- 关联关系验证
- ES索引健康检查

### Inference测试输出
- 每个步骤的输入数据
- 每个步骤的处理结果
- 中间状态（实体识别、知识增强、规则分析）
- 最终输出（包含完整的药品适应症列表等）

---

## 🔧 常见问题

### ModuleNotFoundError
```bash
# 解决：设置PYTHONPATH
PYTHONPATH=. pytest tests/test_pipeline_e2e.py -v -s
```

### diseases索引不存在
```bash
# 解决：运行疾病索引器
python -m app.pipeline.disease_indexer --rebuild
```

### ES连接失败
```bash
# 解决：检查Docker服务
docker compose ps
make es up
```

### API密钥错误
```bash
# 解决：配置环境变量
cp .env.example .env
# 编辑 .env，配置 DEEPSEEK_API_KEY
```

---

## 🎉 测试理念

**"每个步骤都清晰可见"** - 两个端到端测试涵盖了：
- ✅ 数据ETL的完整流程（Pipeline）
- ✅ 推理分析的完整流程（Inference）
- ✅ 每个步骤的输入输出
- ✅ 错误处理和边界情况

通过测试后，可以确信整个系统从数据建库到智能推理都是完整、正确、可用的！
