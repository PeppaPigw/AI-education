# AI-Education FastAPI 版本

## 项目说明

本项目已从 Gradio 界面迁移到 FastAPI + HTML 前后端分离架构。

## 安装依赖

```bash
pip install -r requirements.txt
```

## 配置环境变量

确保项目根目录下有 `.env` 文件，包含以下配置：

```
model_name=your_model_name
base_url=your_api_base_url
api_key=your_api_key
embedding_model=your_embedding_model
```

## 启动应用

### 方法 1: 使用启动脚本（推荐）

```bash
python main_fastapi.py
```

### 方法 2: 直接使用 uvicorn

```bash
uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000
```

## 访问应用

打开浏览器访问: http://localhost:8000

## 功能说明

### 1. 知识图谱可视化

- 左侧面板显示课程知识图谱
- 圆形辐射状布局，支持多层级节点

### 2. 学习资源管理

- 选择知识节点查看相关学习资源
- 点击 PDF 资源进行在线阅读

### 3. AI 助教 (🤖)

- 基于 RAG 的智能问答
- 支持多种语言
- 自动检索文档上下文

### 4. 随堂测验 (📝)

- 根据主题自动生成测验题
- 支持 A/B/C/D 选项
- 实时反馈正确答案
- 可基于测验结果生成学习计划

### 5. 学习计划 (🗺️)

- 根据学习目标生成个性化计划
- 按优先级排序学习任务
- 推荐相关学习材料

### 6. 知识总结 (📜)

- 自动生成结构化学习指南
- 支持基于文档的总结
- Markdown 格式输出

### 7. 资源上传 (📤)

- 支持 PDF、DOC、DOCX、PPT、PPTX 格式
- 自动转换为 PDF
- 自动索引到 RAG 数据库
- 关联到指定知识节点

## API 端点

### 聊天相关

- `POST /api/chat` - 发送聊天消息
- `GET /api/languages` - 获取支持的语言列表

### 测验相关

- `POST /api/quiz/start` - 开始测验
- `POST /api/quiz/answer` - 回答测验问题

### 学习计划相关

- `POST /api/learning-plan` - 生成学习计划
- `POST /api/learning-plan/from-quiz` - 根据测验生成学习计划

### 总结相关

- `POST /api/summary` - 生成知识总结

### 知识图谱相关

- `GET /api/knowledge-graph` - 获取知识图谱数据
- `GET /api/learning-nodes` - 获取所有学习节点
- `POST /api/node/resources` - 获取节点资源

### 文件相关

- `POST /api/upload` - 上传文件
- `GET /api/pdf/{path}` - 获取 PDF 文件

## 项目结构

```
AI-education/
├── backend/
│   ├── app.py              # FastAPI 应用主文件
│   ├── static/
│   │   ├── index.html      # 前端 HTML
│   │   ├── style.css       # 样式文件
│   │   └── app.js          # 前端 JavaScript
├── AgentModule/            # AI Agent 模块
├── LearningPlanModule/     # 学习计划模块
├── QuizModule/             # 测验模块
├── SummaryModule/          # 总结模块
├── tools/                  # 工具函数
├── data/                   # 数据目录
├── main_fastapi.py         # FastAPI 启动脚本
├── main.py                 # Gradio 启动脚本（旧版）
└── requirements.txt        # 依赖列表
```

## 技术栈

### 后端

- FastAPI - 现代高性能 Web 框架
- LangChain - LLM 应用开发框架
- Chroma - 向量数据库
- OpenAI API - LLM 服务

### 前端

- 原生 HTML/CSS/JavaScript
- Plotly.js - 知识图谱可视化
- Marked.js - Markdown 渲染

## 注意事项

1. **跨域问题**: 已配置 CORS 中间件，允许所有来源访问
2. **文件上传**: 支持多文件上传，自动转换和索引
3. **PDF 查看**: 使用 iframe 嵌入式查看
4. **RAG 检索**: 所有功能都支持 RAG 文档检索增强

## 旧版本

如需使用 Gradio 版本，运行:

```bash
python main.py
```

## 故障排除

### 1. 端口被占用

修改 `main_fastapi.py` 中的端口号

### 2. 模块导入错误

确保在项目根目录运行，或设置 PYTHONPATH

### 3. PDF 无法显示

检查文件路径是否正确，浏览器是否支持 PDF 嵌入
