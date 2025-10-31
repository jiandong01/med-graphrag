# 医疗超适应症分析系统 - Web UI

基于 Next.js 16 + React 19 的医疗超适应症智能分析系统前端界面。

## 技术栈

- **框架**: Next.js 16 + React 19
- **UI库**: shadcn/ui (new-york风格)
- **样式**: Tailwind CSS 4
- **语言**: TypeScript
- **图标**: lucide-react

## 项目结构

```
app/ui/
├── app/
│   ├── api/
│   │   └── analyze/
│   │       └── route.ts          # API路由，调用Python后端
│   ├── page.tsx                   # 主页面
│   ├── layout.tsx                 # 布局组件
│   └── globals.css                # 全局样式
├── components/
│   ├── ui/                        # shadcn/ui基础组件
│   │   ├── button.tsx
│   │   ├── input.tsx
│   │   ├── label.tsx
│   │   ├── card.tsx
│   │   ├── badge.tsx
│   │   └── collapsible.tsx
│   └── analysis/                  # 分析展示组件
│       ├── entity-recognition-card.tsx      # 实体识别卡片
│       ├── indication-analysis-card.tsx     # 规则判断卡片
│       ├── ai-analysis-card.tsx             # AI辅助分析卡片
│       └── final-result-card.tsx            # 最终结果卡片
├── lib/
│   ├── types.ts                   # TypeScript类型定义
│   └── utils.ts                   # 工具函数
└── docs/                          # 参考文档
    ├── ai-ui-reasoning.md
    ├── ai-ui-task.md
    └── ai-ui-tool.md
```

## 功能特性

### 1. 输入表单
- 药品名称输入
- 疾病名称输入
- 可选的临床描述
- 表单验证和加载状态

### 2. 分析流程展示
采用可折叠卡片展示四个分析步骤：

#### 步骤1: 实体识别
- 展示识别的药品信息（名称、规格、分类、适应症）
- 展示识别的疾病信息（名称、严重程度、疾病组成）
- 显示置信度评分

#### 步骤2: 规则判断
- 适应症匹配结果（完全匹配/部分匹配/不匹配）
- 匹配的适应症列表
- 禁忌症检查结果
- 详细说明和解释

#### 步骤3: AI辅助分析
- 相似度分析（机制相似度、临床相似度）
- 证据分析（药品说明书、临床指南、专家共识）
- 风险评估（获益因素、风险因素、获益风险比）

#### 步骤4: 最终判断
- 用药类别判断（标准用药/合理超说明书/不建议）
- 综合评分展示
- 临床建议
- 监测计划（疗效指标、安全性监测、随访计划、调整标准）

### 3. 交互特性
- 响应式设计，支持各种屏幕尺寸
- 可折叠/展开的详细信息
- 清晰的视觉反馈（加载状态、成功/失败状态）
- 错误提示
- 会话信息展示

## 开发指南

### 安装依赖

```bash
cd app/ui
pnpm install
```

### 开发模式

```bash
pnpm dev
```

应用将在 http://localhost:3000 启动。

### 构建生产版本

```bash
pnpm build
pnpm start
```

### 代码检查

```bash
pnpm lint
```

## API集成

前端通过 `/api/analyze` 路由与Python后端通信。

### 前端请求格式
前端发送简化的请求：
```json
{
  "drug_name": "美托洛尔",
  "disease_name": "心力衰竭",
  "description": "患者诊断为心力衰竭，拟使用美托洛尔治疗"
}
```

### 后端API格式
Next.js API路由会自动转换为后端期望的格式：
```json
{
  "patient": {
    "diagnosis": "心力衰竭",
    "medical_history": "患者诊断为心力衰竭，拟使用美托洛尔治疗"
  },
  "prescription": {
    "drug_name": "美托洛尔"
  },
  "clinical_context": "患者诊断为心力衰竭，拟使用美托洛尔治疗"
}
```

### 响应格式
```json
{
  "success": true,
  "data": {
    "entity_recognition": {...},
    "indication_analysis": {...},
    "analysis": {...},
    "final_result": {...}
  },
  "timestamp": "2025-01-01T00:00:00"
}
```

后端服务地址配置在 `app/api/analyze/route.ts` 中，默认为 `http://localhost:8000`。

## 使用说明

### 启动完整系统

1. **启动Python后端** (在项目根目录):
```bash
# 确保Elasticsearch已启动
make run-api  # 或者 python -m app.api
```

2. **启动前端** (在app/ui目录):
```bash
pnpm dev
```

3. **访问应用**:
打开浏览器访问 http://localhost:3000

### 使用流程

1. 在表单中输入药品名称和疾病名称
2. （可选）输入临床描述以获得更准确的分析
3. 点击"开始分析"按钮
4. 系统将展示完整的分析流程和结果
5. 查看各个步骤的详细信息
6. 根据最终判断和建议做出临床决策

## 注意事项

1. 确保Python后端服务正在运行（默认端口8000）
2. 确保Elasticsearch服务正常（后端依赖）
3. 首次访问时加载可能较慢，请耐心等待
4. 建议使用Chrome或Edge等现代浏览器以获得最佳体验

## 后续改进方向

- [ ] 添加历史分析记录查询
- [ ] 支持批量分析
- [ ] 导出分析报告（PDF/Word）
- [ ] 添加用户认证和权限管理
- [ ] 优化移动端显示
- [ ] 添加数据可视化图表
- [ ] 支持自定义分析参数

## 许可证

本项目仅供研究和学习使用。
