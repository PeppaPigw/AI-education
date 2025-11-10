let treeData = null;
let svg = null;
let g = null;
let root = null;
let i = 0;

const COLORS = {
  root: "#2b6cb0",
  children: "#4299e1",
  grandchildren: "#805ad5",
  greatGrandchildren: "#f6ad55",
  learned: "#48bb78",
};

function initializeGraph(data) {
  console.log("Initializing graph with data:", data);
  treeData = data;

  d3.select("#knowledge-graph").selectAll("*").remove();

  const container = document.getElementById("knowledge-graph");
  const width = container.clientWidth || 800;
  const height = container.clientHeight || 600;

  console.log("Container dimensions:", width, height);

  svg = d3
    .select("#knowledge-graph")
    .append("svg")
    .attr("width", width)
    .attr("height", height);

  g = svg
    .append("g")
    .attr("transform", `translate(${width / 2}, ${height / 2})`);

  svg.call(
    d3.zoom().on("zoom", (event) => {
      g.attr("transform", event.transform);
    })
  );

  // 添加展开所有按钮
  d3.select("#knowledge-graph")
    .append("div")
    .attr("class", "expand-all-btn")
    .style("position", "absolute")
    .style("top", "10px")
    .style("right", "10px")
    .style("padding", "8px 16px")
    .style("background", "#4299e1")
    .style("color", "white")
    .style("border-radius", "8px")
    .style("cursor", "pointer")
    .style("font-size", "14px")
    .style("z-index", "1000")
    .text("展开全部")
    .on("click", expandAll);

  root = d3.hierarchy(convertToD3Format(treeData));
  root.x0 = 0;
  root.y0 = 0;

  if (root.children) {
    root.children.forEach(collapse);
  }

  update(root);
  console.log("Graph initialized successfully");
}

function convertToD3Format(data) {
  const result = {
    name: data.root_name,
    type: "root",
    flag: "1",
    resource_path: [],
    children: [],
  };

  if (data.children) {
    result.children = data.children.map((child) => ({
      name: child.name,
      type: "children",
      flag: child.flag,
      resource_path: child.resource_path || [],
      children: (child.grandchildren || []).map((gc) => ({
        name: gc.name,
        type: "grandchildren",
        flag: gc.flag,
        resource_path: gc.resource_path || [],
        children: (gc["great-grandchildren"] || []).map((ggc) => ({
          name: ggc.name,
          type: "greatGrandchildren",
          flag: ggc.flag,
          resource_path: ggc.resource_path || [],
          children: null,
        })),
      })),
    }));
  }

  return result;
}

function collapse(d) {
  if (d.children) {
    d._children = d.children;
    d._children.forEach(collapse);
    d.children = null;
  }
}

function expand(d) {
  if (d._children) {
    d.children = d._children;
    d._children = null;
  }
  if (d.children) {
    d.children.forEach(expand);
  }
}

function expandAll() {
  expand(root);
  update(root);
}

function update(source) {
  const duration = 200;

  // 使用径向布局
  const radius =
    Math.min(
      document.getElementById("knowledge-graph").clientWidth,
      document.getElementById("knowledge-graph").clientHeight
    ) /
      1 -
    100;

  const tree = d3
    .tree()
    .size([2 * Math.PI, radius])
    .separation((a, b) => (a.parent == b.parent ? 1 : 2) / a.depth);

  const treeData = tree(root);
  const nodes = treeData.descendants();
  const links = treeData.descendants().slice(1);

  // 更新节点
  const node = g.selectAll("g.node").data(nodes, (d) => d.id || (d.id = ++i));

  const nodeEnter = node
    .enter()
    .append("g")
    .attr("class", "node")
    .attr("transform", (d) => {
      return `translate(${radialPoint(source.x0 || 0, source.y0 || 0)})`;
    })
    .on("click", click);

  nodeEnter
    .append("circle")
    .attr("r", 1e-6)
    .style("fill", (d) => (d.data.flag === "1" ? getNodeColor(d) : "#fff"))
    .style("stroke", (d) => getNodeColor(d))
    .style("stroke-width", "3px")
    .style("cursor", "pointer")
    .style("filter", "drop-shadow(0 2px 4px rgba(0,0,0,0.1))");

  nodeEnter
    .append("text")
    .attr("dy", ".31em")
    .attr("x", (d) => (d.x < Math.PI ? 12 : -12))
    .attr("text-anchor", (d) => (d.x < Math.PI ? "start" : "end"))
    .text((d) => d.data.name)
    .style("fill-opacity", 1e-6)
    .style("font-size", "13px")
    .style("font-weight", (d) => (d.data.flag === "1" ? "bold" : "normal"))
    .style("fill", "#2d3748")
    .style("text-shadow", "0 1px 2px rgba(255,255,255,0.8)");

  const nodeUpdate = nodeEnter.merge(node);

  nodeUpdate
    .transition()
    .duration(duration)
    .attr("transform", (d) => `translate(${radialPoint(d.x, d.y)})`);

  nodeUpdate
    .select("circle")
    .attr("r", (d) => getNodeRadius(d))
    .style("fill", (d) => (d.data.flag === "1" ? getNodeColor(d) : "#fff"))
    .style("stroke", (d) => getNodeColor(d))
    .style("stroke-width", (d) => (d.data.flag === "1" ? "4px" : "3px"));

  nodeUpdate.select("text").style("fill-opacity", 1);

  const nodeExit = node
    .exit()
    .transition()
    .duration(duration)
    .attr("transform", (d) => `translate(${radialPoint(source.x, source.y)})`)
    .remove();

  nodeExit.select("circle").attr("r", 1e-6);
  nodeExit.select("text").style("fill-opacity", 1e-6);

  // 更新连线
  const link = g.selectAll("path.link").data(links, (d) => d.id);

  const linkEnter = link
    .enter()
    .insert("path", "g")
    .attr("class", "link")
    .attr("d", (d) => {
      const o = { x: source.x0 || 0, y: source.y0 || 0 };
      return radialDiagonal(o, o);
    })
    .style("fill", "none")
    .style("stroke", "#a0aec0")
    .style("stroke-width", "2px")
    .style("opacity", 0.6);

  const linkUpdate = linkEnter.merge(link);

  linkUpdate
    .transition()
    .duration(duration)
    .attr("d", (d) => radialDiagonal(d, d.parent));

  link
    .exit()
    .transition()
    .duration(duration)
    .attr("d", (d) => {
      const o = { x: source.x, y: source.y };
      return radialDiagonal(o, o);
    })
    .remove();

  nodes.forEach((d) => {
    d.x0 = d.x;
    d.y0 = d.y;
  });
}

