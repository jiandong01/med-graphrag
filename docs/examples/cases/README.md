# 超适应症用药分析案例

本目录包含三个典型的超适应症用药分析案例，展示了系统的分析流程和判断逻辑。

## 案例结构

### 案例1：标准适应症用药 (case1_standard)
- 阿莫西林用于急性链球菌性咽炎
- 展示了标准适应症的判断流程

### 案例2：合理的超适应症用药 (case2_reasonable_offlabel)
- 西地那非用于继发性肺动脉高压
- 展示了基于疾病机制相似性和临床证据的分析过程

### 案例3：不推荐的超适应症用药 (case3_unreasonable_offlabel)
- 奥氮平用于轻度焦虑症
- 展示了风险评估和替代方案推荐

## 文件说明

每个案例目录包含以下文件：
- `input.json`: 原始病例数据
- `entity_recognition.json`: 实体识别和标准化结果
- `indication_analysis.json`/`similarity_analysis.json`/`risk_analysis.json`: 分析过程
- `final_result.json`: 最终分析结果

## 数据流程

1. 输入数据 → 实体识别和标准化
2. 根据不同情况进行分析：
   - 标准适应症：直接匹配分析
   - 合理超适应症：机制相似性和证据分析
   - 不推荐超适应症：风险评估和替代方案
3. 生成最终分析报告
