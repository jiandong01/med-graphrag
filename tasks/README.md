# 疾病提取任务

用于从 Elasticsearch drugs 索引中批量提取疾病实体的任务脚本。

## 📋 功能特性

- ✅ **分批处理**：支持自定义批次大小，避免一次性处理所有数据
- ✅ **进度跟踪**：实时显示处理进度和统计信息
- ✅ **断点续传**：支持中断后继续执行，不会丢失已处理的数据
- ✅ **结果保存**：每批结果独立保存，支持增量处理
- ✅ **错误处理**：记录失败的提取，不影响整体进度
- ✅ **状态查询**：随时查看当前任务进度

## 🚀 快速开始

### 1. 环境准备

确保已安装依赖并配置环境变量：

```bash
# 检查环境变量
cat .env | grep DEEPSEEK_API_KEY

# 如果没有，需要添加
echo "DEEPSEEK_API_KEY=your_key_here" >> .env
```

### 2. 查看当前状态

```bash
python tasks/extract_diseases.py --status
```

### 3. 开始提取

**小规模测试（处理前100个药品）**：
```bash
python tasks/extract_diseases.py --batch-size 10 --start-from 0
```

**正常处理（推荐）**：
```bash
# 每批处理100个药品
python tasks/extract_diseases.py --batch-size 100
```

**大规模处理（更快）**：
```bash
# 每批处理500个药品
python tasks/extract_diseases.py --batch-size 500
```

### 4. 中断后继续

```bash
python tasks/extract_diseases.py --resume
```

### 5. 合并结果

```bash
# 提取完成后，合并所有批次
python tasks/extract_diseases.py --merge-only
```

## 📊 数据规模

| 项目 | 数量 | 说明 |
|------|------|------|
| 药品总数 | 86,345 | drugs 索引中的药品 |
| 有适应症的 | 85,923 | 需要处理的药品 |
| 预估适应症 | ~200,000 | 平均每药品2-3条 |
| 预期疾病数 | 5,000-10,000 | 去重后的独特疾病 |

## ⏱️ 时间和成本估算

### 按批次大小

| 批次大小 | 批次数 | 预估时间 | API调用数 | 预估成本 |
|---------|-------|---------|-----------|---------|
| 10 | 8,592 | 4-5天 | ~200,000 | $8-12 |
| 100 | 859 | 2-3天 | ~200,000 | $8-12 |
| 500 | 172 | 1-2天 | ~200,000 | $8-12 |
| 1000 | 86 | 18-24小时 | ~200,000 | $8-12 |

**说明**：
- 时间基于每个适应症2-3秒的处理时间
- 成本基于 DeepSeek Chat 模型
- 包含 0.1 秒的API限流延迟

### 推荐策略

**方案A：稳妥渐进**（推荐）
```bash
# 1. 先测试 10 个
python tasks/extract_diseases.py --batch-size 10 --start-from 0

# 2. 检查结果
ls -lh tasks/output/diseases/

# 3. 确认无误后，用 batch-size=100 继续
python tasks/extract_diseases.py --batch-size 100 --resume
```

**方案B：快速完成**
```bash
# 直接用大批次，适合有充足API额度的情况
python tasks/extract_diseases.py --batch-size 500

# 在后台运行
nohup python tasks/extract_diseases.py --batch-size 500 > tasks/logs/extraction.log 2>&1 &

# 查看进度
tail -f tasks/logs/extraction.log
```

**方案C：分多天处理**
```bash
# 每天处理 10,000 个药品 (100个批次)
python tasks/extract_diseases.py --batch-size 100 --start-from 0

# 第二天继续
python tasks/extract_diseases.py --resume
```

## 📁 输出结构

```
tasks/
├── extract_diseases.py          # 主脚本
├── README.md                     # 本文档
├── logs/                         # 日志目录
│   └── disease_extraction_*.log  # 运行日志
├── state/                        # 状态目录
│   └── extraction_state.json     # 任务状态（断点续传用）
└── output/                       # 输出目录
    ├── diseases/                 # 分批结果
    │   ├── batch_00000.json     # 第1批
    │   ├── batch_00001.json     # 第2批
    │   └── ...
    └── all_diseases.json         # 合并后的完整结果
```

## 📄 文件格式

### batch_XXXXX.json（批次结果）

```json
{
  "batch_number": 0,
  "start_time": "2025-10-26T18:00:00",
  "end_time": "2025-10-26T18:05:00",
  "drugs_count": 100,
  "success_count": 250,
  "failure_count": 10,
  "extractions": [
    {
      "id": "abc123...",
      "drug_id": "...",
      "drug_name": "阿司匹林片",
      "indication_text": "用于发热、头痛...",
      "diseases": [
        {
          "name": "发热",
          "type": "disease",
          "sub_diseases": [],
          "related_diseases": [],
          "confidence_score": 0.9
        }
      ],
      "extraction_time": "2025-10-26T18:01:23",
      "confidence": 0.95
    }
  ]
}
```

