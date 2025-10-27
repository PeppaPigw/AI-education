const API_BASE = "";
let courseData = null;
let currentNode = null;
let currentResources = [];
let chatHistory = [];
let currentHls = null;

// Initialize
document.addEventListener("DOMContentLoaded", async () => {
  console.log("My Learning page loaded");
  await loadCourseData();
  setupEventListeners();
});

// Load course data
async function loadCourseData() {
  try {
    const response = await fetch(`${API_BASE}/api/knowledge-graph`);
    courseData = await response.json();
    console.log("Course data loaded:", courseData);
    renderTOC();
  } catch (error) {
    console.error("Error loading course data:", error);
    document.getElementById("toc-tree").innerHTML =
      '<li style="text-align: center; color: red; padding: 20px">加载失败</li>';
  }
}

// Render Table of Contents
function renderTOC() {
  if (!courseData || !courseData.children) return;

  const tocTree = document.getElementById("toc-tree");
  tocTree.innerHTML = "";

  courseData.children.forEach((chapter, chapterIndex) => {
    const chapterLi = document.createElement("li");
    chapterLi.className = "toc-chapter";

    const chapterHeader = document.createElement("div");
    chapterHeader.className = "toc-chapter-header";
    const completedBadge =
      chapter.flag === "1"
        ? '<span class="completed-badge">✓ 已完成</span>'
        : "";
    chapterHeader.innerHTML = `
            <span class="toc-toggle">▶</span>
            <span>${chapter.name}</span>
            ${completedBadge}
          `;

    const sectionsUl = document.createElement("ul");
    sectionsUl.className = "toc-sections";

    // Add grandchildren (sections)
    if (chapter.grandchildren) {
      chapter.grandchildren.forEach((section) => {
        const sectionLi = document.createElement("li");
        sectionLi.className = "toc-section-item";
        const sectionCompletedBadge =
          section.flag === "1" ? '<span class="completed-badge">✓</span>' : "";
        sectionLi.innerHTML = `${section.name}${sectionCompletedBadge}`;
        sectionLi.dataset.node = JSON.stringify(section);

        // Add great-grandchildren (knowledge points)
        if (
          section["great-grandchildren"] &&
          section["great-grandchildren"].length > 0
        ) {
          const kpUl = document.createElement("ul");
          kpUl.className = "toc-knowledge-points";

          section["great-grandchildren"].forEach((kp) => {
            const kpLi = document.createElement("li");
            kpLi.className = "toc-knowledge-item";
            const kpCompletedBadge =
              kp.flag === "1" ? '<span class="completed-badge">✓</span>' : "";
            kpLi.innerHTML = `${kp.name}${kpCompletedBadge}`;
            kpLi.dataset.node = JSON.stringify(kp);

            kpLi.addEventListener("click", (e) => {
              e.stopPropagation();
              handleNodeSelect(kp);
            });

            kpUl.appendChild(kpLi);
          });

          sectionLi.appendChild(kpUl);
        }

        sectionLi.addEventListener("click", (e) => {
          e.stopPropagation();
          handleNodeSelect(section);
        });

        sectionsUl.appendChild(sectionLi);
      });
    }

    chapterHeader.addEventListener("click", () => {
      const toggle = chapterHeader.querySelector(".toc-toggle");
      toggle.classList.toggle("expanded");
      sectionsUl.classList.toggle("show");
      chapterHeader.classList.toggle("active");
    });

    chapterLi.appendChild(chapterHeader);
    chapterLi.appendChild(sectionsUl);
    tocTree.appendChild(chapterLi);
  });
}

