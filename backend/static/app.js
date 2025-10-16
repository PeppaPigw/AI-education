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
  console.log("DOM loaded, starting initialization...");
  try {
    await loadLanguages();
    await loadKnowledgeGraph();
    setupEventListeners();
    console.log("Initialization complete");
  } catch (error) {
    console.error("Initialization error:", error);
  }
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
    console.log("Loading knowledge graph...");
    const response = await fetch(`${API_BASE}/api/knowledge-graph`);
    knowledgeGraphData = await response.json();
    console.log("Knowledge graph data loaded:", knowledgeGraphData);

    if (typeof initializeGraph === "function") {
      initializeGraph(knowledgeGraphData);
    } else {
      console.error("initializeGraph function not found!");
    }
  } catch (error) {
    console.error("Error loading knowledge graph:", error);
  }
}

// 处理节点点击，显示资源
window.handleNodeClick = function (nodeData) {
  console.log("handleNodeClick called with:", nodeData);
  console.log("Node type:", nodeData.type);
  console.log("Raw resource_path:", nodeData.resource_path);

  currentNode = nodeData.name;
  const resources = nodeData.resource_path;

  // 处理resource_path可能是字符串或数组的情况
  let resourceArray = [];
  if (typeof resources === "string") {
    if (resources.trim()) {
      resourceArray = [resources.trim()];
    }
  } else if (Array.isArray(resources)) {
    resourceArray = resources.filter((r) => r && r.trim());
  }

  console.log("Processed resources array:", resourceArray);

  if (!resourceArray || resourceArray.length === 0) {
    console.log("No resources found for node:", nodeData.name);
    // 清空资源列表但不隐藏容器
    const resourceGroup = document.getElementById("resource-display-group");
    const resourceList = document.getElementById("resource-list");
    resourceList.innerHTML =
      '<div style="padding: 10px; color: #718096;">该节点暂无学习资源</div>';
    resourceGroup.style.display = "block";
    return;
  }

  // 判断是视频还是PDF
  const isVideo =
    resourceArray[0].startsWith("http://") ||
    resourceArray[0].startsWith("https://");

  const resourceGroup = document.getElementById("resource-display-group");
  const resourceList = document.getElementById("resource-list");

  if (isVideo) {
    // 视频资源 - 使用great-grandchildren名字
    const videoNames = getGrandchildrenNames(nodeData.name);
    console.log("Video names from great-grandchildren:", videoNames);
    resourceList.innerHTML = resourceArray
      .map((url, i) => {
        const name = videoNames[i] || `视频 ${i + 1}`;
        return `<div class="resource-item" data-path="${url}" data-type="video">🎬 ${name}</div>`;
      })
      .join("");
  } else {
    // PDF资源 - 去掉后缀
    resourceList.innerHTML = resourceArray
      .map((path) => {
        const filename = path
          .split("/")
          .pop()
          .replace(/\.pdf$/i, "");
        return `<div class="resource-item" data-path="${path}" data-type="pdf">📄 ${filename}</div>`;
      })
      .join("");
  }

  resourceList.querySelectorAll(".resource-item").forEach((item) => {
    item.addEventListener("click", () => {
      if (item.dataset.type === "video") {
        selectVideo(item.dataset.path);
      } else {
        selectResource(item.dataset.path);
      }
    });
  });

  resourceGroup.style.display = "block";
};

function getGrandchildrenNames(childName) {
  if (!knowledgeGraphData || !knowledgeGraphData.children) return [];

  const child = knowledgeGraphData.children.find((c) => c.name === childName);
  if (!child || !child.grandchildren) return [];

  const names = [];
  for (const gc of child.grandchildren) {
    if (gc["great-grandchildren"] && gc["great-grandchildren"].length > 0) {
      for (const ggc of gc["great-grandchildren"]) {
        names.push(ggc.name);
      }
    }
  }

  return names;
}

function selectVideo(videoUrl) {
  currentPdfPath = null;

  // 更新资源列表样式
  document.querySelectorAll(".resource-item").forEach((item) => {
    item.classList.toggle("active", item.dataset.path === videoUrl);
  });

  // 隐藏知识图谱和PDF
  document.getElementById("knowledge-graph-container").style.display = "none";
  document.getElementById("pdf-viewer-container").style.display = "none";

  // 显示视频播放器
  const videoContainer = document.getElementById("video-player-container");
  const video = document.getElementById("video-player");
  videoContainer.style.display = "block";

  // 使用HLS.js播放m3u8
  if (Hls.isSupported()) {
    const hls = new Hls();
    hls.loadSource(videoUrl);
    hls.attachMedia(video);
    hls.on(Hls.Events.MANIFEST_PARSED, function () {
      video.play();
    });
  } else if (video.canPlayType("application/vnd.apple.mpegurl")) {
    video.src = videoUrl;
    video.addEventListener("loadedmetadata", function () {
      video.play();
    });
  }

  // 显示功能面板
  document.getElementById("main-function-group").style.display = "block";
  document.getElementById(
    "current-node-display"
  ).textContent = `当前节点: ${currentNode}`;
}

// 设置事件监听器
function setupEventListeners() {
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

// 选择资源
async function selectResource(path) {
  currentPdfPath = path;

  // 更新资源列表样式
  document.querySelectorAll(".resource-item").forEach((item) => {
    item.classList.toggle("active", item.dataset.path === path);
  });

  // 通知后端当前选择的PDF
  try {
    const response = await fetch(`${API_BASE}/api/pdf/select`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pdf_path: path }),
    });
    const data = await response.json();
    if (data.success) {
      console.log("✅ PDF selected and ingested:", path);
    } else {
      console.error("❌ Failed to select PDF:", data.error);
    }
  } catch (error) {
    console.error("Error selecting PDF:", error);
  }

  // 显示 PDF
  document.getElementById("knowledge-graph-container").style.display = "none";
  document.getElementById("video-player-container").style.display = "none";
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
