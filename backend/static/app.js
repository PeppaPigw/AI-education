// API 基础 URL
const API_BASE = "";

// 全局状态
let currentNode = null;
let currentPdfPath = null;
let chatHistory = [];
let quizState = null;
let knowledgeGraphData = null;

// 初始化
document.addEventListener("DOMContentLoaded", async () => {
  await loadLanguages();
  await loadKnowledgeGraph();
  await loadLearningNodes();
  setupEventListeners();
});

// 加载语言列表
async function loadLanguages() {
  try {
    const response = await fetch(`${API_BASE}/api/languages`);
    const languages = await response.json();
    const select = document.getElementById("lang-select");
    select.innerHTML = languages
      .map((lang) => `<option>${lang}</option>`)
      .join("");
  } catch (error) {
    console.error("Error loading languages:", error);
  }
}

// 加载知识图谱
async function loadKnowledgeGraph() {
  try {
    const response = await fetch(`${API_BASE}/api/knowledge-graph`);
    knowledgeGraphData = await response.json();
    renderKnowledgeGraph(knowledgeGraphData);
  } catch (error) {
    console.error("Error loading knowledge graph:", error);
  }
}

// 渲染知识图谱
function renderKnowledgeGraph(data) {
  if (!data || !data.root_name) {
    return;
  }

  const nodes = { labels: [], colors: [], x: [], y: [], ids: [] };
  const edges = { x: [], y: [] };

  // 根节点
  nodes.labels.push(data.root_name);
  nodes.colors.push("#FFA07A");
  nodes.x.push(0);
  nodes.y.push(0);
  nodes.ids.push("root");

  const radii = [0, 1.5, 3.0, 4.5];
  const children = data.children || [];
  const numChildren = children.length;
  const childAngleStep = numChildren > 0 ? (2 * Math.PI) / numChildren : 0;

  children.forEach((child, i) => {
    const childAngle = i * childAngleStep;
    const xChild = radii[1] * Math.cos(childAngle);
    const yChild = radii[1] * Math.sin(childAngle);

    nodes.labels.push(child.name);
    nodes.colors.push(child.flag === "1" ? "#87CEFA" : "#D3D3D3");
    nodes.x.push(xChild);
    nodes.y.push(yChild);
    nodes.ids.push(`child-${i}`);

    edges.x.push(0, xChild, null);
    edges.y.push(0, yChild, null);

    const grandchildren = child.grandchildren || [];
    const numGrandchildren = grandchildren.length;

    if (numGrandchildren === 0) return;

    const sectorAngle = numChildren > 1 ? childAngleStep * 0.95 : 2 * Math.PI;
    const startAngle = childAngle - sectorAngle / 2;
    const gcAngleStep = sectorAngle / numGrandchildren;

    grandchildren.forEach((gc, j) => {
      const gcAngle = startAngle + (j + 0.5) * gcAngleStep;
      const xGc = radii[2] * Math.cos(gcAngle);
      const yGc = radii[2] * Math.sin(gcAngle);

      nodes.labels.push(gc.name);
      nodes.colors.push(gc.flag === "1" ? "#90EE90" : "#D3D3D3");
      nodes.x.push(xGc);
      nodes.y.push(yGc);
      nodes.ids.push(`gc-${i}-${j}`);

      edges.x.push(xChild, xGc, null);
      edges.y.push(yChild, yGc, null);

      const greatGrandchildren = gc["great-grandchildren"] || [];
      const numGgc = greatGrandchildren.length;

      if (numGgc === 0) return;

      const subSectorAngle = gcAngleStep * 0.95;
      const ggcStartAngle = gcAngle - subSectorAngle / 2;
      const ggcAngleStep = subSectorAngle / numGgc;

      greatGrandchildren.forEach((ggc, k) => {
        const ggcAngle = ggcStartAngle + (k + 0.5) * ggcAngleStep;
        const xGgc = radii[3] * Math.cos(ggcAngle);
        const yGgc = radii[3] * Math.sin(ggcAngle);

        nodes.labels.push(ggc.name);
        nodes.colors.push(ggc.flag === "1" ? "#FFD700" : "#D3D3D3");
        nodes.x.push(xGgc);
        nodes.y.push(yGgc);
        nodes.ids.push(`ggc-${i}-${j}-${k}`);

        edges.x.push(xGc, xGgc, null);
        edges.y.push(yGc, yGgc, null);
      });
    });
  });

  const edgeTrace = {
    x: edges.x,
    y: edges.y,
    mode: "lines",
    line: { width: 1, color: "#888" },
    hoverinfo: "none",
  };

  const nodeTrace = {
    x: nodes.x,
    y: nodes.y,
    mode: "markers+text",
    text: nodes.labels,
    textposition: "bottom center",
    textfont: { size: 10 },
    hoverinfo: "text",
    marker: {
      symbol: "circle",
      size: 25,
      color: nodes.colors,
      line: { width: 2, color: "#555" },
    },
  };

  const layout = {
    showlegend: false,
    xaxis: { showgrid: false, zeroline: false, showticklabels: false },
    yaxis: {
      showgrid: false,
      zeroline: false,
      showticklabels: false,
      scaleanchor: "x",
      scaleratio: 1,
    },
    plot_bgcolor: "rgba(0,0,0,0)",
    paper_bgcolor: "rgba(0,0,0,0)",
    margin: { l: 10, r: 10, t: 30, b: 10 },
    hovermode: "closest",
  };

  Plotly.newPlot("knowledge-graph", [edgeTrace, nodeTrace], layout, {
    responsive: true,
  });
}

