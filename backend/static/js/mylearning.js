const API_BASE = "";
let allPlans = [];
let currentMonth = new Date();
let selectedPlanIndex = null;

document.addEventListener("DOMContentLoaded", async () => {
  console.log("My Learning page loaded");
  await loadLanguages();
  await loadPlans();
  renderCalendar();

  document.getElementById("prev-month").addEventListener("click", () => {
    currentMonth.setMonth(currentMonth.getMonth() - 1);
    renderCalendar();
  });

  document.getElementById("next-month").addEventListener("click", () => {
    currentMonth.setMonth(currentMonth.getMonth() + 1);
    renderCalendar();
  });
});

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
async function loadPlans() {
  try {
    const response = await fetch(`${API_BASE}/api/learning-plans`);
    if (!response.ok) {
      throw new Error("Failed to fetch plans");
    }

    const plans = await response.json();
    allPlans = plans.map((plan) => ({
      filename: plan.filename,
      data: plan.data,
      date: extractDateFromFilename(plan.filename),
    }));

    renderPlansList();
    updateCalendarStats();
  } catch (error) {
    console.error("Error loading plans:", error);
    showEmptyState("无法加载学习计划");
  }
}

function extractDateFromFilename(filename) {
  const match = filename.match(/(\d{8})_(\d{6})/);
  if (match) {
    const dateStr = match[1];
    const year = dateStr.substring(0, 4);
    const month = dateStr.substring(4, 6);
    const day = dateStr.substring(6, 8);
    return `${year}-${month}-${day}`;
  }
  return new Date().toISOString().split("T")[0];
}

