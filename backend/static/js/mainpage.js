console.log("AI-Education Main Page Loaded");

let kgData = null;
let allNodesData = {};
let expandedNodes = new Set();
let showRelations = true;
let selectedNode = null;
let kgSvg, kgG, kgSimulation;

const kgWidth =
  document.getElementById("knowledge-graph-container")?.clientWidth || 1200;
const kgHeight = 800;
const kgCenterX = kgWidth / 2;
const kgCenterY = kgHeight / 2;

const levelColors = [
  "#48cae4",
  "#8b5cf6",
  "#ff4d6d",
  "#f59e0b",
  "#10b981",
  "#06b6d4",
  "#f43f5e",
];

function initKGSVG() {
  d3.select("#graph-container-kg").selectAll("*").remove();

  kgSvg = d3
    .select("#graph-container-kg")
    .append("svg")
    .attr("width", kgWidth)
    .attr("height", kgHeight);

  kgSvg
    .append("defs")
    .append("marker")
    .attr("id", "arrowhead")
    .attr("viewBox", "0 -5 10 10")
    .attr("refX", 25)
    .attr("refY", 0)
    .attr("markerWidth", 8)
    .attr("markerHeight", 8)
    .attr("orient", "auto")
    .append("path")
    .attr("d", "M0,-5L10,0L0,5")
    .attr("fill", "#a855f7");

  kgG = kgSvg.append("g");

  const zoom = d3
    .zoom()
    .scaleExtent([0.1, 4])
    .on("zoom", (event) => {
      kgG.attr("transform", event.transform);
    });

  kgSvg.call(zoom);
}

function loadKnowledgeGraph() {
  fetch("/static/vendor/graph.json")
    .then((response) => {
      if (!response.ok) {
        throw new Error("网络响应失败");
      }
      return response.json();
    })
    .then((jsonData) => {
      kgData = jsonData;
      processKGData();
    })
    .catch((error) => {
      console.error("知识图谱加载错误:", error);
    });
}

function buildNodeTree(nodeList) {
  allNodesData = {};
  const childrenMap = {};

  nodeList.forEach((node) => {
    if (
      node.flag === undefined &&
      node.mocKgNodeAvgStatisticsDto?.flag !== undefined
    ) {
      node.flag = node.mocKgNodeAvgStatisticsDto.flag;
    }

    allNodesData[node.id] = node;
    if (!childrenMap[node.parentId]) {
      childrenMap[node.parentId] = [];
    }
    childrenMap[node.parentId].push(node);
  });

  nodeList.forEach((node) => {
    node.childrenList = childrenMap[node.id] || [];
  });

  return childrenMap;
}

function processKGData() {
  if (!kgData || !kgData.mocKgNodeDtoList) return;

  initKGSVG();
  expandedNodes.clear();

  const childrenMap = buildNodeTree(kgData.mocKgNodeDtoList);
  const rootNodes = childrenMap[-1] || [];
  if (rootNodes.length === 0) return;

  const root = rootNodes[0];
  expandedNodes.add(root.id);

  updateKGGraph();
}

function getVisibleNodesWithLevel(node, level = 0, result = []) {
  const nodeWithLevel = { ...node, level };
  result.push(nodeWithLevel);

  if (
    expandedNodes.has(node.id) &&
    node.childrenList &&
    node.childrenList.length > 0
  ) {
    node.childrenList.forEach((child) => {
      getVisibleNodesWithLevel(child, level + 1, result);
    });
  }

  return result;
}

function radialPosition(
  level,
  index,
  total,
  parentX = kgCenterX,
  parentY = kgCenterY,
  parentAngle = 0,
  angleSpan = Math.PI * 2
) {
  if (level === 0) {
    return { x: kgCenterX, y: kgCenterY };
  }

  const radius = 280 + (level - 1) * 250;
  const startAngle = parentAngle - angleSpan / 2;
  const angle = startAngle + (index + 0.5) * (angleSpan / total);

  return {
    x: parentX + radius * Math.cos(angle),
    y: parentY + radius * Math.sin(angle),
    targetAngle: angle,
  };
}