### extraction_state.json（任务状态）

```json
{
  "start_time": "2025-10-26T18:00:00",
  "processed_count": 1500,
  "total_count": 85923,
  "processed_drug_ids": ["id1", "id2", ...],
  "current_batch": 15,
  "success_count": 3500,
  "failure_count": 50,
  "last_updated": "2025-10-26T18:30:00"
}
```

## 🔧 命令行选项

```bash
python tasks/extract_diseases.py [选项]

选项:
  --batch-size SIZE      每批处理的药品数量 (默认: 100)
  --start-from BATCH     从指定批次开始 (0-based)
  --resume              从上次中断处继续
  --merge-only          只合并已有批次结果，不提取
  --status              显示当前任务状态
  --output-dir DIR      输出目录 (默认: tasks/output/diseases)
  -h, --help            显示帮助信息
```

## 📈 监控进度

### 方法1：使用 --status 命令

```bash
# 在另一个终端查看状态
python tasks/extract_diseases.py --status

# 输出示例:
============================================================
任务状态
============================================================
总药品数:     85,923
已处理:       15,000
当前批次:     150
成功提取:     35,000
失败次数:     250
完成进度:     17.45%
最后更新:     2025-10-26T18:30:00
============================================================
```

### 方法2：查看日志

```bash
# 实时查看日志
tail -f tasks/logs/disease_extraction_*.log

# 查看最近的日志
tail -100 tasks/logs/disease_extraction_*.log
```

### 方法3：查看输出文件

```bash
# 查看已完成的批次数
ls tasks/output/diseases/batch_*.json | wc -l

# 查看最新批次
ls -lt tasks/output/diseases/batch_*.json | head -5
```

## ⚠️ 注意事项

### 1. API 限流

- 每个适应症提取后会延迟 0.1 秒
- 如遇到 429 错误，脚本会记录失败并继续
- 可以调整 `time.sleep(0.1)` 的值

### 2. 中断处理

- 使用 Ctrl+C 可以安全中断任务
- 状态会自动保存到 `extraction_state.json`
- 下次使用 `--resume` 参数继续

### 3. 磁盘空间

- 每个批次文件约 50-200 KB
- 总共需要约 50-100 MB 空间
- 确保有足够的磁盘空间

### 4. API 密钥

```bash
# 检查 API 密钥是否配置
python -c "import os; from app.src.utils import load_env; load_env(); print('API Key配置:', 'OK' if os.getenv('DEEPSEEK_API_KEY') else 'MISSING')"
```

## 🔄 完整工作流程

### 阶段1：小规模测试

```bash
# 1. 测试提取10个药品
python tasks/extract_diseases.py --batch-size 10 --start-from 0

# 2. 检查结果
cat tasks/output/diseases/batch_00000.json | python3 -m json.tool | head -50

# 3. 如果结果正常，继续
```

### 阶段2：批量提取

```bash
# 方式A：前台运行（可以看到进度）
python tasks/extract_diseases.py --batch-size 100

# 方式B：后台运行（长时间任务）
nohup python tasks/extract_diseases.py --batch-size 100 > tasks/logs/run.log 2>&1 &

# 获取进程ID
echo $!

# 查看进度
python tasks/extract_diseases.py --status
```

### 阶段3：合并和索引

```bash
# 1. 合并所有批次结果
python tasks/extract_diseases.py --merge-only

# 2. 处理并索引到 Elasticsearch
python -c "
import sys
sys.path.append('.')
from app.src.indication.diseases import DiseaseManager
import json

# 读取合并结果
with open('tasks/output/all_diseases.json', 'r') as f:
    extractions = json.load(f)

# 处理疾病数据
manager = DiseaseManager()
diseases = []

# 从提取结果构建疾病文档
disease_dict = {}
for extraction in extractions:
    for disease in extraction.get('diseases', []):
        disease_name = disease['name']
        if disease_name not in disease_dict:
            disease_dict[disease_name] = {
                'id': f'disease_{len(disease_dict) + 1}',
                'name': disease_name,
                'type': disease.get('type', 'disease'),
                'sub_diseases': disease.get('sub_diseases', []),
                'related_diseases': disease.get('related_diseases', []),
                'confidence_score': disease.get('confidence_score', 0.9),
                'sources': [],
                'mention_count': 0
            }
        
        # 添加来源
        disease_dict[disease_name]['sources'].append({
            'drug_id': extraction['drug_id'],
            'extraction_time': extraction['extraction_time'],
            'confidence': extraction.get('confidence', 0.95)
        })
        disease_dict[disease_name]['mention_count'] += 1

diseases = list(disease_dict.values())

# 添加时间戳
from datetime import datetime
for disease in diseases:
    if 'first_seen' not in disease:
        disease['first_seen'] = disease['sources'][0]['extraction_time']
    disease['last_updated'] = datetime.now().isoformat()

# 创建索引并导入
manager.create_index(clear_existing=True)
manager.index_diseases(diseases)

print(f'成功索引 {len(diseases)} 个疾病')
"
```