function renderPlansList() {
  const container = document.getElementById("plans-list");

  if (allPlans.length === 0) {
    showEmptyState('暂无学习计划，点击"创建新计划"开始制定您的学习计划');
    return;
  }

  function parseMaterialsBySection(materials) {
    if (!Array.isArray(materials)) return [];
    const text = materials.join("\n");
    const sections = text.split(/^###\s+/m).slice(1);
    return sections.map((section) => {
      const [title, ...body] = section.split("\n");
      const count = (body.join("\n").match(/^\s*\d+\.\s+\*\*.*\*\*/gm) || [])
        .length;
      return { title: title.trim(), count };
    });
  }

  function countLearningMaterials(materials) {
    return parseMaterialsBySection(materials).reduce(
      (sum, s) => sum + s.count,
      0
    );
  }

  container.innerHTML = allPlans
    .map((plan, index) => {
      const firstEntry = plan.data[0];
      const sections = parseMaterialsBySection(firstEntry.materials);
      const materialsCount = countLearningMaterials(firstEntry.materials);

      const sectionText = sections
        .map((s) => `${s.title}：${s.count} 条`)
        .join("， ");
      const deadlineInfo = firstEntry.deadline
        ? `<div class="plan-deadline" style="color: #ff6b6b; font-size: 12px; margin-top: 4px;">⏰ 截止日期: ${firstEntry.deadline}</div>`
        : "";

      return `
        <div class="plan-card ${selectedPlanIndex === index ? "selected" : ""}" 
             onclick="selectPlan(${index})">
          <div class="plan-header">
            <div class="plan-date">📅 ${firstEntry.date}</div>
            <div class="plan-priority ${firstEntry.priority}">${
        firstEntry.priority
      }</div>
          </div>
          <div class="plan-topic">${firstEntry.topic}</div>
          <div class="plan-materials">
            📚 共 ${materialsCount} 个学习材料
            <div class="plan-section-details">(${sectionText})</div>
          </div>
          ${deadlineInfo}
        </div>
      `;
    })
    .join("");
  if (selectedPlanIndex !== null) {
    showPlanDetail(selectedPlanIndex);
  }
}

function showEmptyState(message) {
  const container = document.getElementById("plans-list");
  container.innerHTML = `
          <div class="empty-state">
            <div class="empty-state-icon">📋</div>
            <p>${message}</p>
          </div>
        `;
}
function selectPlan(index) {
  selectedPlanIndex = index;
  renderPlansList();
}

function showPlanDetail(index) {
  const plan = allPlans[index];
  const container = document.getElementById("plans-list");

  const detailHTML = `
          <div class="plan-card selected">
            <div class="plan-header">
              <div class="plan-date">📅 ${plan.data[0].date}</div>
              <div class="plan-priority ${plan.data[0].priority}">${
    plan.data[0].priority
  }</div>
            </div>
            <div class="plan-topic">${plan.data[0].topic}</div>
          </div>
          <div class="plan-detail">
            ${formatPlanMarkdown(plan.data)}
          </div>
          <button class="action-button" style="margin-top: 16px;" onclick="selectedPlanIndex = null; renderPlansList()">
            ← 返回列表
          </button>
        `;

  container.innerHTML = detailHTML;
}

function formatPlanMarkdown(planData) {
  const markdown = planData
    .map((entry) => {
      const deadlineInfo = entry.deadline
        ? `**截止日期**: ⏰ ${entry.deadline}\n\n`
        : "";
      return (
        `### 📅 ${entry.date}\n\n` +
        `**主题**: ${entry.topic}\n\n` +
        `**学习类型**: ${entry.priority}\n\n` +
        deadlineInfo +
        `**推荐材料**:\n\n${entry.materials.map((m) => `- ${m}`).join("\n")}`
      );
    })
    .join("\n\n---\n\n");

  return marked.parse(markdown);
}

function renderCalendar() {
  const year = currentMonth.getFullYear();
  const month = currentMonth.getMonth();

  const monthNames = [
    "一月",
    "二月",
    "三月",
    "四月",
    "五月",
    "六月",
    "七月",
    "八月",
    "九月",
    "十月",
    "十一月",
    "十二月",
  ];
  document.getElementById(
    "calendar-title"
  ).textContent = `${monthNames[month]} ${year}`;

  // 获取当月第一天和最后一天
  const firstDay = new Date(year, month, 1);
  const lastDay = new Date(year, month + 1, 0);
  const firstDayOfWeek = firstDay.getDay(); // 0 = 周日
  const daysInMonth = lastDay.getDate();

  // 获取上个月的天数
  const lastDayPrevMonth = new Date(year, month, 0).getDate();

  const grid = document.getElementById("calendar-grid");
  grid.innerHTML = "";

  const today = new Date();
  const isCurrentMonth =
    today.getFullYear() === year && today.getMonth() === month;
  const todayDate = today.getDate();

  for (let i = firstDayOfWeek - 1; i >= 0; i--) {
    const cell = document.createElement("div");
    cell.className = "calendar-cell dimmed";
    cell.textContent = lastDayPrevMonth - i;
    grid.appendChild(cell);
  }
  for (let day = 1; day <= daysInMonth; day++) {
    const cell = document.createElement("div");
    cell.className = "calendar-cell";

    if (isCurrentMonth && day === todayDate) {
      cell.classList.add("today");
    }

    const dateStr = `${year}-${String(month + 1).padStart(2, "0")}-${String(
      day
    ).padStart(2, "0")}`;
    const hasPlan = allPlans.some((plan) =>
      plan.data.some((entry) => entry.date === dateStr)
    );

    const hasDeadline = allPlans.some((plan) =>
      plan.data.some((entry) => entry.deadline === dateStr)
    );

    if (hasDeadline) {
      cell.style.fontWeight = "bold";
      cell.style.backgroundColor = "#ffebee";
      cell.style.color = "#d32f2f";
      cell.style.borderRadius = "4px";
      cell.title = "⏰ 截止日期";
    } else if (hasPlan) {
      cell.style.fontWeight = "bold";
      cell.style.color = "var(--primary-blue)";
      cell.title = "有学习计划";
    }

    cell.textContent = day;
    grid.appendChild(cell);
  }

  // 添加下个月的日期（灰色）
  const totalCells = firstDayOfWeek + daysInMonth;
  const remainingCells = totalCells % 7 === 0 ? 0 : 7 - (totalCells % 7);
  for (let day = 1; day <= remainingCells; day++) {
    const cell = document.createElement("div");
    cell.className = "calendar-cell dimmed";
    cell.textContent = day;
    grid.appendChild(cell);
  }

  updateCalendarStats();
}

function updateCalendarStats() {
  const year = currentMonth.getFullYear();
  const month = currentMonth.getMonth();

  const plansThisMonth = allPlans.filter((plan) => {
    const planDate = new Date(plan.date);
    return planDate.getFullYear() === year && planDate.getMonth() === month;
  }).length;

  document.getElementById(
    "calendar-stats"
  ).textContent = `本月学习计划：${plansThisMonth} 个 | 总计：${allPlans.length} 个`;
}

function showPlansTab() {
  document.getElementById("plans-tab").style.display = "block";
  document.getElementById("create-tab").style.display = "none";
  document.querySelectorAll(".feed-tab")[0].classList.add("active");
  document.querySelectorAll(".feed-tab")[1].classList.remove("active");
}

function showCreateTab() {
  document.getElementById("plans-tab").style.display = "none";
  document.getElementById("create-tab").style.display = "block";
  document.querySelectorAll(".feed-tab")[1].classList.add("active");
  document.querySelectorAll(".feed-tab")[0].classList.remove("active");
}

function showCreatePlanForm() {
  showCreateTab();
}

async function generatePlan() {
  const name = document.getElementById("plan-name").value.trim();
  const goals = document.getElementById("plan-goals").value.trim();
  const langChoice = document.getElementById("lang-select").value;
  const priority = document.getElementById("plan-priority").value;
  const deadlineDays = parseInt(document.getElementById("plan-deadline").value);

  if (!name || !goals) {
    alert("请输入姓名和学习目标");
    return;
  }

  const output = document.getElementById("plan-output");
  output.innerHTML =
    '<p style="text-align: center; color: var(--text-light);">⏳ 正在生成学习计划，请稍候...</p>';

  try {
    const response = await fetch(`${API_BASE}/api/learning-plan`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: name,
        goals: goals,
        lang_choice: langChoice,
        priority: priority,
        deadline_days: deadlineDays,
      }),
    });

    if (!response.ok) {
      throw new Error("生成失败");
    }

    const data = await response.json();
    const formattedPlan = formatPlanMarkdown(data.plan);

    output.innerHTML = `
            <div style="padding: 20px; background-color: var(--light-gray-bg); border-radius: 8px;">
              <h4 style="color: var(--primary-blue); margin-top: 0;">✅ ${data.message}</h4>
              <div class="markdown-content">${formattedPlan}</div>
              <button class="action-button" onclick="reloadPlans()" style="margin-top: 16px;">
                刷新计划列表
              </button>
            </div>
          `;
  } catch (error) {
    console.error("Error generating plan:", error);
    output.innerHTML = `
            <div style="padding: 20px; background-color: #fee; border-radius: 8px; color: #c00;">
              <p>❌ 生成学习计划失败，请稍后重试</p>
            </div>
          `;
  }
}
async function reloadPlans() {
  await loadPlans();
  showPlansTab();
}
