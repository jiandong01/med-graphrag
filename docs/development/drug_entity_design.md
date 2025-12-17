# 基于ATC编码的药品实体设计方案

## 1. 核心思路

```
ATC药品编码-2022.csv (基准)
  ↓ 直接使用
创建标准药物实体
  ↓ 匹配（parent_id=1过滤西药）
ES药品制剂
  ↓ 关联
保留每个制剂的完整信息 → 完整实体
```

### ATC层级说明

**国内ATC（4级）**：来自ATC药品编码-2022.csv
- Level 1: XN (神经系统药物)
- Level 2: XN02 (镇痛药)
- Level 3: XN02A (阿片类)
- Level 4: XN02AX (其他阿片类药)

**WHO标准ATC（5级）**：来自ATC编码.csv（辅助）
- Level 1-5: 完整5级分类

## 2. 数据模型（保留重复记录）⭐

```python
{
  # 实体标识
  "entity_id": "X-N02AX-Q098-B002",  # 首个药品代码
  "generic_name": "曲马多",
  
  # ATC分类
  "atc_domestic": {
    "atc1": "XN", "atc1_name": "神经系统药物",
    "atc2": "XN02", "atc2_name": "镇痛药",
    "atc3": "XN02A", "atc3_name": "阿片类",
    "drug_class": "XN02AX", "drug_class_name": "其他阿片类药"
  },
  "atc_who": {
    "code": "N02AX02",
    "name_en": "tramadol",
    "name_zh": "曲马多0.3g口服"
  },
  
  # ATC注册产品（from ATC-2022）⭐ 保留所有重复记录
  "atc_registered_products": [
    {
      "drug_code": "X-N02AX-Q098-B002",
      "product_name": "盐酸曲马多注射液",
      "formulation": "注射剂",
      "spec": "2ml:0.1g",
      "approval_number": "国药准字H10800001",
      "manufacturer": "石药集团欧意药业有限公司",
      "holder": "石药集团欧意药业有限公司",
      "approval_date": "2021/9/2"
    },
    {
      "drug_code": "X-N02AX-Q098-B003",  # 另一个药品代码
      "product_name": "盐酸曲马多片",
      "formulation": "片剂",
      "spec": "50mg",
      "approval_number": "国药准字H...",
      "manufacturer": "另一家公司"
    }
    // ... 该通用名的所有ATC记录
  ],
  "atc_product_count": 15,  # ATC中该通用名的产品数
  
  # ES匹配制剂（from ES）⭐
  "es_formulations": [
    {
      "formulation_id": "xxx",
      "name": "盐酸曲马多注射液",
      "spec": "2ml:0.1g",
      "indications_list": ["术后疼痛"],
      "contraindications": [...]
    }
    // ... ES中匹配到的所有制剂
  ],
  "es_formulation_count": 56  # ES匹配到的制剂数
}
```

## 3. 实施流程

### Step 1: 加载ATC基准数据（保留所有记录）⭐

```python
atc_drugs = pd.read_csv('data/raw/drugs/ATC药品编码-2022.csv')

# 按通用名分组，保留该通用名的所有产品记录
entity_mapping = {}
for _, row in atc_drugs.iterrows():
    generic_name = row['西药药品名称'].strip()
    
    if generic_name not in entity_mapping:
        # 第一次出现，创建实体
        entity_mapping[generic_name] = {
            'entity_id': row['西药药品代码'],  # 使用第一个代码作为entity_id
            'generic_name': generic_name,
            'atc_domestic': {
                'atc1': row['ATC1'], 'atc1_name': row['ATC1名称'],
                'atc2': row['ATC2'], 'atc2_name': row['ATC2名称'],
                'atc3': row['ATC3'], 'atc3_name': row['ATC3名称'],
                'drug_class': row['药品分类'],
                'drug_class_name': row['药品分类名称']
            },
            'atc_registered_products': []  # 注册产品列表
        }
    
    # 添加该通用名的所有产品记录
    entity_mapping[generic_name]['atc_registered_products'].append({
        'drug_code': row['西药药品代码'],
        'product_name': row['产品名称'],
        'formulation': row['剂型'],
        'spec': row['规格'],
        'approval_number': row['批准文号'],
        'manufacturer': row['生产单位'],
        'holder': row['上市许可持有人']
    })

# 添加产品计数
for entity in entity_mapping.values():
    entity['atc_product_count'] = len(entity['atc_registered_products'])

print(f"实体数: {len(entity_mapping):,}")
print(f"总产品数: {len(atc_drugs):,}")
```

