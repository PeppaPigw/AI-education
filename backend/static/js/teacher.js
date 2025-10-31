let courseData = null;
let studentData = [];
let currentUploadNode = null;

async function loadData() {
  try {
    const courseRes = await fetch("/api/knowledge-graph");
    courseData = await courseRes.json();

    const studentRes = await fetch("/api/students");
    studentData = await studentRes.json();

    renderCourseTree();
    renderStudents();
  } catch (error) {
    console.error("加载数据失败:", error);
  }
}

document.addEventListener("DOMContentLoaded", loadData);

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

function renderCourseTree() {
  const container = document.getElementById("courseTree");

  const rootHtml = `
                <div class="tree-node">
                    <div class="tree-item root" onclick="toggleNode(this)">
                        <span class="toggle-icon">▶</span>
                        <span>${courseData.root_name}</span>
                        <span class="resource-tag">${
                          courseData.children.length
                        } 个主题</span>
                    </div>
                    <div class="tree-children">
                        ${renderChildren(courseData.children, 1)}
                    </div>
                </div>
            `;

  container.innerHTML = rootHtml;
}

function renderChildren(children, level) {
  return children
    .map((child, index) => {
      const hasGrandchildren =
        child.grandchildren && child.grandchildren.length > 0;

      let html = `
                    <div class="tree-node">
                        <div class="tree-item level-${level}" onclick="toggleNode(this)">
                            ${
                              hasGrandchildren
                                ? '<span class="toggle-icon">▶</span>'
                                : '<span style="width: 12px;"></span>'
                            }
                            <span>${child.name}</span>
                        </div>
                `;

      if (hasGrandchildren) {
        html += `<div class="tree-children">`;
        if (child.grandchildren) {
          html += renderGrandchildren(child.grandchildren, level + 1);
        }
        html += `</div>`;
      }

      html += `</div>`;
      return html;
    })
    .join("");
}

function renderGrandchildren(grandchildren, level) {
  return grandchildren
    .map((grand) => {
      const hasGreatGrandchildren =
        grand["great-grandchildren"] && grand["great-grandchildren"].length > 0;

      let html = `
                    <div class="tree-node">
                        <div class="tree-item level-${level}" onclick="toggleNode(this)">
                            ${
                              hasGreatGrandchildren
                                ? '<span class="toggle-icon">▶</span>'
                                : '<span style="width: 12px;"></span>'
                            }
                            <span>${grand.name}</span>
                        </div>
                `;

      if (hasGreatGrandchildren) {
        html += `<div class="tree-children">`;
        grand["great-grandchildren"].forEach((great) => {
          const resources = Array.isArray(great.resource_path)
            ? great.resource_path
            : great.resource_path
            ? [great.resource_path]
            : [];
          const hasResources = resources.length > 0;

          html += `
                            <div class="tree-node">
                                <div class="tree-item level-${level + 1}">
                                    <span style="width: 12px;"></span>
                                    <span>${great.name}</span>
                                    <div class="action-btns">
                                        ${
                                          hasResources
                                            ? `<span class="resource-tag">${resources.length} 个资源</span>`
                                            : ""
                                        }
                                        <button class="add-btn" onclick="openUploadModal(event, '${
                                          great.name
                                        }')">+ 资源</button>
                                    </div>
                                </div>
                        `;

          if (hasResources) {
            html += `<div class="resource-links">`;
            resources.forEach((path, i) => {
              const isPDF = path.includes(".PDF") || path.includes(".pdf");
              const icon = isPDF ? "📄" : "🎥";
              const filename = isPDF ? path.split("/").pop() : `视频 ${i + 1}`;
              html += `
                      <div class="resource-item-actions">
                        <a href="${path}" class="resource-link" target="_blank" style="text-decoration: none; color: #7a6ad8;">${icon} ${filename}</a>
                        <button class="resource-delete-btn" onclick="deleteResource(event, '${great.name}', ${i})">删除</button>
                      </div>
                    `;
            });
            html += `</div>`;
          }

          html += `</div>`;
        });
        html += `</div>`;
      }

      html += `</div>`;
      return html;
    })
    .join("");
}

function toggleNode(element) {
  const children = element.nextElementSibling;
  if (children && children.classList.contains("tree-children")) {
    children.classList.toggle("show");
    const icon = element.querySelector(".toggle-icon");
    if (icon) {
      icon.classList.toggle("expanded");
    }
  }
}

function openUploadModal(event, nodeName) {
  event.stopPropagation();
  currentUploadNode = nodeName;
  document.getElementById("uploadNodeName").textContent = nodeName;
  document.getElementById("uploadModal").classList.add("show");
  document.getElementById("uploadStatus").textContent = "";
}

