let teacherData = [];
let studentData = [];
let llmLogData = [];
let currentTimeRange = "week";
let allConversations = [];

document.addEventListener("DOMContentLoaded", async () => {
  await loadAllData();
});

async function loadAllData() {
  try {
    // Load teachers
    const teacherRes = await fetch("/api/teachers");
    if (!teacherRes.ok) {
      throw new Error(`Failed to load teachers: ${teacherRes.status}`);
    }
    teacherData = await teacherRes.json();

    // Load students
    const studentRes = await fetch("/api/students");
    if (!studentRes.ok) {
      throw new Error(`Failed to load students: ${studentRes.status}`);
    }
    studentData = await studentRes.json();

    // Load LLM logs
    const logRes = await fetch("/api/llm-logs");
    if (!logRes.ok) {
      throw new Error(`Failed to load LLM logs: ${logRes.status}`);
    }
    llmLogData = await logRes.json();

    renderTeachers();
    renderStudents();
    calculateTokenStats();
    renderTokenChart();
    renderModelChart();
    renderConversations();
    populateModelFilter();
  } catch (error) {
    console.error("加载数据失败:", error);
    // Show error message to user
    const errorMsg = document.createElement("div");
    errorMsg.className = "error-message";
    errorMsg.style.cssText =
      "padding: 20px; margin: 20px; background: #ffebee; color: #c62828; border-radius: 8px;";
    errorMsg.textContent = `数据加载失败: ${error.message}`;
    document.querySelector(".main-content").prepend(errorMsg);
  }
}

function switchTab(tab) {
  document
    .querySelectorAll(".nav-item")
    .forEach((item) => item.classList.remove("active"));
  document
    .querySelectorAll(".content-section")
    .forEach((section) => section.classList.remove("active"));

  event.target.closest(".nav-item").classList.add("active");
  document.getElementById(tab + "-section").classList.add("active");
}

function renderTeachers() {
  const container = document.getElementById("teachersGrid");
  document.getElementById("teacherCount").textContent = teacherData.length;

  const html = teacherData
    .map(
      (teacher) => `
        <div class="teacher-card" data-name="${teacher.name}">
          <div class="teacher-header">
            <div class="teacher-avatar">
              ${teacher.name.charAt(0).toUpperCase()}
            </div>
            <div class="teacher-info">
              <h3>${teacher.name}</h3>
              <p>${teacher.email || "未提供邮箱"}</p>
            </div>
          </div>
          
          <div class="teacher-meta">
            <div class="meta-item">
              <div class="meta-label">用户名</div>
              <div class="meta-value">${teacher.username}</div>
            </div>
            <div class="meta-item">
              <div class="meta-label">角色</div>
              <div class="meta-value">教师</div>
            </div>
          </div>
          
          <div class="teacher-students">
            <div class="students-label">负责学生 (${
              teacher.students.length
            })</div>
            <div class="student-tags">
              ${teacher.students
                .map(
                  (student) =>
                    `<span class="student-tag" onclick="scrollToStudent('${student}')">${student}</span>`
                )
                .join("")}
            </div>
          </div>
        </div>
      `
    )
    .join("");

  container.innerHTML =
    html ||
    '<div class="empty-state"><div class="empty-state-icon">👨‍🏫</div><div class="empty-state-text">暂无教师信息</div></div>';
}

function renderStudents() {
  const container = document.getElementById("studentsGrid");
  document.getElementById("studentCount").textContent = studentData.length;

  const html = studentData
    .map(
      (student) => `
        <div class="student-card" data-name="${student.stu_name}">
          <div class="student-header">
            <div class="student-avatar">
              ${
                student.img && student.img !== ""
                  ? `<img src="${student.img}" alt="${student.stu_name}" />`
                  : student.stu_name.charAt(0).toUpperCase()
              }
            </div>
            <div class="student-info">
              <h3>${student.stu_name}</h3>
              <p>${student.email || "未提供邮箱"}</p>
            </div>
          </div>
          
          <div class="student-meta">
            <div class="meta-item">
              <div class="meta-label">用户名</div>
              <div class="meta-value">${student.username}</div>
            </div>
            <div class="meta-item">
              <div class="meta-label">指导教师</div>
              <div class="meta-value">${student.teacher}</div>
            </div>
          </div>
          
          <div class="student-section">
            <div class="section-title">学习目标</div>
            <div class="goals-list">
              ${student.learning_goals
                .map((goal) => `<span class="goal-tag">${goal}</span>`)
                .join("")}
            </div>
          </div>
          
          <div class="student-section">
            <div class="section-title">课程偏好</div>
            <div class="goals-list">
              ${student.preference.course_type
                .map((type) => `<span class="goal-tag">${type.name}</span>`)
                .join("")}
            </div>
          </div>
        </div>
      `
    )
    .join("");

  container.innerHTML =
    html ||
    '<div class="empty-state"><div class="empty-state-icon">🧑‍🎓</div><div class="empty-state-text">暂无学生信息</div></div>';
}