function updateKGGraph() {
  const rootNodes = kgData.mocKgNodeDtoList.filter((n) => n.parentId === -1);
  if (rootNodes.length === 0) return;

  const root = rootNodes[0];
  const visibleNodes = getVisibleNodesWithLevel(root);

  const nodesByLevel = {};
  visibleNodes.forEach((node) => {
    if (!nodesByLevel[node.level]) {
      nodesByLevel[node.level] = [];
    }
    nodesByLevel[node.level].push(node);
  });

  visibleNodes.forEach((node, i) => {
    const nodesInLevel = nodesByLevel[node.level];
    const indexInLevel = nodesInLevel.indexOf(node);
    const parent =
      node.parentId !== -1
        ? visibleNodes.find((n) => n.id === node.parentId)
        : null;

    const pos = radialPosition(
      node.level,
      indexInLevel,
      nodesInLevel.length,
      parent ? parent.x : kgCenterX,
      parent ? parent.y : kgCenterY
    );

    node.x = pos.x;
    node.y = pos.y;
    node.targetRadius = 280 + node.level * 250;
    node.radius = Math.max(70 / Math.pow(1.5, node.level), 18);
  });

  const links = [];
  visibleNodes.forEach((node) => {
    if (node.parentId !== -1) {
      const parent = visibleNodes.find((n) => n.id === node.parentId);
      if (parent) {
        links.push({ source: parent.id, target: node.id });
      }
    }
  });

  const visibleNodeIds = new Set(visibleNodes.map((n) => n.id));
  const relations = (kgData.mocKgRelationDtoList || [])
    .filter(
      (rel) =>
        visibleNodeIds.has(rel.fromNodeId) && visibleNodeIds.has(rel.toNodeId)
    )
    .map((rel) => ({
      source: rel.fromNodeId,
      target: rel.toNodeId,
      relationType: rel.relationType,
    }));

  if (kgSimulation) kgSimulation.stop();

  kgSimulation = d3
    .forceSimulation(visibleNodes)
    .force(
      "link",
      d3
        .forceLink(links)
        .id((d) => d.id)
        .distance(120)
        .strength(0.3)
    )
    .force("charge", d3.forceManyBody().strength(-300))
    .force(
      "collision",
      d3
        .forceCollide()
        .radius((d) => d.radius + 20)
        .strength(0.9)
    )
    .force(
      "radial",
      d3.forceRadial((d) => d.targetRadius, kgCenterX, kgCenterY).strength(0.8)
    )
    .force("center", d3.forceCenter(kgCenterX, kgCenterY).strength(0.05))
    .alphaDecay(0.02);

  const linkElements = kgG
    .selectAll(".kg-link")
    .data(links, (d) => `${d.source}-${d.target}`)
    .join("line")
    .attr("class", "kg-link");

  const relationElements = kgG
    .selectAll(".relation-link")
    .data(relations, (d) => `${d.source}-${d.target}`)
    .join("path")
    .attr("class", (d) => `relation-link${showRelations ? "" : " hidden"}`)
    .attr("marker-end", showRelations ? "url(#arrowhead)" : "");

  const relationLabelElements = kgG
    .selectAll(".relation-label")
    .data(relations, (d) => `${d.source}-${d.target}`)
    .join("text")
    .attr("class", (d) => `relation-label${showRelations ? "" : " hidden"}`)
    .text("前置");

  const nodeElements = kgG
    .selectAll(".kg-node")
    .data(visibleNodes, (d) => d.id)
    .join("g")
    .attr("class", "kg-node")
    .call(kgDrag(kgSimulation));

  nodeElements.selectAll("*").remove();

  nodeElements
    .append("circle")
    .attr("r", (d) => d.radius)
    .attr("fill", (d) => levelColors[Math.min(d.level, levelColors.length - 1)])
    .attr("stroke", (d) => (d.flag === 1 ? "#ff0000ff" : "none"))
    .attr("stroke-width", (d) => (d.flag === 1 ? 5 : 0))
    .style("filter", (d) =>
      d.flag === 1 ? "drop-shadow(0 0 8px #ff0000ff)" : "none"
    );

  nodeElements
    .append("text")
    .attr("dy", "0.35em")
    .attr("font-size", (d) => `${Math.max(d.radius / 3.2, 11)}px`)
    .text((d) => {
      const maxLen = Math.floor(d.radius / 4.5);
      return d.nodeName.length > maxLen
        ? d.nodeName.substring(0, maxLen - 1) + "…"
        : d.nodeName;
    });

  nodeElements
    .filter((d) => d.childrenList && d.childrenList.length > 0)
    .append("circle")
    .attr("class", "expand-indicator")
    .attr("cx", (d) => d.radius * 0.7)
    .attr("cy", (d) => -d.radius * 0.7)
    .attr("r", 11)
    .attr("fill", (d) => (expandedNodes.has(d.id) ? "#10b981" : "#f59e0b"))
    .attr("stroke", "#ffffff")
    .attr("stroke-width", 2.5);

  nodeElements
    .filter((d) => d.childrenList && d.childrenList.length > 0)
    .append("text")
    .attr("x", (d) => d.radius * 0.7)
    .attr("y", (d) => -d.radius * 0.7)
    .attr("dy", "0.35em")
    .attr("text-anchor", "middle")
    .attr("fill", "#ffffff")
    .attr("font-weight", "bold")
    .attr("font-size", "16px")
    .style("pointer-events", "none")
    .text((d) => (expandedNodes.has(d.id) ? "−" : "+"));

  nodeElements.on("click", (event, d) => {
    event.stopPropagation();
    if (d.childrenList && d.childrenList.length > 0) {
      toggleKGNode(d);
    }
    showKGDescription(d);
  });

  kgSimulation.on("tick", () => {
    linkElements
      .attr("x1", (d) => d.source.x)
      .attr("y1", (d) => d.source.y)
      .attr("x2", (d) => d.target.x)
      .attr("y2", (d) => d.target.y);

    relationElements.attr("d", (d) => {
      const sourceNode = visibleNodes.find((n) => n.id === d.source);
      const targetNode = visibleNodes.find((n) => n.id === d.target);
      if (!sourceNode || !targetNode) return "";

      const dx = targetNode.x - sourceNode.x;
      const dy = targetNode.y - sourceNode.y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      const offsetX = (dx / dist) * targetNode.radius;
      const offsetY = (dy / dist) * targetNode.radius;

      return `M ${sourceNode.x} ${sourceNode.y} L ${targetNode.x - offsetX} ${
        targetNode.y - offsetY
      }`;
    });

    relationLabelElements
      .attr("x", (d) => {
        const sourceNode = visibleNodes.find((n) => n.id === d.source);
        const targetNode = visibleNodes.find((n) => n.id === d.target);
        return sourceNode && targetNode ? (sourceNode.x + targetNode.x) / 2 : 0;
      })
      .attr("y", (d) => {
        const sourceNode = visibleNodes.find((n) => n.id === d.source);
        const targetNode = visibleNodes.find((n) => n.id === d.target);
        return sourceNode && targetNode
          ? (sourceNode.y + targetNode.y) / 2 - 5
          : 0;
      });

    nodeElements.attr("transform", (d) => `translate(${d.x}, ${d.y})`);
  });

  updateKGStats(visibleNodes.length);
}