function radialPoint(x, y) {
  return [(y = +y) * Math.cos((x -= Math.PI / 2)), y * Math.sin(x)];
}

function radialDiagonal(s, d) {
  const sPoint = radialPoint(s.x, s.y);
  const dPoint = radialPoint(d.x, d.y);
  return `M ${sPoint[0]},${sPoint[1]}
          C ${sPoint[0]},${sPoint[1]}
            ${dPoint[0]},${dPoint[1]}
            ${dPoint[0]},${dPoint[1]}`;
}

function getNodeColor(d) {
  if (d.data.flag === "1") {
    return COLORS.learned;
  }
  return COLORS[d.data.type] || "#cbd5e0";
}

function getNodeRadius(d) {
  const radiusMap = {
    root: 80,
    children: 30,
    grandchildren: 20,
    greatGrandchildren: 10,
  };
  return radiusMap[d.data.type] || 8;
}

function click(event, d) {
  console.log(
    "Node clicked:",
    d.data.name,
    "Type:",
    d.data.type,
    "Resources:",
    d.data.resource_path
  );

  // 总是尝试显示资源（包括空数组和字符串）
  showNodeResources(d.data);

  // 再处理展开/折叠
  if (d.children) {
    d._children = d.children;
    d.children = null;
  } else if (d._children) {
    d.children = d._children;
    d._children = null;
  }

  update(d);
}

function showNodeResources(nodeData) {
  if (window.handleNodeClick) {
    window.handleNodeClick(nodeData);
  }
}

window.initializeGraph = initializeGraph;

let data = null;
let allNodesData = {};
let expandedNodes = new Set();
let showRelations = true;
let selectedNode = null;
let simulation;

const width = window.innerWidth;
const height = window.innerHeight;
const centerX = width / 2;
const centerY = height / 2;

const levelColors = [
  "#3b82f6", // 蓝色 - Level 0
  "#8b5cf6", // 紫色 - Level 1
  "#fcb9b2", // 粉色 - Level 2
  "#f59e0b", // 橙色 - Level 3
  "#10b981", // 绿色 - Level 4
  "#06b6d4", // 青色 - Level 5
  "#f43f5e", // 红色 - Level 6+
];

function initSVG() {
  d3.select("#graph-container").selectAll("*").remove();

  svg = d3
    .select("#graph-container")
    .append("svg")
    .attr("width", width)
    .attr("height", height);

  svg
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

  g = svg.append("g");

  const zoom = d3
    .zoom()
    .scaleExtent([0.1, 4])
    .on("zoom", (event) => {
      g.attr("transform", event.transform);
    });

  svg.call(zoom);
}

// 自动加载 JSON 文件
function loadJSON() {
  fetch("/static/vendor/graph.json")
    .then((response) => {
      if (!response.ok) {
        throw new Error("网络响应失败");
      }
      return response.json();
    })
    .then((jsonData) => {
      data = jsonData;
      processData();
    })
    .catch((error) => {
      console.error("JSON 加载错误:", error);
      alert("JSON 加载错误: " + error.message);
    });
}

// 页面加载完成后自动加载数据
window.addEventListener("DOMContentLoaded", () => {
  loadJSON();
});