### Step 2: 匹配ES药品（parent_id过滤）⭐

```python
# 关键：用parent_id精确过滤中西药
for generic_name, entity_info in entity_mapping.items():
    query = {
        "query": {
            "bool": {
                "must": [
                    # 1. 名称匹配
                    {"match_phrase": {"name": generic_name}},
                    # 2. 只要西药（parent_id = "1"）⭐
                    {
                        "nested": {
                            "path": "category_hierarchy",
                            "query": {
                                "term": {
                                    "category_hierarchy.parent_id": "1                               "
                                }
                            }
                        }
                    }
                ]
            }
        }
    }
    
    result = es.search(index='drugs', body=query)
    # 处理结果...
```

### Step 3: 创建实体

```python
# 按entity_id分组，每个制剂保留完整信息
entities = []
for entity_id, drugs in groups.items():
    entity = {
        'entity_id': entity_id,
        'generic_name': ...,
        'formulations': [
            {
                'formulation_id': d['id'],
                'name': d['name'],
                'indications_list': d.get('indications_list', []),  # 保留
                'contraindications': d.get('contraindications', [])
            }
            for d in drugs
        ]
    }
    entities.append(entity)
```

### Step 4: 索引到ES

```python
# 新建drug_entities索引
es.indices.create(index='drug_entities', body=ENTITY_MAPPING)
bulk_index(es, entities)
```

## 4. 中西药过滤 ⭐

### 精确过滤方案：parent_id

**原理**：
```
category_hierarchy.parent_id = "1" → 西药 ✅
category_hierarchy.parent_id = "2" → 中药 ❌
```

**示例**：
```
曲马多：
  category_hierarchy: [
    {"parent_id": "1", "category": "抗感染药"}
  ]
  → 西药 ✅

大山楂丸：
  category_hierarchy: [
    {"parent_id": "2", "category": "消导剂"}
  ]
  → 中药 ❌ 被过滤
```

**优势**：
- ✅ 最精确（基于数据库设计）
- ✅ 最简单（单一条件）
- ✅ 最可靠（无需维护关键词）

## 5. 测试结果

### 前100条测试（parent_id过滤）

| 指标 | 值 |
|------|-----|
| ATC实体 | 52 |
| 匹配成功 | 18 |
| 匹配率 | 34.6% |
| 总制剂数 | 510 |
| 过滤中药 | 109个 ✅ |

### 过滤效果验证

- ❌ 大山楂丸（76个）→ 被过滤
- ❌ 灵芝胶囊（32个）→ 被过滤
- ❌ 止血宝颗粒（1个）→ 被过滤
- ✅ 曲马多（56个）→ 保留
- ✅ 氟康唑（100个）→ 保留

## 6. FAQ

### Q1: ATC层级？
国内4级为主，WHO 5级为辅

### Q2: WHO信息如何处理？
保留原始字段，不额外提取

### Q3: 制剂适应症如何处理？
每个制剂保留自己的，不聚合

### Q4: 如何过滤中药？⭐
使用`category_hierarchy.parent_id = "1"`精确过滤

## 7. 实施计划

- Phase 1: 开发Pipeline（2天）
- Phase 2: 数据匹配（1天）  
- Phase 3: 创建索引（0.5天）
- Phase 4: 人工审核（1-2天）

## 8. 核心优势

1. **parent_id过滤**：最精确的中西药区分
2. **反向ES查询**：简单高效
3. **信息完整**：每个制剂保留完整信息
4. **零风险**：原索引不动

---

**文档**: v3.0（parent_id过滤版）  
**状态**: ✅ 测试验证完成，可实施
