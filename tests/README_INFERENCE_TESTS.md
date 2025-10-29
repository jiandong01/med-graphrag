# Inference模块测试文档

## 概述

本文档介绍inference模块的测试套件，包含4个主要测试文件，覆盖从底层组件到端到端工作流程的完整测试。

## 测试文件列表

### 1. test_inference_knowledge_retriever.py
**知识增强模块测试**

测试 `KnowledgeEnhancer` 类的功能，包括：
- 根据ID和名称获取药品/疾病信息
- 病例信息增强
- 证据收集（临床指南、专家共识、研究文献）
- 空实体和多匹配结果的处理

**测试用例数量：** 9个

**关键测试：**
```bash
pytest tests/test_inference_knowledge_retriever.py -v
```

### 2. test_inference_rule_checker.py
**规则分析模块测试**

测试 `RuleAnalyzer` 类的功能，包括：
- 精确匹配检查
- 禁忌症检查
- 大小写不敏感匹配
- 同义词和层级匹配（占位测试）
- 置信度评估
- 边界条件处理

**测试用例数量：** 14个

**关键测试：**
```bash
pytest tests/test_inference_rule_checker.py -v
```

### 3. test_inference_result_synthesizer.py
**结果综合模块测试**

测试 `ResultSynthesizer` 类的功能，包括：
- 标准用药和超适应症用药的结果综合
- 加权得分计算
- 最终超适应症状态判定
- 证据整合
- 建议生成（建议使用/谨慎使用/不建议使用）
- 临床指南和研究文献支持度评估
- 风险评估
- 元数据生成

**测试用例数量：** 12个

**关键测试：**
```bash
pytest tests/test_inference_result_synthesizer.py -v
```

### 4. test_inference_engine.py
**推理引擎端到端测试**

测试 `InferenceEngine` 类的完整工作流程，包括：
- 推理引擎初始化
- 标准用药和超适应症案例分析
- 自定义输入处理
- 批量分析
- 错误处理
- 结果结构验证
- 置信度范围检查
- 证据综合验证
- 建议质量评估
- 性能测试
- 向后兼容性测试
- 完整端到端工作流程

**测试用例数量：** 17个

**关键测试：**
```bash
pytest tests/test_inference_engine.py -v
```

## 运行所有测试

### 运行所有inference测试
```bash
pytest tests/test_inference_*.py -v
```

### 运行特定模块测试
```bash
# 知识增强模块
pytest tests/test_inference_knowledge_retriever.py -v -s

# 规则分析模块
pytest tests/test_inference_rule_checker.py -v -s

# 结果综合模块
pytest tests/test_inference_result_synthesizer.py -v -s

# 推理引擎端到端
pytest tests/test_inference_engine.py -v -s
```

### 运行单个测试用例
```bash
# 示例：测试标准用药案例
pytest tests/test_inference_engine.py::test_analyze_standard_case -v -s
```

## 测试覆盖率

各模块测试覆盖情况：

| 模块 | 测试文件 | 测试用例数 | 覆盖度 |
|------|---------|-----------|--------|
| KnowledgeEnhancer | test_inference_knowledge_retriever.py | 9 | 高 |
| RuleAnalyzer | test_inference_rule_checker.py | 14 | 高 |
| ResultSynthesizer | test_inference_result_synthesizer.py | 12 | 高 |
| InferenceEngine | test_inference_engine.py | 17 | 高 |
| **总计** | **4个文件** | **52个测试** | **高** |

## 测试数据

测试使用以下数据文件：
- `tests/data/input/entity_recognition_input_1.json` - 标准用药案例（阿莫西林治疗急性咽炎）
- `tests/data/input/entity_recognition_input_2.json` - 超适应症案例（西地那非治疗肺动脉高压）
- `tests/data/input/entity_recognition_input_error.json` - 错误处理测试

## 前置条件

运行测试前需要：

1. **环境配置**
   ```bash
   cp .env.example .env
   # 配置必要的API密钥
   ```

2. **Elasticsearch服务**
   ```bash
   make es up
   # 确保Elasticsearch运行在 localhost:9200
   ```

3. **索引数据**
   ```bash
   # 确保已经运行pipeline创建药品和疾病索引
   # drugs索引和diseases索引必须存在
   ```

4. **安装依赖**
   ```bash
   pip install -r requirements.txt
   # 或
   uv sync
   ```

## 测试特点

### 1. 全面的功能覆盖
- 从单元测试到集成测试
- 覆盖正常流程和异常处理
- 包含边界条件和特殊场景

### 2. 详细的输出信息
- 使用 `capsys` fixture 捕获和显示输出
- 每个测试都有清晰的打印信息
- 便于调试和理解测试过程

### 3. 真实场景模拟
- 使用实际的医疗案例
- 模拟真实的数据流
- 验证完整的业务逻辑

### 4. 性能验证
- 包含响应时间测试
- 验证系统性能在合理范围
- 确保用户体验良好

## 常见问题

### Q1: 测试失败怎么办？

**A:** 首先检查：
1. Elasticsearch服务是否正常运行
2. 环境变量是否正确配置
3. 索引数据是否已创建
4. 依赖包是否完整安装

### Q2: 如何调试单个测试？

**A:** 使用 `-s` 参数显示打印输出：
```bash
pytest tests/test_inference_engine.py::test_analyze_standard_case -v -s
```

### Q3: 测试运行很慢怎么办？

**A:** 
- 使用 `-k` 参数运行特定测试
- 优化Elasticsearch配置
- 确保网络连接正常（LLM API调用）

### Q4: 如何跳过需要外部服务的测试？

**A:** 使用pytest的标记功能：
```bash
# 在测试函数上添加 @pytest.mark.skipif 装饰器
# 或使用 -m 参数过滤测试
```

## 持续改进

测试套件会持续改进，包括：
- [ ] 增加更多边界条件测试
- [ ] 添加压力测试和并发测试
- [ ] 完善错误恢复测试
- [ ] 增加模拟（mock）以减少外部依赖
- [ ] 添加测试覆盖率报告

## 贡献指南

添加新测试时请遵循：
1. 使用描述性的测试函数名
2. 添加清晰的文档字符串
3. 使用 `capsys` 提供详细输出
4. 包含断言验证预期结果
5. 处理可能的异常情况

## 联系方式

如有问题或建议，请联系开发团队或提交Issue。

---

**最后更新：** 2025-10-29
**维护者：** Med-GraphRAG开发团队