function closeUploadModal() {
  document.getElementById("uploadModal").classList.remove("show");
  document.getElementById("uploadFiles").value = "";
  currentUploadNode = null;
}

async function confirmUpload() {
  const fileInput = document.getElementById("uploadFiles");
  const files = fileInput.files;
  const statusDiv = document.getElementById("uploadStatus");

  if (files.length === 0) {
    statusDiv.textContent = "请选择文件";
    return;
  }

  statusDiv.textContent = "上传中...";

  const formData = new FormData();
  for (let file of files) {
    formData.append("files", file);
  }

  try {
    const response = await fetch(
      `/api/upload?node_name=${encodeURIComponent(currentUploadNode)}`,
      {
        method: "POST",
        body: formData,
      }
    );

    const data = await response.json();

    if (response.ok) {
      statusDiv.textContent = "✅ " + data.message;
      setTimeout(() => {
        closeUploadModal();
        loadData();
      }, 1500);
    } else {
      statusDiv.textContent = "❌ " + (data.detail || "上传失败");
    }
  } catch (error) {
    console.error("上传失败:", error);
    statusDiv.textContent = "❌ 上传失败";
  }
}

async function deleteResource(event, nodeName, resourceIndex) {
  event.stopPropagation();

  if (!confirm(`确定要删除该资源吗？`)) {
    return;
  }

  try {
    const response = await fetch("/api/delete-resource", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        node_name: nodeName,
        resource_index: resourceIndex,
      }),
    });

    const data = await response.json();

    if (response.ok) {
      alert("✅ 删除成功");
      loadData();
    } else {
      alert("❌ " + (data.detail || "删除失败"));
    }
  } catch (error) {
    console.error("删除失败:", error);
    alert("❌ 删除失败");
  }
}

function renderStudents() {
  const container = document.getElementById("studentsGrid");

  const html = studentData
    .map(
      (student) => `
                <div class="student-card">
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
                    
                    <div class="student-section">
                        <div class="section-title">学习目标</div>
                        <div class="goals-list">
                            ${student.learning_goals
                              .map(
                                (goal) =>
                                  `<span class="goal-tag">${goal}</span>`
                              )
                              .join("")}
                        </div>
                    </div>
                    
                    <div class="student-section">
                        <div class="section-title">课程偏好</div>
                        <div class="goals-list">
                            ${student.preference.course_type
                              .map(
                                (type) =>
                                  `<span class="goal-tag">${type.name}</span>`
                              )
                              .join("")}
                        </div>
                    </div>
                    
                    <button class="view-progress-btn" onclick="showProgress('${
                      student.stu_name
                    }')">
                        查看学习进度
                    </button>
                </div>
            `
    )
    .join("");

  container.innerHTML = html;
}

function showProgress(studentName) {
  const student = studentData.find((s) => s.stu_name === studentName);
  if (!student) return;

  document.getElementById("modalStudentName").textContent =
    studentName + " 的学习进度";
  document.getElementById("progressModal").classList.add("show");

  setTimeout(() => {
    const chart = echarts.init(document.getElementById("progressChart"));

    const series = student.progress.map((prog) => ({
      name: prog.topic,
      type: "line",
      smooth: true,
      symbol: "circle",
      symbolSize: 8,
      lineStyle: { width: 3 },
      data: prog.date,
    }));

    const option = {
      title: {
        text: "学习进度随时间变化",
        left: "center",
        textStyle: { fontSize: 16, color: "#333" },
      },
      tooltip: {
        trigger: "axis",
        backgroundColor: "rgba(50,50,50,0.9)",
        borderRadius: 8,
        textStyle: { color: "#fff" },
      },
      legend: {
        top: 40,
        data: student.progress.map((p) => p.topic),
      },
      grid: {
        left: "8%",
        right: "6%",
        bottom: "10%",
        top: "20%",
        containLabel: true,
      },
      xAxis: {
        type: "time",
        name: "时间",
        nameLocation: "middle",
        nameGap: 30,
        axisLine: { lineStyle: { color: "#aaa" } },
        axisLabel: {
          formatter: (value) => echarts.format.formatTime("MM-dd", value),
        },
      },
      yAxis: {
        type: "value",
        name: "完成进度 (%)",
        min: 0,
        max: 100,
        splitLine: { lineStyle: { type: "dashed", color: "#ddd" } },
      },
      series: series,
      color: ["#7a6ad8", "#91CC75", "#FAC858", "#EE6666", "#73C0DE"],
      animationDuration: 1800,
      animationEasing: "cubicOut",
    };

    chart.setOption(option);
    window.addEventListener("resize", () => chart.resize());
  }, 100);
}

function closeModal() {
  document.getElementById("progressModal").classList.remove("show");
}
