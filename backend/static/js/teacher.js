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
    renderHeatmap();
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

function renderHeatmap() {
  const topicStats = {};

  studentData.forEach((student) => {
    if (!student.progress) return;

    student.progress.forEach((prog) => {
      const topic = prog.topic;
      if (!topicStats[topic]) {
        topicStats[topic] = {
          totalProgress: 0,
          studentCount: 0,
          progressList: [],
        };
      }

      const latestProgress = prog.date
        .filter((d) => d[0] !== null && d[1] !== null)
        .map((d) => d[1])
        .pop();

      if (latestProgress !== undefined) {
        topicStats[topic].totalProgress += latestProgress;
        topicStats[topic].studentCount += 1;
        topicStats[topic].progressList.push(latestProgress);
      }
    });
  });

  const topics = Object.keys(topicStats);
  const heatmapData = topics.map((topic, index) => {
    const stats = topicStats[topic];
    const avgProgress =
      stats.studentCount > 0 ? stats.totalProgress / stats.studentCount : 0;
    return {
      name: topic,
      value: [index, avgProgress, stats.studentCount],
      avgProgress: avgProgress,
      studentCount: stats.studentCount,
    };
  });

  const heatmapChart = echarts.init(document.getElementById("heatmapChart"));

  const heatmapOption = {
    title: {
      text: "课程章节学习热度分布",
      left: "center",
      textStyle: { fontSize: 18, color: "#333", fontWeight: 600 },
    },
    tooltip: {
      trigger: "item",
      backgroundColor: "rgba(50,50,50,0.9)",
      borderRadius: 8,
      textStyle: { color: "#fff" },
      formatter: function (params) {
        const dataIndex = params.dataIndex;
        const topic = topics[dataIndex];
        const stats = topicStats[topic];
        return `
          <div style="padding: 5px;">
            <strong>${topic}</strong><br/>
            平均进度: ${Math.round(
              stats.totalProgress / stats.studentCount
            )}%<br/>
            学习人数: ${stats.studentCount}人
          </div>
        `;
      },
    },
    grid: {
      left: "3%",
      right: "7%",
      bottom: "3%",
      top: "15%",
      containLabel: true,
    },
    xAxis: {
      type: "value",
      name: "平均学习进度 (%)",
      min: 0,
      max: 100,
      axisLine: { lineStyle: { color: "#aaa" } },
      splitLine: { lineStyle: { type: "dashed", color: "#ddd" } },
    },
    yAxis: {
      type: "category",
      data: topics,
      axisLine: { lineStyle: { color: "#aaa" } },
      axisLabel: {
        fontSize: 12,
        color: "#666",
      },
    },
    series: [
      {
        type: "bar",
        data: heatmapData.map((d) => d.avgProgress),
        itemStyle: {
          color: function (params) {
            const value = params.value;
            if (value >= 80) return "#7a6ad8";
            if (value >= 60) return "#91CC75";
            if (value >= 40) return "#FAC858";
            if (value >= 20) return "#EE6666";
            return "#ccc";
          },
          borderRadius: [0, 4, 4, 0],
        },
        label: {
          show: true,
          position: "right",
          formatter: function (params) {
            const topic = topics[params.dataIndex];
            const stats = topicStats[topic];
            const avgProgress = Math.round(
              stats.totalProgress / stats.studentCount
            );
            return `${avgProgress}% (${stats.studentCount}人)`;
          },
          fontSize: 11,
          color: "#666",
        },
        barWidth: "60%",
        animationDuration: 1500,
        animationEasing: "cubicOut",
      },
    ],
  };

  heatmapChart.setOption(heatmapOption);
  window.addEventListener("resize", () => heatmapChart.resize());

  renderScoresDistribution();
}