## 🐛 故障排查

### 问题1：API 密钥错误

```bash
# 症状
AuthenticationError: Incorrect API key provided

# 解决
echo "DEEPSEEK_API_KEY=your_actual_key" >> .env
```

### 问题2：Elasticsearch 连接失败

```bash
# 症状
ConnectionError: Connection refused

# 解决
docker ps | grep elasticsearch
docker compose up -d  # 如果没有运行
```

### 问题3：内存不足

```bash
# 症状
MemoryError

# 解决：减小批次大小
python tasks/extract_diseases.py --batch-size 50 --resume
```

### 问题4：处理卡住

```bash
# 查看是否在等待API响应
tail -f tasks/logs/disease_extraction_*.log

# 如果长时间无响应，可能是网络问题
# Ctrl+C 中断，然后 --resume 继续
```

## 📊 监控脚本

创建一个简单的监控脚本：

```bash
#!/bin/bash
# tasks/monitor.sh

while true; do
    clear
    echo "===== 疾病提取任务监控 ====="
    date
    echo ""
    
    python tasks/extract_diseases.py --status
    
    echo "最近日志:"
    tail -20 tasks/logs/disease_extraction_*.log
    
    sleep 30
done
```

使用：
```bash
chmod +x tasks/monitor.sh
./tasks/monitor.sh
```

## 🔄 完整示例

### 场景：周末运行完整提取

**周五晚上**：
```bash
# 启动任务（批次大小100，预计2-3天）
nohup python tasks/extract_diseases.py --batch-size 100 > tasks/logs/weekend_run.log 2>&1 &

# 记录进程ID
echo $! > tasks/extraction.pid
```

**周六检查**：
```bash
# 检查进度
python tasks/extract_diseases.py --status

# 查看日志
tail -50 tasks/logs/weekend_run.log
```

**周日完成**：
```bash
# 检查是否完成
python tasks/extract_diseases.py --status

# 合并结果
python tasks/extract_diseases.py --merge-only

# 索引到 Elasticsearch（见上面的Python代码）
```

## 🎯 最佳实践

### 1. 渐进式处理

```bash
# 第1阶段：测试（10个药品）
python tasks/extract_diseases.py --batch-size 10

# 第2阶段：小规模（1,000个药品）
python tasks/extract_diseases.py --batch-size 100 --resume

# 第3阶段：全量处理
python tasks/extract_diseases.py --batch-size 100 --resume
# 让它运行到完成
```

### 2. 定期检查

```bash
# 每小时检查一次进度
watch -n 3600 'python tasks/extract_diseases.py --status'
```

### 3. 备份结果

```bash
# 定期备份已完成的批次
tar czf tasks_backup_$(date +%Y%m%d).tar.gz tasks/output/ tasks/state/
```

## 📝 输出示例

### 提取结果示例

```json
{
  "id": "abc123def456",
  "drug_id": "drug_001",
  "drug_name": "阿莫西林胶囊",
  "indication_text": "用于化脓性链球菌引起的急性咽炎、急性扁桃体炎",
  "diseases": [
    {
      "name": "急性咽炎",
      "type": "disease",
      "sub_diseases": [],
      "related_diseases": [
        {
          "name": "化脓性链球菌",
          "attributes": {},
          "relationship": "cause"
        }
      ],
      "confidence_score": 0.95
    },
    {
      "name": "急性扁桃体炎",
      "type": "disease",
      "sub_diseases": [],
      "related_diseases": [
        {
          "name": "化脓性链球菌",
          "attributes": {},
          "relationship": "cause"
        }
      ],
      "confidence_score": 0.95
    }
  ],
  "extraction_time": "2025-10-26T18:30:00",
  "confidence": 0.95
}
```

## 🆘 获取帮助

```bash
# 查看完整帮助
python tasks/extract_diseases.py --help

# 查看日志
ls -lh tasks/logs/

# 查看状态文件
cat tasks/state/extraction_state.json | python3 -m json.tool
```

## 🎓 提示

1. **首次运行前**先用小批次测试，确保配置正确
2. **长时间运行**建议在 screen 或 tmux 会话中执行
3. **定期检查**进度和日志，及时发现问题
4. **保存备份**，完成一定数量后备份结果文件
5. **合并前检查**确保所有批次都成功完成

## 📞 支持

如有问题，请查看：
- 日志文件：`tasks/logs/disease_extraction_*.log`
- 状态文件：`tasks/state/extraction_state.json`
- 项目文档：`docs/`