function toggleKGNode(nodeData) {
  if (expandedNodes.has(nodeData.id)) {
    expandedNodes.delete(nodeData.id);
    collapseKGChildren(nodeData.id);
  } else {
    expandedNodes.add(nodeData.id);
  }
  updateKGGraph();
}

function collapseKGChildren(nodeId) {
  const nodeData = allNodesData[nodeId];
  if (nodeData && nodeData.childrenList) {
    nodeData.childrenList.forEach((child) => {
      expandedNodes.delete(child.id);
      collapseKGChildren(child.id);
    });
  }
}

function expandAllNodes() {
  Object.values(allNodesData).forEach((node) => {
    if (node.childrenList && node.childrenList.length > 0) {
      expandedNodes.add(node.id);
    }
  });
  updateKGGraph();
}

function collapseAllNodes() {
  const root = kgData.mocKgNodeDtoList.find((n) => n.parentId === -1);
  expandedNodes.clear();
  expandedNodes.add(root.id);
  updateKGGraph();
}

function toggleRelations() {
  showRelations = !showRelations;
  const btn = document.getElementById("relationBtn");
  btn.textContent = showRelations ? "隐藏关系" : "显示关系";
  btn.classList.toggle("active", showRelations);

  d3.selectAll(".relation-link")
    .classed("hidden", !showRelations)
    .attr("marker-end", showRelations ? "url(#arrowhead)" : "");

  d3.selectAll(".relation-label").classed("hidden", !showRelations);
}