// Handle node selection
function handleNodeSelect(node) {
  console.log("Node selected:", node);
  currentNode = node;

  // Update active state
  document
    .querySelectorAll(".toc-section-item, .toc-knowledge-item")
    .forEach((el) => {
      el.classList.remove("active");
    });
  event.target.classList.add("active");

  // Process resources
  let resources = node.resource_path;
  let resourceArray = [];

  if (typeof resources === "string") {
    if (resources.trim()) {
      resourceArray = [resources.trim()];
    }
  } else if (Array.isArray(resources)) {
    resourceArray = resources.filter((r) => r && r.trim());
  }

  currentResources = resourceArray;

  // Show resource container
  document.getElementById("welcome-screen").style.display = "none";
  document.getElementById("resource-container").style.display = "flex";

  // Update resource title
  document.getElementById("resource-title").textContent = node.name;

  // Render resource list
  renderResourceList(resourceArray);

  // If has resources, auto-select first one
  if (resourceArray.length > 0) {
    selectResource(resourceArray[0], 0);
  } else {
    showNoResource();
  }
}

// Render resource list
function renderResourceList(resources) {
  const resourceList = document.getElementById("resource-list");
  resourceList.innerHTML = "";

  if (resources.length === 0) {
    resourceList.innerHTML =
      '<div style="color: var(--text-dim); font-size: 12px;">该节点暂无资源</div>';
    return;
  }

  resources.forEach((resource, index) => {
    const badge = document.createElement("div");
    badge.className = "resource-badge";

    const isVideo =
      resource.startsWith("http://") || resource.startsWith("https://");

    if (isVideo) {
      badge.textContent = `🎬 视频 ${index + 1}`;
    } else {
      const filename = resource
        .split("/")
        .pop()
        .replace(/\.pdf$/i, "");
      badge.textContent = `📄 ${filename}`;
    }

    badge.dataset.index = index;
    badge.dataset.resource = resource;

    badge.addEventListener("click", () => {
      selectResource(resource, index);
    });

    resourceList.appendChild(badge);
  });
}

// Select and display resource
async function selectResource(resource, index) {
  // Update active state
  document.querySelectorAll(".resource-badge").forEach((badge) => {
    badge.classList.toggle("active", badge.dataset.index == index);
  });

  const isVideo =
    resource.startsWith("http://") || resource.startsWith("https://");

  // Hide all viewers
  document.getElementById("no-resource").style.display = "none";
  document.getElementById("pdf-viewer").style.display = "none";
  document.getElementById("video-player").style.display = "none";

  // Clean up previous HLS instance
  if (currentHls) {
    currentHls.destroy();
    currentHls = null;
  }

  if (isVideo) {
    // Show video
    const video = document.getElementById("video-player");
    video.style.display = "block";

    if (Hls.isSupported()) {
      currentHls = new Hls();
      currentHls.loadSource(resource);
      currentHls.attachMedia(video);
      currentHls.on(Hls.Events.MANIFEST_PARSED, function () {
        video.play();
      });
    } else if (video.canPlayType("application/vnd.apple.mpegurl")) {
      video.src = resource;
      video.addEventListener("loadedmetadata", function () {
        video.play();
      });
    }
  } else {
    // Show PDF
    const pdfViewer = document.getElementById("pdf-viewer");
    pdfViewer.style.display = "block";

    // Notify backend about PDF selection for RAG
    try {
      await fetch(`${API_BASE}/api/pdf/select`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pdf_path: resource }),
      });
      console.log("PDF selected for RAG:", resource);
    } catch (error) {
      console.error("Error selecting PDF:", error);
    }

    pdfViewer.src = `${API_BASE}/api/pdf/${encodeURIComponent(resource)}`;
  }
}

// Show no resource message
function showNoResource() {
  document.getElementById("no-resource").style.display = "flex";
  document.getElementById("pdf-viewer").style.display = "none";
  document.getElementById("video-player").style.display = "none";
}

