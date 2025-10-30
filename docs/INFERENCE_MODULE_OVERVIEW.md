# Inference 模块架构说明

## 模块概览

inference模块是med-graphrag的核心推理引擎，负责超适应症用药的智能分析和判断。

## 模块关系图

```
┌─────────────────────────────────────────────────────────────────┐
│                        InferenceEngine                          │
│                        (engine.py)                              │
│                 ┌───────────┐                                   │
│            ┌───►│ 协调各模块 │◄───┐                             │
│            │    └───────────┘    │                             │
└────────────┼─────────────────────┼─────────────────────────────┘
             │                     │
    ┌────────▼────────┐   ┌───────▼────────┐
    │ EntityRecognizer │   │ IndicationAnalyzer│
    │(entity_matcher.py│   │ (llm_reasoner.py) │
    └────────┬─────────┘   └───────┬──────────┘
             │                     │
             │              ┌──────▼──────┐
             │              │KnowledgeEnhancer│
             │              │(knowledge_    │
             │              │ retriever.py) │
             │              └──────┬────────┘
             │                     │
             │              ┌──────▼─────────┐
             │              │  RuleAnalyzer  │
             │              │(rule_checker.py)│
             │              └──────┬─────────┘
             │                     │
             │              ┌──────▼────────────┐
             │              │ResultSynthesizer  │
             │              │(result_synthesizer│
             │              │       .py)        │
             │              └──────┬────────────┘
             │                     │
             └─────────────────────▼────────────┐
                              ResultGenerator    │
                            (result_generator.py)│
                              └──────────────────┘
```

## 核心模块

### 1. **engine.py** - 推理引擎
**职责**：总控制器，协调所有分析步骤

**主要类**：`InferenceEngine`

**核心方法**：
- `analyze()` - 单例分析
- `analyze_batch()` - 批量分析

**流程**：
```python
输入 → 实体识别 → 适应症分析 → 生成结果 → 输出
```

---

### 2. **entity_matcher.py** - 实体识别
**职责**：识别药品和疾病实体，并与ES数据库对齐

**主要类**：`EntityRecognizer`

**工作流程**：
1. 使用LLM提取实体（药品名、疾病名）
2. 在ES中搜索匹配的标准实体
3. 返回标准化的实体信息

**输出**：`RecognizedEntities`（包含药品、疾病、上下文）

---

### 3. **knowledge_retriever.py** - 知识增强
**职责**：从ES获取完整的药品和疾病信息

**主要类**：`KnowledgeEnhancer`

**核心功能**：
- `enhance_case()` - 增强病例信息
- `get_drug_by_id()` - 获取药品详细信息
- `get_disease_by_id()` - 获取疾病详细信息
- `_gather_evidence()` - 收集临床证据

**关键点**：
- ✅ 优先读取`indications_list`（结构化疾病列表）
- ✅ 降级使用`indications`（原始文本）

---

### 4. **rule_checker.py** - 规则分析
**职责**：基于规则的超适应症判断

**主要类**：`RuleAnalyzer`

**判断维度**：
- `exact_match()` - 精确匹配（confidence=1.0）
- `synonym_match()` - 同义词匹配（confidence=0.9）
- `hierarchy_match()` - 层级匹配（confidence=0.8）
- `check_contraindications()` - 禁忌症检查

**关键原则**：
```python
# 严格精确匹配
if 疾病名 == 适应症列表中的某项:
    confidence = 1.0, is_offlabel = False
else:
    confidence = 0.0, is_offlabel = True
```

---

### 5. **llm_reasoner.py** - LLM推理
**职责**：使用大语言模型进行深度分析

**主要类**：`IndicationAnalyzer`

**工作流程**：
1. 调用`KnowledgeEnhancer`增强病例
2. 调用`RuleAnalyzer`进行规则分析
3. 构建prompt，调用LLM分析
4. 调用`ResultSynthesizer`综合结果

**LLM分析内容**：
- 适应症匹配度
- 药理机制相似性
- 临床证据支持
- 风险评估

---

### 6. **result_synthesizer.py** - 结果综合
**职责**：综合规则分析和LLM分析，生成最终判断

**主要类**：`ResultSynthesizer`

**核心逻辑**：
```python
def _determine_final_offlabel_status():
    # 严格判断：只有精确匹配才是非超适应症
    if rule_confidence == 1.0:
        return False  # 标准用药
    return True  # 超适应症
```

**输出结构**：
```json
{
  "is_offlabel": bool,           // 严格规则判断
  "analysis_details": {
    "indication_match": {...},   // 规则判断
    "open_evidence": {...},      // AI辅助
    "recommendation": {...}      // 推荐建议
  }
}
```

---

### 7. **result_generator.py** - 结果生成
**职责**：生成最终的标准化输出

**主要类**：`ResultGenerator`

**功能**：
- 整合所有分析结果
- 格式化输出
- 支持新旧结构（向后兼容）

---

### 8. **models.py** - 数据模型
**职责**：定义所有数据结构

**主要模型**：
- `RecognizedEntities` - 识别的实体
- `EnhancedCase` - 增强的病例
- `AnalysisResult` - 分析结果
- `AnalysisDetails` - 分析详情
- `OpenEvidence` - AI辅助证据

---

### 9. **prompt.py** - Prompt模板
**职责**：LLM的prompt模板

**模板类型**：
- `create_entity_recognition_prompt()` - 实体识别
- `create_indication_analysis_prompt()` - 适应症分析

---

## 数据流转

```
输入数据
   ↓
[EntityRecognizer] 实体识别
   ↓
[Case] 病例对象
   ↓
[KnowledgeEnhancer] 知识增强
   ↓
[EnhancedCase] 增强病例
   ↓
[RuleAnalyzer] 规则分析 ──┐
   ↓                      │
[LLM + Prompt] AI分析 ────┤
   ↓                      │
[ResultSynthesizer] 结果综合
   ↓
[ResultGenerator] 格式化输出
   ↓
最终结果
```

## 关键设计原则

### 1. 职责分离
- **规则判断**：严格、确定性
- **AI辅助**：灵活、参考性

### 2. 数据驱动
- 优先使用`indications_list`（结构化）
- 降级使用`indications`（文本）

### 3. 可解释性
- 完整的推理链
- 清晰的证据来源
- 明确的判断依据

### 4. 扩展性
- 模块化设计
- 标准化接口
- 易于添加新功能
