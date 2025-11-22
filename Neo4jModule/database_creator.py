import json
from neo4j import GraphDatabase
import os
from pyvis.network import Network
import webbrowser
import traceback

URI = "bolt://localhost:7687"
USERNAME = "neo4j"
PASSWORD = os.getenv("NEO4J_PASSWORD", "12345678")
COURSE_JSON_PATH = "data/course/big_data.json"


def get_user_course_path(username: str) -> str:
    """Get user-specific course path"""
    user_path = f"data/user_data/{username}/big_data.json"
    if os.path.exists(user_path):
        return user_path
    return COURSE_JSON_PATH


class Neo4jDemo:
    def __init__(self, uri, user, password):
        self._driver = GraphDatabase.driver(uri, auth=(user, password))
        self._driver.verify_connectivity()
        print("✅ Neo4j 驱动已初始化并连接成功。")

    def close(self):
        self._driver.close()
        print(" Neo4j 连接已关闭。")

    def _process_node_recursive(self, session, node_data, parent_name=None):
        node_name = node_data.get("name")
        flag = node_data.get("flag", "0")
        resource_paths = node_data.get("resource_path")

        if not node_name:
            return

        session.run(
            """
            MERGE (c:CourseNode {name: $name})
            SET c.flag = $flag
            RETURN c
        """,
            name=node_name,
            flag=flag,
        )

        if parent_name:
            session.run(
                """
                MATCH (p:CourseNode {name: $parent_name})
                MATCH (c:CourseNode {name: $child_name})
                MERGE (p)-[:HAS_CHILD]->(c)
            """,
                parent_name=parent_name,
                child_name=node_name,
            )

        if isinstance(resource_paths, list) and resource_paths:
            for path in resource_paths:
                session.run(
                    """
                    MERGE (r:Resource {path: $path})
                    RETURN r
                """,
                    path=path,
                )

                session.run(
                    """
                    MATCH (c:CourseNode {name: $course_name})
                    MATCH (r:Resource {path: $path})
                    MERGE (c)-[:USES_RESOURCE]->(r)
                """,
                    course_name=node_name,
                    path=path,
                )

        child_keys = ["children", "grandchildren", "great-grandchildren"]
        for key in child_keys:
            if key in node_data and isinstance(node_data[key], list):
                for child_node_data in node_data[key]:
                    self._process_node_recursive(
                        session, child_node_data, parent_name=node_name
                    )

    def import_course_data(self, json_file_path):
        try:
            with open(json_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            print(f"❌ 错误：文件未找到 at {json_file_path}")
            return False
        except json.JSONDecodeError:
            print("❌ 错误：JSON 文件格式不正确。")
            return False

        with self._driver.session() as session:
            print("⏳ 正在清空数据库...")
            session.run("MATCH (n) DETACH DELETE n")
            print("🧹 数据库已清空。")

            root_name = data.get("root_name")
            if not root_name:
                print("❌ 错误：JSON 中缺少 'root_name' 字段。")
                return False

            session.run(
                "MERGE (c:CourseNode {name: $name}) SET c.flag = '1' RETURN c",
                name=root_name,
            )

            print("⏳ 正在导入课程数据...")
            children_data = data.get("children", [])
            for child_data in children_data:
                self._process_node_recursive(session, child_data, parent_name=root_name)

            stats_query = """
                MATCH (c:CourseNode) WITH count(c) AS courseNodes
                MATCH (r:Resource) WITH courseNodes, count(r) AS resources
                MATCH ()-[rel]->() RETURN courseNodes, resources, count(rel) AS relations
            """
            result = session.run(stats_query).single()

            print(f"✨ 导入完成。")
            if result:
                print(f"   - 创建了 {result['courseNodes']} 个 CourseNode 节点")
                print(f"   - 创建了 {result['resources']} 个 Resource 节点")
                print(
                    f"   - 创建了 {result['relations']} 个关系 (HAS_CHILD, USES_RESOURCE)"
                )
            else:
                print("   - 未能获取统计信息。")

            return True

    def visualize_graph(self, output_file="Neo4jModule/course_graph.html"):
        print("⏳ 正在生成可视化图形...")

        try:
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)

            # 初始化网络图
            net = Network(
                height="800px", width="100%", bgcolor="#222222", font_color="white"
            )
            net.toggle_hide_edges_on_drag(True)
            net.barnes_hut(gravity=-8000, central_gravity=0.3, spring_length=200)

            print("正在从Neo4j查询数据...")
            with self._driver.session() as session:
                query = """
                MATCH (n)-[r]->(m)
                RETURN n.name as source_name, 
                       labels(n)[0] as source_type,
                       type(r) as rel_type,
                       m.name as target_name,
                       labels(m)[0] as target_type
                LIMIT 200
                """
                result = session.run(query)

                nodes = set()
                edge_count = 0

                print("正在处理节点和边...")
                for record in result:
                    try:
                        source_name = str(record["source_name"])
                        source_type = str(record["source_type"])
                        target_name = str(record["target_name"])
                        target_type = str(record["target_type"])
                        rel_type = str(record["rel_type"])

                        if source_name not in nodes:
                            color = (
                                "#3498db" if source_type == "CourseNode" else "#e74c3c"
                            )
                            net.add_node(
                                source_name,
                                label=source_name,
                                color=color,
                                group=source_type,
                            )
                            nodes.add(source_name)

                        if target_name not in nodes:
                            color = (
                                "#3498db" if target_type == "CourseNode" else "#e74c3c"
                            )
                            net.add_node(
                                target_name,
                                label=target_name,
                                color=color,
                                group=target_type,
                            )
                            nodes.add(target_name)

                        net.add_edge(
                            source_name, target_name, title=rel_type, label=rel_type
                        )
                        edge_count += 1
                    except Exception as e:
                        print(f"⚠️ 处理记录时出错: {str(e)}")
                        continue

                print(f"已处理 {len(nodes)} 个节点和 {edge_count} 条边")

            # 直接保存到最终文件，不再使用临时文件
            print("正在生成HTML文件...")
            net.save_graph(output_file)

            # 确保文件生成成功
            if not os.path.exists(output_file):
                raise Exception("HTML文件未生成")

            print(f"✅ 可视化图形已生成: {os.path.abspath(output_file)}")

            # 尝试在浏览器中打开
            try:
                webbrowser.open(f"file://{os.path.abspath(output_file)}")
            except Exception as e:
                print(f"⚠️ 无法在浏览器中打开文件: {str(e)}")
                print(f"请手动打开文件: {os.path.abspath(output_file)}")

            return True

        except Exception as e:
            print(f"❌ 可视化生成失败:")
            traceback.print_exc()
            return False


if __name__ == "__main__":
    db = None
    try:
        import sys

        username = sys.argv[1] if len(sys.argv) > 1 else None
        json_path = get_user_course_path(username) if username else COURSE_JSON_PATH

        print(f"Using course data: {json_path}")

        db = Neo4jDemo(URI, USERNAME, PASSWORD)
        if db.import_course_data(json_path):
            if not db.visualize_graph():
                print("⚠️ 可视化生成失败，但数据已成功导入Neo4j")
    except Exception as e:
        print(f"\n❌ 发生错误:")
        traceback.print_exc()
    finally:
        if db:
            db.close()