// Setup event listeners
function setupEventListeners() {
  // AI tabs
  document.querySelectorAll(".ai-tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      const targetTab = tab.dataset.tab;
      switchAITab(targetTab);
    });
  });

  // Chat
  document
    .getElementById("send-chat-btn")
    .addEventListener("click", sendChatMessage);
  document.getElementById("chat-input").addEventListener("keypress", (e) => {
    if (e.key === "Enter") sendChatMessage();
  });

  // Summary
  document
    .getElementById("generate-summary-btn")
    .addEventListener("click", generateSummary);

  // Quiz
  document.getElementById("start-quiz-btn").addEventListener("click", () => {
    // Use current node name as topic
    if (currentNode && currentNode.name) {
      window.location.href = `/static/quizpage.html?topic=${encodeURIComponent(
        currentNode.name
      )}`;
    } else {
      alert("请先选择一个知识点");
    }
  });

  document.querySelectorAll(".quiz-topic-item").forEach((item) => {
    item.addEventListener("click", () => {
      const topic = item.dataset.topic;
      window.location.href = `/static/quizpage.html?topic=${encodeURIComponent(
        topic
      )}`;
    });
  });
}

// Switch AI tab
function switchAITab(tabName) {
  document.querySelectorAll(".ai-tab").forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.tab === tabName);
  });

  document.querySelectorAll(".ai-content").forEach((content) => {
    content.classList.toggle("active", content.id === `${tabName}-content`);
  });

  // Show/hide chat input area based on tab
  const chatInputArea = document.querySelector(".chat-input-area");
  chatInputArea.style.display = tabName === "chat" ? "block" : "none";
}

// Send chat message
async function sendChatMessage() {
  const input = document.getElementById("chat-input");
  const message = input.value.trim();
  if (!message) return;

  const messagesContainer = document.getElementById("chat-messages");

  // Add user message
  const userMsg = document.createElement("div");
  userMsg.className = "chat-message user";
  userMsg.textContent = message;
  messagesContainer.appendChild(userMsg);

  input.value = "";

  // Add loading message
  const loadingMsg = document.createElement("div");
  loadingMsg.className = "chat-message loading";
  loadingMsg.innerHTML = '<span class="loading-dots">思考中</span>';
  messagesContainer.appendChild(loadingMsg);
  messagesContainer.scrollTop = messagesContainer.scrollHeight;

  try {
    const response = await fetch(`${API_BASE}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: message,
        history: chatHistory,
        lang_choice: "🌐 Auto-detect",
      }),
    });

    const data = await response.json();

    // Remove loading message
    loadingMsg.remove();

    // Add bot message
    const botMsg = document.createElement("div");
    botMsg.className = "chat-message bot markdown-content";
    botMsg.innerHTML = marked.parse(data.response);
    messagesContainer.appendChild(botMsg);

    chatHistory.push([message, data.response]);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  } catch (error) {
    console.error("Error sending chat message:", error);
    loadingMsg.remove();

    const errorMsg = document.createElement("div");
    errorMsg.className = "chat-message bot";
    errorMsg.textContent = "抱歉，发生错误。请稍后再试。";
    messagesContainer.appendChild(errorMsg);
  }
}

// Generate summary
async function generateSummary() {
  const topic = document.getElementById("summary-topic").value.trim();

  if (!topic) {
    alert("请输入要总结的主题");
    return;
  }

  const output = document.getElementById("summary-output");
  output.innerHTML =
    '<p style="color: var(--text-dim);">⏳ 正在生成总结...</p>';

  try {
    const response = await fetch(`${API_BASE}/api/summary`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        topic: topic,
        lang_choice: "🌐 Auto-detect",
      }),
    });

    const data = await response.json();
    const notice = data.used_retriever
      ? '<p style="color: var(--primary-blue); font-size: 12px; margin-bottom: 12px;">📄 使用文档上下文生成</p>'
      : "";

    output.innerHTML = notice + marked.parse(data.summary);
    output.classList.add("markdown-content");
  } catch (error) {
    console.error("Error generating summary:", error);
    output.innerHTML = '<p style="color: red;">❌ 生成总结失败</p>';
  }
}