// 加载学习节点
async function loadLearningNodes() {
  try {
    const response = await fetch(`${API_BASE}/api/learning-nodes`);
    const nodes = await response.json();
    const select = document.getElementById("node-selector");
    select.innerHTML =
      '<option value="">请选择...</option>' +
      nodes.map((node) => `<option value="${node}">${node}</option>`).join("");
  } catch (error) {
    console.error("Error loading learning nodes:", error);
  }
}

// 设置事件监听器
function setupEventListeners() {
  // 节点选择
  document
    .getElementById("node-selector")
    .addEventListener("change", handleNodeSelection);

  // 功能切换
  document
    .getElementById("feature-select")
    .addEventListener("change", handleFeatureSwitch);

  // 聊天
  document
    .getElementById("send-btn")
    .addEventListener("click", sendChatMessage);
  document.getElementById("chat-input").addEventListener("keypress", (e) => {
    if (e.key === "Enter") sendChatMessage();
  });

  // 测验
  document
    .getElementById("start-quiz-btn")
    .addEventListener("click", startQuiz);
  document.querySelectorAll(".quiz-choice").forEach((btn) => {
    btn.addEventListener("click", () => answerQuiz(btn.dataset.choice));
  });
  document
    .getElementById("plan-from-quiz-btn")
    .addEventListener("click", generatePlanFromQuiz);

  // 学习计划
  document
    .getElementById("plan-btn")
    .addEventListener("click", generateLearningPlan);

  // 总结
  document
    .getElementById("summary-btn")
    .addEventListener("click", generateSummary);

  // 上传
  document.getElementById("upload-btn").addEventListener("click", uploadFiles);
}

// 处理节点选择
async function handleNodeSelection(e) {
  const nodeName = e.target.value;
  if (!nodeName) return;

  currentNode = nodeName;

  try {
    const response = await fetch(`${API_BASE}/api/node/resources`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ node_name: nodeName }),
    });
    const resources = await response.json();

    const resourceGroup = document.getElementById("resource-display-group");
    const resourceList = document.getElementById("resource-list");

    if (resources.length > 0) {
      resourceList.innerHTML = resources
        .map(
          (path, i) =>
            `<div class="resource-item" data-path="${path}">${path
              .split("/")
              .pop()}</div>`
        )
        .join("");

      resourceList.querySelectorAll(".resource-item").forEach((item) => {
        item.addEventListener("click", () => selectResource(item.dataset.path));
      });

      resourceGroup.style.display = "block";
    } else {
      resourceList.innerHTML = "<p>暂无资源</p>";
      resourceGroup.style.display = "block";
    }
  } catch (error) {
    console.error("Error loading resources:", error);
  }
}

// 选择资源
function selectResource(path) {
  currentPdfPath = path;

  // 更新资源列表样式
  document.querySelectorAll(".resource-item").forEach((item) => {
    item.classList.toggle("active", item.dataset.path === path);
  });

  // 显示 PDF
  document.getElementById("knowledge-graph-container").style.display = "none";
  document.getElementById("pdf-viewer-container").style.display = "block";
  document.getElementById(
    "pdf-viewer"
  ).src = `${API_BASE}/api/pdf/${encodeURIComponent(path)}`;

  // 显示功能面板
  document.getElementById("main-function-group").style.display = "block";
  document.getElementById(
    "current-node-display"
  ).textContent = `当前节点: ${currentNode}`;
}