function buildNodeTree(nodeList) {
  allNodesData = {};
  const childrenMap = {};

  nodeList.forEach((node) => {
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

function processData() {
  if (!data || !data.mocKgNodeDtoList) return;

  initSVG();
  expandedNodes.clear();

  const childrenMap = buildNodeTree(data.mocKgNodeDtoList);
  const rootNodes = childrenMap[-1] || [];
  if (rootNodes.length === 0) return;

  const root = rootNodes[0];
  expandedNodes.add(root.id);

  updateGraph();
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
  parentX = centerX,
  parentY = centerY,
  parentAngle = 0,
  angleSpan = Math.PI * 2
) {
  if (level === 0) {
    return { x: centerX, y: centerY };
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

function updateGraph() {
  const rootNodes = data.mocKgNodeDtoList.filter((n) => n.parentId === -1);
  if (rootNodes.length === 0) return;

  const root = rootNodes[0];
  const visibleNodes = getVisibleNodesWithLevel(root);

  // 计算每个节点的层级和理想位置
  const nodesByLevel = {};
  visibleNodes.forEach((node) => {
    if (!nodesByLevel[node.level]) {
      nodesByLevel[node.level] = [];
    }
    nodesByLevel[node.level].push(node);
  });

  // 为每个节点设置初始位置和目标半径
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
      parent ? parent.x : centerX,
      parent ? parent.y : centerY
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
  const relations = (data.mocKgRelationDtoList || [])
    .filter(
      (rel) =>
        visibleNodeIds.has(rel.fromNodeId) && visibleNodeIds.has(rel.toNodeId)
    )
    .map((rel) => ({
      source: rel.fromNodeId,
      target: rel.toNodeId,
      relationType: rel.relationType,
    }));

  if (simulation) simulation.stop();

  // 创建力导向模拟，保持径向结构
  simulation = d3
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
      d3.forceRadial((d) => d.targetRadius, centerX, centerY).strength(0.8)
    )
    .force("center", d3.forceCenter(centerX, centerY).strength(0.05))
    .alphaDecay(0.02);

  // 绘制层级连线
  const linkElements = g
    .selectAll(".link")
    .data(links, (d) => `${d.source}-${d.target}`)
    .join("line")
    .attr("class", "link");

  // 绘制关系连线
  const relationElements = g
    .selectAll(".relation-link")
    .data(relations, (d) => `${d.source}-${d.target}`)
    .join("path")
    .attr("class", (d) => `relation-link${showRelations ? "" : " hidden"}`)
    .attr("marker-end", showRelations ? "url(#arrowhead)" : "");

  // 绘制关系标签
  const relationLabelElements = g
    .selectAll(".relation-label")
    .data(relations, (d) => `${d.source}-${d.target}`)
    .join("text")
    .attr("class", (d) => `relation-label${showRelations ? "" : " hidden"}`)
    .text("前置");

  // 绘制节点
  const nodeElements = g
    .selectAll(".node")
    .data(visibleNodes, (d) => d.id)
    .join("g")
    .attr("class", "node")
    .call(drag(simulation));

  nodeElements.selectAll("*").remove();

  nodeElements
    .append("circle")
    .attr("r", (d) => d.radius)
    .attr("fill", (d) => levelColors[Math.min(d.level, levelColors.length - 1)])
    .attr("stroke", (d) => (d.flag === 1 ? "#ff4d6d" : "#ffffff"))
    .attr("stroke-width", (d) => (d.flag === 1 ? 5 : 3));

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
      toggleNode(d);
    }
    showDescription(d);
  });

  simulation.on("tick", () => {
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

  updateStats(visibleNodes.length);
}

function toggleNode(nodeData) {
  if (expandedNodes.has(nodeData.id)) {
    expandedNodes.delete(nodeData.id);
    collapseChildren(nodeData.id);
  } else {
    expandedNodes.add(nodeData.id);
  }
  updateGraph();
}

function collapseChildren(nodeId) {
  const nodeData = allNodesData[nodeId];
  if (nodeData && nodeData.childrenList) {
    nodeData.childrenList.forEach((child) => {
      expandedNodes.delete(child.id);
      collapseChildren(child.id);
    });
  }
}

function expandAll() {
  Object.values(allNodesData).forEach((node) => {
    if (node.childrenList && node.childrenList.length > 0) {
      expandedNodes.add(node.id);
    }
  });
  updateGraph();
}

function collapseAll() {
  const root = data.mocKgNodeDtoList.find((n) => n.parentId === -1);
  expandedNodes.clear();
  expandedNodes.add(root.id);
  updateGraph();
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

function showDescription(nodeData) {
  selectedNode = nodeData;

  d3.selectAll(".node circle")
    .attr("stroke", (d) => (d.flag === 1 ? "#ff4d6d" : "#ffffff"))
    .attr("stroke-width", (d) => (d.flag === 1 ? 5 : 3));

  d3.selectAll(".node")
    .filter((d) => d.id === nodeData.id)
    .select("circle")
    .attr("stroke", (d) => (d.flag === 1 ? "#ff4d6d" : "#a5cbff"))
    .attr("stroke-width", 5);

  document.getElementById("node-title").textContent = nodeData.nodeName;
  document.getElementById("node-description").textContent =
    nodeData.description || "暂无描述";
  document.getElementById("description-panel").classList.add("show");
}

function updateStats(visibleCount) {
  document.getElementById("total-nodes").textContent =
    Object.keys(allNodesData).length;
  document.getElementById("visible-nodes").textContent = visibleCount;
}

function drag(simulation) {
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