function filterUsers() {
  const searchTerm = document.getElementById("userSearch").value.toLowerCase();

  document.querySelectorAll(".teacher-card").forEach((card) => {
    const name = card.getAttribute("data-name").toLowerCase();
    const studentTags = Array.from(card.querySelectorAll(".student-tag"))
      .map((tag) => tag.textContent.toLowerCase())
      .join(" ");
    const matches =
      name.includes(searchTerm) || studentTags.includes(searchTerm);
    card.style.display = matches ? "block" : "none";
  });

  document.querySelectorAll(".student-card").forEach((card) => {
    const name = card.getAttribute("data-name").toLowerCase();
    const matches = name.includes(searchTerm);
    card.style.display = matches ? "block" : "none";
  });
}

function scrollToStudent(studentName) {
  const studentCard = document.querySelector(
    `.student-card[data-name="${studentName}"]`
  );
  if (studentCard) {
    studentCard.scrollIntoView({ behavior: "smooth", block: "center" });
    studentCard.style.animation = "highlight 1s ease";
    setTimeout(() => {
      studentCard.style.animation = "";
    }, 1000);
  }
}

function calculateTokenStats() {
  const now = new Date();
  const oneWeekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
  const oneMonthAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);

  let weeklyTotal = 0;
  let monthlyTotal = 0;
  let allTimeTotal = 0;

  llmLogData.forEach((log) => {
    const logDate = new Date(log.timestamp);
    const tokens = log.response?.usage?.total_tokens || 0;

    allTimeTotal += tokens;

    if (logDate >= oneWeekAgo) {
      weeklyTotal += tokens;
    }
    if (logDate >= oneMonthAgo) {
      monthlyTotal += tokens;
    }
  });

  const avgTokens =
    llmLogData.length > 0 ? Math.round(allTimeTotal / llmLogData.length) : 0;

  document.getElementById("weeklyTokens").textContent =
    formatNumber(weeklyTotal);
  document.getElementById("monthlyTokens").textContent =
    formatNumber(monthlyTotal);
  document.getElementById("totalTokens").textContent =
    formatNumber(allTimeTotal);
  document.getElementById("avgTokens").textContent = formatNumber(avgTokens);
}

function formatNumber(num) {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + "M";
  } else if (num >= 1000) {
    return (num / 1000).toFixed(1) + "K";
  }
  return num.toString();
}