function showKGDescription(nodeData) {
  selectedNode = nodeData;
  d3.selectAll(".kg-node").classed("selected", false);
  d3.selectAll(".kg-node")
    .filter((d) => d.id === nodeData.id)
    .classed("selected", true);

  document.getElementById("node-title").textContent = nodeData.nodeName;
  document.getElementById("node-description").textContent =
    nodeData.description || "暂无描述";
  document.getElementById("description-panel").classList.add("show");
}

function updateKGStats(visibleCount) {
  document.getElementById("total-nodes").textContent =
    Object.keys(allNodesData).length;
  document.getElementById("visible-nodes").textContent = visibleCount;
}

function kgDrag(simulation) {
  function dragstarted(event) {
    if (!event.active) simulation.alphaTarget(0.3).restart();
    event.subject.fx = event.subject.x;
    event.subject.fy = event.subject.y;
  }

  function dragged(event) {
    event.subject.fx = event.x;
    event.subject.fy = event.y;
  }

  function dragended(event) {
    if (!event.active) simulation.alphaTarget(0);
    event.subject.fx = null;
    event.subject.fy = null;
  }

  return d3
    .drag()
    .on("start", dragstarted)
    .on("drag", dragged)
    .on("end", dragended);
}

function findCurrentNodes(graphData) {
  let currentChapter = null;
  let currentSection = null;
  let currentPoint = null;

  const children = graphData.children || [];

  for (let i = 0; i < children.length; i++) {
    const chapter = children[i];

    if (chapter.flag === "0" && !currentChapter) {
      currentChapter = {
        name: chapter.name,
        index: i,
        total: children.length,
        completed: i,
      };
    }

    const grandchildren = chapter.grandchildren || [];
    for (let j = 0; j < grandchildren.length; j++) {
      const section = grandchildren[j];

      if (
        section.flag === "0" &&
        !currentSection &&
        (!currentChapter || currentChapter.index === i)
      ) {
        currentSection = {
          name: section.name,
          index: j,
          total: grandchildren.length,
          completed: j,
          chapterName: chapter.name,
        };
      }

      function findFirstIncompletePoint(node, depth = 0) {
        const greatGrandchildren = node["great-grandchildren"] || [];
        for (let k = 0; k < greatGrandchildren.length; k++) {
          const point = greatGrandchildren[k];
          if (point.flag === "0" && !currentPoint) {
            currentPoint = {
              name: point.name,
              index: k,
              total: greatGrandchildren.length,
              completed: k,
              sectionName: node.name,
            };
            return true;
          }
          if (findFirstIncompletePoint(point, depth + 1)) {
            return true;
          }
        }
        return false;
      }

      if (
        (!currentSection || currentSection.index === j) &&
        (!currentChapter || currentChapter.index === i)
      ) {
        findFirstIncompletePoint(section);
      }
    }
  }

  if (!currentChapter && children.length > 0) {
    currentChapter = {
      name: children[0].name,
      index: 0,
      total: children.length,
      completed: 0,
    };
  }

  return { currentChapter, currentSection, currentPoint };
}