function renderScoresDistribution() {
  const knowledgePoints = [];
  const scoreStats = [];

  function collectKnowledgePoints(children, parentName = "") {
    if (!children) return;

    children.forEach((child) => {
      if (child.grandchildren) {
        child.grandchildren.forEach((grand) => {
          if (grand["great-grandchildren"]) {
            grand["great-grandchildren"].forEach((great) => {
              knowledgePoints.push({
                name: great.name,
                parent: grand.name,
                chapter: child.name,
              });
            });
          }
        });
      }
    });
  }

  if (courseData && courseData.children) {
    collectKnowledgePoints(courseData.children);
  }

  knowledgePoints.forEach((point, index) => {
    const scores = [];
    let passCount = 0;
    let failCount = 0;
    let notLearnedCount = 0;

    studentData.forEach((student) => {
      if (student.scores && student.scores[index] !== undefined) {
        const score = student.scores[index];
        if (score === -1) {
          notLearnedCount++;
        } else if (score === 0) {
          failCount++;
        } else {
          passCount++;
          scores.push(score);
        }
      }
    });

    const avgScore =
      scores.length > 0 ? scores.reduce((a, b) => a + b, 0) / scores.length : 0;

    scoreStats.push({
      name: point.name,
      chapter: point.chapter,
      avgScore: avgScore,
      passCount: passCount,
      failCount: failCount,
      notLearnedCount: notLearnedCount,
      totalStudents: studentData.length,
    });
  });

  const topScores = scoreStats
    .filter((s) => s.passCount > 0)
    .sort((a, b) => b.avgScore - a.avgScore)
    .slice(0, 10);

  const bottomScores = scoreStats
    .filter((s) => s.passCount > 0)
    .sort((a, b) => a.avgScore - b.avgScore)
    .slice(0, 10);

  const combinedScores = [...topScores, ...bottomScores];

  const scoresChart = echarts.init(document.getElementById("scoresChart"));

  const scoresOption = {
    title: {
      text: "知识点平均成绩 TOP 10 & BOTTOM 10",
      left: "center",
      textStyle: { fontSize: 18, color: "#333", fontWeight: 600 },
    },
    tooltip: {
      trigger: "axis",
      backgroundColor: "rgba(50,50,50,0.9)",
      borderRadius: 8,
      textStyle: { color: "#fff" },
      axisPointer: {
        type: "shadow",
      },
      formatter: function (params) {
        const data = combinedScores[params[0].dataIndex];
        return `
          <div style="padding: 5px;">
            <strong>${data.name}</strong><br/>
            章节: ${data.chapter}<br/>
            平均分: ${Math.round(data.avgScore)}<br/>
            通过: ${data.passCount}人<br/>
            未通过: ${data.failCount}人<br/>
            未学习: ${data.notLearnedCount}人
          </div>
        `;
      },
    },
    grid: {
      left: "3%",
      right: "4%",
      bottom: "3%",
      top: "15%",
      containLabel: true,
    },
    xAxis: {
      type: "category",
      data: combinedScores.map((s) => s.name),
      axisLabel: {
        rotate: 45,
        fontSize: 11,
        color: "#666",
        interval: 0,
      },
      axisLine: { lineStyle: { color: "#aaa" } },
    },
    yAxis: {
      type: "value",
      name: "平均成绩",
      min: 0,
      max: 10,
      axisLine: { lineStyle: { color: "#aaa" } },
      splitLine: { lineStyle: { type: "dashed", color: "#ddd" } },
    },
    series: [
      {
        type: "bar",
        data: combinedScores.map((s, index) => ({
          value: s.avgScore,
          itemStyle: {
            color:
              index < 10
                ? new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                    { offset: 0, color: "#7a6ad8" },
                    { offset: 1, color: "#9b8ee5" },
                  ])
                : new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                    { offset: 0, color: "#ff6b6b" },
                    { offset: 1, color: "#ff8787" },
                  ]),
            borderRadius: [4, 4, 0, 0],
          },
        })),
        label: {
          show: true,
          position: "top",
          formatter: function (params) {
            return Math.round(params.value);
          },
          fontSize: 10,
          color: "#666",
        },
        barWidth: "50%",
        animationDuration: 1500,
        animationEasing: "cubicOut",
      },
    ],
  };

  scoresChart.setOption(scoresOption);
  window.addEventListener("resize", () => scoresChart.resize());
}