function renderTokenChart() {
  const chartDom = document.getElementById("tokenChart");
  const chart = echarts.init(chartDom);

  const dateMap = {};
  const now = new Date();
  let daysToShow = 7;

  if (currentTimeRange === "month") {
    daysToShow = 30;
  } else if (currentTimeRange === "all") {
    daysToShow = 365;
  }

  const startDate = new Date(now.getTime() - daysToShow * 24 * 60 * 60 * 1000);

  llmLogData.forEach((log) => {
    const logDate = new Date(log.timestamp);
    if (logDate >= startDate) {
      const dateKey = logDate.toISOString().split("T")[0];
      if (!dateMap[dateKey]) {
        dateMap[dateKey] = {
          prompt: 0,
          completion: 0,
          total: 0,
        };
      }
      const usage = log.response?.usage || {};
      dateMap[dateKey].prompt += usage.prompt_tokens || 0;
      dateMap[dateKey].completion += usage.completion_tokens || 0;
      dateMap[dateKey].total += usage.total_tokens || 0;
    }
  });

  const dates = Object.keys(dateMap).sort();
  const promptData = dates.map((date) => dateMap[date].prompt);
  const completionData = dates.map((date) => dateMap[date].completion);
  const totalData = dates.map((date) => dateMap[date].total);

  const option = {
    tooltip: {
      trigger: "axis",
      backgroundColor: "rgba(50,50,50,0.9)",
      borderRadius: 8,
      textStyle: { color: "#fff" },
      axisPointer: {
        type: "cross",
        label: {
          backgroundColor: "#7a6ad8",
        },
      },
    },
    legend: {
      data: ["Prompt Tokens", "Completion Tokens", "Total Tokens"],
      top: 10,
    },
    grid: {
      left: "3%",
      right: "4%",
      bottom: "3%",
      top: 60,
      containLabel: true,
    },
    xAxis: {
      type: "category",
      boundaryGap: false,
      data: dates,
      axisLabel: {
        formatter: (value) => {
          const date = new Date(value);
          return `${date.getMonth() + 1}/${date.getDate()}`;
        },
      },
    },
    yAxis: {
      type: "value",
      name: "Tokens",
      splitLine: {
        lineStyle: {
          type: "dashed",
          color: "#e0e0e0",
        },
      },
    },
    series: [
      {
        name: "Prompt Tokens",
        type: "line",
        smooth: true,
        data: promptData,
        lineStyle: { width: 2 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: "rgba(122, 106, 216, 0.3)" },
            { offset: 1, color: "rgba(122, 106, 216, 0.05)" },
          ]),
        },
      },
      {
        name: "Completion Tokens",
        type: "line",
        smooth: true,
        data: completionData,
        lineStyle: { width: 2 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: "rgba(81, 207, 102, 0.3)" },
            { offset: 1, color: "rgba(81, 207, 102, 0.05)" },
          ]),
        },
      },
      {
        name: "Total Tokens",
        type: "line",
        smooth: true,
        data: totalData,
        lineStyle: { width: 3 },
        itemStyle: { color: "#ff6b6b" },
      },
    ],
    color: ["#7a6ad8", "#51cf66", "#ff6b6b"],
  };

  chart.setOption(option);
  window.addEventListener("resize", () => chart.resize());
}

function changeTimeRange(range) {
  currentTimeRange = range;

  document.querySelectorAll(".chart-btn").forEach((btn) => {
    btn.classList.remove("active");
  });
  event.target.classList.add("active");

  renderTokenChart();
}

function renderModelChart() {
  const chartDom = document.getElementById("modelChart");
  const chart = echarts.init(chartDom);

  const modelMap = {};
  llmLogData.forEach((log) => {
    const model = log.request?.model || "Unknown";
    if (!modelMap[model]) {
      modelMap[model] = { count: 0, tokens: 0 };
    }
    modelMap[model].count += 1;
    modelMap[model].tokens += log.response?.usage?.total_tokens || 0;
  });

  const modelData = Object.keys(modelMap).map((model) => ({
    name: model,
    value: modelMap[model].count,
    tokens: modelMap[model].tokens,
  }));

  const option = {
    tooltip: {
      trigger: "item",
      formatter: (params) => {
        const item = params.data;
        return `${params.name}<br/>
                调用次数: ${item.value}<br/>
                总 Tokens: ${formatNumber(item.tokens)}`;
      },
      backgroundColor: "rgba(50,50,50,0.9)",
      borderRadius: 8,
      textStyle: { color: "#fff" },
    },
    legend: {
      orient: "vertical",
      left: "left",
      top: "center",
    },
    series: [
      {
        name: "模型使用",
        type: "pie",
        radius: ["40%", "70%"],
        center: ["60%", "50%"],
        avoidLabelOverlap: true,
        itemStyle: {
          borderRadius: 10,
          borderColor: "#fff",
          borderWidth: 2,
        },
        label: {
          show: true,
          formatter: "{b}: {d}%",
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 16,
            fontWeight: "bold",
          },
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: "rgba(0, 0, 0, 0.5)",
          },
        },
        data: modelData,
      },
    ],
    color: ["#7a6ad8", "#51cf66", "#ff6b6b", "#ffd43b", "#74c0fc"],
  };

  chart.setOption(option);
  window.addEventListener("resize", () => chart.resize());
}

function populateModelFilter() {
  const models = [
    ...new Set(llmLogData.map((log) => log.request?.model || "Unknown")),
  ];
  const select = document.getElementById("modelFilter");

  models.forEach((model) => {
    const option = document.createElement("option");
    option.value = model;
    option.textContent = model;
    select.appendChild(option);
  });
}

function renderConversations() {
  allConversations = llmLogData.map((log, index) => ({
    id: index,
    ...log,
  }));

  filterConversations();
}

