# Scripts 脚本说明

med-graphrag评估和分析工具集。

## 脚本列表

### 1. prepare_evaluation_dataset.py
**用途**：准备评估数据集

**功能**：
- 从完整CSV筛选"是"和"否"数据
- 随机抽取50条是+50条否（可配置）
- 输出CSV和JSON格式

**使用**：
```bash
python scripts/prepare_evaluation_dataset.py
```

**输出**：
- `evaluation_dataset.csv` - 100条评估数据
- `evaluation_dataset.json` - JSON格式

**配置**：`config.yaml → inference.evaluation`

---

### 2. analyze_evaluation_dataset.py
**用途**：分析评估数据集（推荐）

**功能**：
- 读取evaluation_dataset.csv
- 调用推理引擎分析每条数据
- 输出JSONL格式结果

**使用**：
```bash
python scripts/analyze_evaluation_dataset.py

# 测试3条
# 输入: 3
# 输入: yes
```

**输出**：
- `evaluation_results.jsonl` - 分析结果（每行一个JSON）

**配置**：使用`config.yaml → inference.skip_entity_recognition`

**性能**：
- 快速模式：~20秒/条
- 100条：~33分钟

---

### 3. analyze_clinical_cases.py
**用途**：通用分析脚本

**功能**：
- 支持自定义输入文件
- 支持全量数据分析
- 灵活的参数配置

**使用**：
```bash
# 默认：使用evaluation_dataset.csv
python scripts/analyze_clinical_cases.py

# 使用完整数据集（5497条）
python scripts/analyze_clinical_cases.py --use-full-dataset

# 自定义输入
python scripts/analyze_clinical_cases.py --input your_file.csv
```

**参数**：
- `--input`: 输入文件
- `--output`: 输出文件
- `--use-full-dataset`: 使用完整数据

---

### 4. evaluate_results.py
**用途**：评估分析结果

**功能**：
- 计算混淆矩阵
- 计算Accuracy/Precision/Recall/F1
- 计算AUC-ROC
- 绘制ROC曲线图
- 错误案例分析

**使用**：
```bash
python scripts/evaluate_results.py --input evaluation_results.jsonl

# 不绘制ROC图
python scripts/evaluate_results.py --no-plot
```

**输出**：
- 控制台：评估指标
- `evaluation_report.json` - 完整报告
- `roc_curve.png` - ROC曲线图

**依赖**：
- numpy：必需
- matplotlib：可选（绘图）

---

## 完整工作流

### 标准流程

```bash
# 1. 准备数据集（100条）
python scripts/prepare_evaluation_dataset.py

# 2. 分析病例
python scripts/analyze_evaluation_dataset.py

# 3. 评估结果
python scripts/evaluate_results.py --input evaluation_results.jsonl
```

### 测试流程

```bash
# 1. 准备数据
python scripts/prepare_evaluation_dataset.py

# 2. 测试3条
python scripts/analyze_evaluation_dataset.py
# 输入: 3
# 输入: yes

# 3. 评估
python scripts/evaluate_results.py --input evaluation_results.jsonl
```

---

## 配置说明

### config.yaml

```yaml
inference:
  skip_entity_recognition: true  # 快速模式
  
  evaluation:
    sample_size_yes: 50  # 抽取"是"的数量
    sample_size_no: 50   # 抽取"否"的数量
    random_seed: 42      # 随机种子
```

---

## 输出文件

### 数据文件
```
data/raw/clinical_cases/
├── evaluation_dataset.csv      # 评估数据集
├── evaluation_dataset.json     # JSON格式
├── evaluation_results.jsonl    # 分析结果
├── evaluation_report.json      # 评估报告
└── roc_curve.png               # ROC曲线图
```

---

## 评估指标

| 指标 | 说明 |
|------|------|
| Accuracy | 总体准确率 |
| Precision | 查准率 |
| Recall | 查全率 |
| F1-Score | 综合指标 |
| AUC | ROC曲线下面积 |

---

## 依赖安装

```bash
# 必需
pip install numpy

# 可选（绘图）
pip install matplotlib
```

---

## 快速参考

### 最小化测试
```bash
# 3条数据，验证功能
python scripts/analyze_evaluation_dataset.py  # 输入3
python scripts/evaluate_results.py --input evaluation_results.jsonl
```

### 完整评估
```bash
# 100条数据，完整评估
python scripts/prepare_evaluation_dataset.py
python scripts/analyze_evaluation_dataset.py  # 回车
python scripts/evaluate_results.py --input evaluation_results.jsonl
```

---

## 更多信息

- 配置指南：`docs/CONFIG_GUIDE.md`
- AUC-ROC说明：`docs/AUC_ROC_GUIDE.md`
- 优化总结：`docs/OPTIMIZATION_SUMMARY.md`
