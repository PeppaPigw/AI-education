# 调试步骤

## 1. 启动服务

```bash
./start.sh
```

## 2. 打开浏览器

访问 http://localhost:8000

## 3. 打开开发者工具

按 F12 或右键 -> 检查

## 4. 查看 Console 标签

应该看到以下日志：

- "DOM loaded, starting initialization..."
- "Loading knowledge graph..."
- "Knowledge graph data loaded: ..."
- "Initializing graph with data: ..."
- "Container dimensions: ..."
- "Graph initialized successfully"
- "Initialization complete"

## 5. 如果看到错误

### 错误: "Failed to load graph.js"

- 检查文件是否存在: backend/static/graph.js
- 检查服务器是否正确启动

### 错误: "initializeGraph function not found"

- graph.js 没有正确加载
- 检查 script 标签顺序

### 错误: "d3 is not defined"

- D3.js CDN 没有加载
- 检查网络连接

### 错误: API 请求失败

- 检查后端服务是否运行
- 访问 http://localhost:8000/api/knowledge-graph 测试 API

## 6. 测试页面

访问 http://localhost:8000/static/test.html
应该看到一个蓝色圆圈，表示 D3.js 正常工作

## 7. 常见问题

### 图谱不显示

1. 检查#knowledge-graph 元素是否有宽高
2. 在 Console 中运行: `document.getElementById('knowledge-graph').clientWidth`
3. 如果返回 0，说明 CSS 有问题

### 资源列表不显示

1. 点击节点后检查 Console
2. 查看是否有 handleNodeClick 调用日志
3. 检查节点是否有 resource_path 数据