function filterConversations() {
  const modelFilter = document.getElementById("modelFilter").value;
  const timeFilter = document.getElementById("timeFilter").value;
  const searchTerm = document
    .getElementById("conversationSearch")
    .value.toLowerCase();

  let filtered = [...allConversations];

  if (modelFilter) {
    filtered = filtered.filter((log) => log.request?.model === modelFilter);
  }

  const now = new Date();
  if (timeFilter !== "all") {
    let startDate;
    if (timeFilter === "today") {
      startDate = new Date(now.setHours(0, 0, 0, 0));
    } else if (timeFilter === "week") {
      startDate = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
    } else if (timeFilter === "month") {
      startDate = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
    }
    filtered = filtered.filter((log) => new Date(log.timestamp) >= startDate);
  }

  if (searchTerm) {
    filtered = filtered.filter((log) => {
      const content = JSON.stringify(log.request?.messages || []).toLowerCase();
      const response =
        log.response?.choices?.[0]?.message?.content?.toLowerCase() || "";
      return content.includes(searchTerm) || response.includes(searchTerm);
    });
  }

  filtered.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

  displayConversations(filtered);
}

function displayConversations(conversations) {
  const container = document.getElementById("conversationsContainer");

  if (conversations.length === 0) {
    container.innerHTML =
      '<div class="empty-state"><div class="empty-state-icon">💬</div><div class="empty-state-text">暂无符合条件的对话记录</div></div>';
    return;
  }

  const html = conversations
    .map((log) => {
      const timestamp = new Date(log.timestamp);
      const model = log.request?.model || "Unknown";
      const module = log.module || "Unknown";
      const usage = log.response?.usage || {};
      const messages = log.request?.messages || [];
      const response =
        log.response?.choices?.[0]?.message?.content || "无响应内容";

      const metadata = log.metadata || {};
      const metadataStr = Object.keys(metadata)
        .map((key) => `${key}: ${metadata[key]}`)
        .join(" | ");

      return `
        <div class="conversation-card">
          <div class="conversation-header" onclick="toggleConversation(${
            log.id
          })">
            <div class="conversation-title">
              <h4>🤖 ${module}</h4>
              <div class="conversation-meta">
                <span class="meta-tag">
                  <span class="meta-tag-icon">🕐</span>
                  ${timestamp.toLocaleString("zh-CN")}
                </span>
                <span class="meta-tag">
                  <span class="meta-tag-icon">🔧</span>
                  ${model}
                </span>
                ${
                  metadataStr
                    ? `<span class="meta-tag"><span class="meta-tag-icon">ℹ️</span>${metadataStr}</span>`
                    : ""
                }
              </div>
            </div>
            <button class="conversation-toggle">
              <span id="toggle-text-${log.id}">展开详情</span>
            </button>
          </div>

          <div class="token-info">
            <div class="token-item">
              <span class="token-label">Prompt Tokens</span>
              <span class="token-value">${usage.prompt_tokens || 0}</span>
            </div>
            <div class="token-item">
              <span class="token-label">Completion Tokens</span>
              <span class="token-value">${usage.completion_tokens || 0}</span>
            </div>
            <div class="token-item">
              <span class="token-label">Total Tokens</span>
              <span class="token-value">${usage.total_tokens || 0}</span>
            </div>
          </div>

          <div class="conversation-content" id="content-${log.id}">
            <div class="message-section">
              <div class="message-label">📤 用户请求</div>
              <div class="message-text request">${formatMessages(
                messages
              )}</div>
            </div>
            <div class="message-section">
              <div class="message-label">📥 AI 响应</div>
              <div class="message-text response">${escapeHtml(response)}</div>
            </div>
          </div>
        </div>
      `;
    })
    .join("");

  container.innerHTML = html;
}

function toggleConversation(id) {
  const content = document.getElementById(`content-${id}`);
  const toggleText = document.getElementById(`toggle-text-${id}`);

  if (content.classList.contains("show")) {
    content.classList.remove("show");
    toggleText.textContent = "展开详情";
  } else {
    content.classList.add("show");
    toggleText.textContent = "收起详情";
  }
}

function formatMessages(messages) {
  return messages
    .map((msg) => {
      const role =
        msg.role === "user"
          ? "用户"
          : msg.role === "assistant"
          ? "助手"
          : msg.role;
      return `[${role}]: ${escapeHtml(msg.content)}`;
    })
    .join("\n\n");
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

const style = document.createElement("style");
style.textContent = `
  @keyframes highlight {
    0%, 100% { background: white; }
    50% { background: #f8f7fe; }
  }
`;
document.head.appendChild(style);