// 处理功能切换
function handleFeatureSwitch(e) {
  const feature = e.target.value;
  const groups = [
    "chat-group",
    "quiz-group",
    "plan-group",
    "summary-group",
    "upload-group",
  ];
  const features = [
    "🤖 AI 助教",
    "📝 随堂测验",
    "🗺️ 学习计划",
    "📜 知识总结",
    "📤 上传新资源",
  ];

  groups.forEach((group, i) => {
    document.getElementById(group).style.display =
      feature === features[i] ? "block" : "none";
  });
}

// 发送聊天消息
async function sendChatMessage() {
  const input = document.getElementById("chat-input");
  const message = input.value.trim();
  if (!message) return;

  const langChoice = document.getElementById("lang-select").value;
  const chatbot = document.getElementById("chatbot");

  // 添加用户消息
  appendMessage("user", message);
  input.value = "";

  // 显示加载状态
  const loadingId = "loading-" + Date.now();
  appendMessage("bot", '<span class="loading"></span>', loadingId);

  try {
    const response = await fetch(`${API_BASE}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: message,
        history: chatHistory,
        lang_choice: langChoice,
      }),
    });

    const data = await response.json();

    // 移除加载状态
    document.getElementById(loadingId)?.remove();

    // 添加助手消息
    const cssClass = data.used_fallback ? "bot fallback" : "bot";
    appendMessage(cssClass, data.response);

    chatHistory.push([message, data.response]);
  } catch (error) {
    console.error("Error sending message:", error);
    document.getElementById(loadingId)?.remove();
    appendMessage("bot", "抱歉，发生错误。请稍后再试。");
  }
}

// 添加消息到聊天框
function appendMessage(type, content, id = null) {
  const chatbot = document.getElementById("chatbot");
  const messageDiv = document.createElement("div");
  messageDiv.className = `message ${type}`;
  if (id) messageDiv.id = id;

  // 如果内容包含 HTML 标签，直接设置
  if (content.includes("<")) {
    messageDiv.innerHTML = content;
  } else {
    // 否则使用 marked 渲染 Markdown
    messageDiv.innerHTML = marked.parse(content);
    messageDiv.classList.add("markdown-content");
  }

  chatbot.appendChild(messageDiv);
  chatbot.scrollTop = chatbot.scrollHeight;
}

// 开始测验
async function startQuiz() {
  const subject = document.getElementById("quiz-subject").value.trim();
  if (!subject) {
    alert("请输入测验主题");
    return;
  }

  const langChoice = document.getElementById("lang-select").value;

  try {
    const response = await fetch(`${API_BASE}/api/quiz/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        subject: subject,
        lang_choice: langChoice,
      }),
    });

    const data = await response.json();
    quizState = data.state;

    displayQuestion(data.question);
    document.getElementById("quiz-result").textContent = data.used_retriever
      ? "📄 Quiz 使用文档上下文生成"
      : "";
  } catch (error) {
    console.error("Error starting quiz:", error);
    alert("生成测验失败");
  }
}

// 显示问题
function displayQuestion(question) {
  const questionDiv = document.getElementById("quiz-question");
  let text = question.question;
  // 格式化选项
  text = text.replace(/\s*([abcd]\))/gi, "\n$1");
  questionDiv.innerHTML = `<strong>${
    question.topic
  }</strong><br><br>${text.trim()}`;
}

// 回答测验
async function answerQuiz(choice) {
  if (!quizState) {
    alert("请先开始测验");
    return;
  }

  try {
    const response = await fetch(`${API_BASE}/api/quiz/answer`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        choice: choice,
        state: quizState,
      }),
    });

    const data = await response.json();

    const resultDiv = document.getElementById("quiz-result");
    resultDiv.textContent = data.is_correct
      ? "✅ 正确！"
      : `❌ 错误！正确答案是：${data.correct_answer}`;

    if (data.finished) {
      document.getElementById("quiz-question").innerHTML =
        "<strong>测验完成！</strong>";
      resultDiv.textContent += "\n\n" + data.results;
      quizState = data.state;
    } else {
      quizState = data.state;
      setTimeout(() => {
        displayQuestion(data.next_question);
        resultDiv.textContent = "";
      }, 1500);
    }
  } catch (error) {
    console.error("Error answering quiz:", error);
    alert("提交答案失败");
  }
}