fetch("/api/learning-progress")
  .then((response) => response.json())
  .then((data) => {
    console.log("Learning progress data loaded:", data);

    document.getElementById(
      "chapter-progress"
    ).textContent = `已完成 ${data.chapters.completed}/${data.chapters.total} 章 (${data.chapters.progress}%)`;
    document.getElementById("chapter-progress-bar").style.width =
      data.chapters.progress + "%";

    document.getElementById(
      "section-progress"
    ).textContent = `已完成 ${data.sections.completed}/${data.sections.total} 节 (${data.sections.progress}%)`;
    document.getElementById("section-progress-bar").style.width =
      data.sections.progress + "%";

    document.getElementById(
      "point-progress"
    ).textContent = `已完成 ${data.points.completed}/${data.points.total} 个 (${data.points.progress}%)`;
    document.getElementById("point-progress-bar").style.width =
      data.points.progress + "%";
  })
  .catch((error) => {
    console.error("Failed to load learning progress:", error);
    document.getElementById("chapter-progress").textContent = "加载失败";
    document.getElementById("section-progress").textContent = "加载失败";
    document.getElementById("point-progress").textContent = "加载失败";
  });

fetch("/api/knowledge-graph")
  .then((response) => response.json())
  .then((data) => {
    console.log("Knowledge graph data loaded:", data);
    if (data && (data.name || data.root_name)) {
      if (data.name && !data.root_name) {
        data.root_name = data.name;
      }

      const { currentChapter, currentSection, currentPoint } =
        findCurrentNodes(data);

      if (currentChapter) {
        document.getElementById("current-chapter-name").textContent =
          currentChapter.name;
        const chapterProgress = (
          (currentChapter.completed / currentChapter.total) *
          100
        ).toFixed(1);
        document.getElementById("current-chapter-desc").textContent = `章节 ${
          currentChapter.index + 1
        }/${currentChapter.total} · ${chapterProgress}% 已完成`;
        document.getElementById("current-chapter-progress").style.width =
          chapterProgress + "%";
      }

      if (currentSection) {
        document.getElementById("current-section-name").textContent =
          currentSection.name;
        const sectionProgress = (
          (currentSection.completed / currentSection.total) *
          100
        ).toFixed(1);
        document.getElementById("current-section-desc").textContent = `小节 ${
          currentSection.index + 1
        }/${currentSection.total} · ${sectionProgress}% 已完成`;
        document.getElementById("current-section-progress").style.width =
          sectionProgress + "%";
      } else {
        document.getElementById("current-section-name").textContent =
          "暂无小节";
        document.getElementById("current-section-desc").textContent =
          "等待开始学习";
      }

      if (currentPoint) {
        document.getElementById("current-point-name").textContent =
          currentPoint.name;
        const pointProgress = (
          (currentPoint.completed / currentPoint.total) *
          100
        ).toFixed(1);
        document.getElementById("current-point-desc").textContent = `知识点 ${
          currentPoint.index + 1
        }/${currentPoint.total} · ${pointProgress}% 已完成`;
        document.getElementById("current-point-progress").style.width =
          pointProgress + "%";
      } else {
        document.getElementById("current-point-name").textContent =
          "暂无知识点";
        document.getElementById("current-point-desc").textContent =
          "等待开始学习";
      }
    }
  })
  .catch((error) => console.error("Failed to load knowledge graph:", error));

loadKnowledgeGraph();
