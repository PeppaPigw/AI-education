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
    )/1.5 - 100;

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
    root: 40,
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
