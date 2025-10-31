# 快速启动指南

## 前置要求

确保系统已安装以下软件：

- Node.js >= 18.0.0
- pnpm >= 8.0.0
- Python >= 3.10
- Elasticsearch >= 8.0

## 启动步骤

### 1. 安装前端依赖

```bash
cd app/ui
pnpm install
```

### 2. 启动后端服务

在项目根目录打开新的终端窗口：

```bash
# 确保Elasticsearch正在运行
docker-compose up -d elasticsearch

# 启动FastAPI后端
python -m app.api
```

后端将在 http://localhost:8000 启动。

### 3. 启动前端开发服务器

在 `app/ui` 目录：

```bash
pnpm dev
```

前端将在 http://localhost:3000 启动。

### 4. 访问应用

在浏览器中打开: http://localhost:3000

## 测试系统

### 测试案例1: 标准用药
- 药品: 美托洛尔
- 疾病: 高血压
- 预期: 符合说明书用药

### 测试案例2: 合理超适应症
- 药品: 西地那非
- 疾病: 特发性肺纤维化伴肺动脉高压
- 预期: 合理超说明书用药

### 测试案例3: 不合理超适应症
- 药品: 阿司匹林
- 疾病: 急性脑出血
- 预期: 不建议使用（存在禁忌）

## 故障排查

### 前端无法启动
- 检查Node.js版本: `node --version`
- 检查pnpm安装: `pnpm --version`
- 清除缓存: `pnpm store prune && pnpm install`

### 后端连接失败
- 检查后端是否运行: `curl http://localhost:8000/docs`
- 检查后端日志
- 确认Elasticsearch服务正常

### 组件显示异常
- 清除浏览器缓存
- 检查浏览器控制台错误
- 确认shadcn/ui组件已正确安装

## 开发提示

1. **热重载**: 修改代码后，开发服务器会自动重新加载
2. **TypeScript检查**: 使用 `pnpm build` 进行完整的类型检查
3. **样式调试**: 使用浏览器开发者工具检查Tailwind CSS类
4. **API调试**: 检查浏览器Network标签查看API请求

## 生产部署

### 构建前端

```bash
cd app/ui
pnpm build
```

### 启动生产服务器

```bash
pnpm start
```

或使用Nginx等反向代理服务器托管构建产物（`.next`目录）。

## 环境变量

创建 `.env.local` 文件配置环境变量：

```bash
# API后端地址（如果不在同一服务器）
NEXT_PUBLIC_API_URL=http://localhost:8000
```

注意：当前API路由使用相对路径，如需修改后端地址，需要更新 `app/api/analyze/route.ts` 文件。