// 根据测验生成学习计划
async function generatePlanFromQuiz() {
  const name = document.getElementById("quiz-name").value.trim();
  if (!name) {
    alert("请输入你的名字");
    return;
  }

  if (!quizState || !quizState.scores) {
    alert("请先完成测验");
    return;
  }

  const langChoice = document.getElementById("lang-select").value;
  const output = document.getElementById("plan-quiz-output");
  output.textContent = "⏳ 正在生成学习计划...";

  try {
    const response = await fetch(`${API_BASE}/api/learning-plan/from-quiz`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: name,
        state: quizState,
        lang_choice: langChoice,
      }),
    });

    const data = await response.json();
    output.textContent = "✅ " + data.message + "\n\n" + formatPlan(data.plan);
  } catch (error) {
    console.error("Error generating plan from quiz:", error);
    output.textContent = "❌ 生成学习计划失败";
  }
}

// 生成学习计划
async function generateLearningPlan() {
  const name = document.getElementById("plan-name").value.trim();
  const goals = document.getElementById("plan-goals").value.trim();

  if (!name || !goals) {
    alert("请输入名字和学习目标");
    return;
  }

  const langChoice = document.getElementById("lang-select").value;
  const output = document.getElementById("plan-output");
  output.textContent = "⏳ 正在生成学习计划...";

  try {
    const response = await fetch(`${API_BASE}/api/learning-plan`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: name,
        goals: goals,
        lang_choice: langChoice,
      }),
    });

    const data = await response.json();
    output.textContent = "✅ " + data.message + "\n\n" + formatPlan(data.plan);
  } catch (error) {
    console.error("Error generating learning plan:", error);
    output.textContent = "❌ 生成学习计划失败";
  }
}

// 格式化学习计划
function formatPlan(plan) {
  return plan
    .map(
      (entry) =>
        `日期: ${entry.date}\n` +
        `主题: ${entry.topic}\n` +
        `优先级: ${entry.priority}\n` +
        `推荐材料:\n${entry.materials.join("\n")}\n`
    )
    .join("\n---\n");
}

// 生成总结
async function generateSummary() {
  const topic = document.getElementById("summary-topic").value.trim();

  if (!topic) {
    alert("请输入主题");
    return;
  }

  const langChoice = document.getElementById("lang-select").value;
  const output = document.getElementById("summary-output");
  output.textContent = "⏳ 正在生成总结...";

  try {
    const response = await fetch(`${API_BASE}/api/summary`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        topic: topic,
        lang_choice: langChoice,
      }),
    });

    const data = await response.json();
    const notice = data.used_retriever
      ? "📄 Summary 使用文档上下文生成\n\n"
      : "";
    output.innerHTML = notice + marked.parse(data.summary);
    output.classList.add("markdown-content");
  } catch (error) {
    console.error("Error generating summary:", error);
    output.textContent = "❌ 生成总结失败";
  }
}

// 上传文件
async function uploadFiles() {
  const fileInput = document.getElementById("upload-files");
  const files = fileInput.files;

  if (files.length === 0) {
    alert("请选择文件");
    return;
  }

  if (!currentNode) {
    alert("请先选择一个知识节点");
    return;
  }

  const formData = new FormData();
  for (let file of files) {
    formData.append("files", file);
  }

  const status = document.getElementById("upload-status");
  status.textContent = "⏳ 正在上传...";

  try {
    const response = await fetch(
      `${API_BASE}/api/upload?node_name=${encodeURIComponent(currentNode)}`,
      {
        method: "POST",
        body: formData,
      }
    );

    const data = await response.json();

    if (response.ok) {
      status.textContent = "✅ " + data.message;
      fileInput.value = "";

      // 重新加载资源列表
      document
        .getElementById("node-selector")
        .dispatchEvent(new Event("change"));
    } else {
      status.textContent = "❌ " + (data.detail || "上传失败");
    }
  } catch (error) {
    console.error("Error uploading files:", error);
    status.textContent = "❌ 上传失败";
  }
}
