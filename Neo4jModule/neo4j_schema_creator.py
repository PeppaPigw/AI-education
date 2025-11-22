import json
from neo4j import GraphDatabase
import os
from pathlib import Path


class Neo4jSchemaCreator:
    def __init__(self, uri, user, password):
        self._driver = GraphDatabase.driver(uri, auth=(user, password))
        self._driver.verify_connectivity()
        print("✅ Neo4j connected")

    def close(self):
        self._driver.close()

    def create_constraints_and_indexes(self):
        with self._driver.session() as session:
            constraints = [
                "CREATE CONSTRAINT student_username_unique IF NOT EXISTS FOR (s:Student) REQUIRE s.username IS UNIQUE",
                "CREATE CONSTRAINT teacher_username_unique IF NOT EXISTS FOR (t:Teacher) REQUIRE t.username IS UNIQUE",
                "CREATE CONSTRAINT knowledge_node_id_unique IF NOT EXISTS FOR (kn:KnowledgeNode) REQUIRE kn.nodeId IS UNIQUE",
            ]

            indexes = [
                "CREATE INDEX knowledge_node_name IF NOT EXISTS FOR (kn:KnowledgeNode) ON (kn.nodeName)",
                "CREATE INDEX student_email IF NOT EXISTS FOR (s:Student) ON (s.email)",
                "CREATE INDEX course_resource_name IF NOT EXISTS FOR (cr:CourseResource) ON (cr.name)",
                "CREATE INDEX knowledge_graph_id IF NOT EXISTS FOR (kn:KnowledgeNode) ON (kn.knowledgeGraphId)",
                "CREATE INDEX student_progress_composite IF NOT EXISTS FOR (p:Progress) ON (p.topic, p.date)",
            ]

            for constraint in constraints:
                try:
                    session.run(constraint)
                    print(f"✅ Created constraint")
                except Exception as e:
                    print(f"⚠️ Constraint error: {e}")

            for index in indexes:
                try:
                    session.run(index)
                    print(f"✅ Created index")
                except Exception as e:
                    print(f"⚠️ Index error: {e}")

    def create_knowledge_nodes(self, graph_data):
        with self._driver.session() as session:
            session.run("MATCH (n:KnowledgeNode) DETACH DELETE n")

            root_name = graph_data.get("root_name", "大数据分析")
            session.run(
                """
                CREATE (root:KnowledgeNode {
                    nodeId: $nodeId,
                    knowledgeGraphId: $graphId,
                    nodeName: $name,
                    description: $desc,
                    position: 0,
                    flag: 1,
                    level: 0,
                    childCount: $childCount,
                    createTime: datetime(),
                    updateTime: datetime()
                })
                """,
                nodeId=1,
                graphId=29889,
                name=root_name,
                desc=root_name,
                childCount=len(graph_data.get("children", [])),
            )

            node_id = 2
            children_data = graph_data.get("children", [])

            for i, child in enumerate(children_data):
                child_id = node_id
                node_id += 1

                session.run(
                    """
                    CREATE (child:KnowledgeNode {
                        nodeId: $nodeId,
                        knowledgeGraphId: $graphId,
                        nodeName: $name,
                        description: $desc,
                        position: $position,
                        flag: $flag,
                        level: 1,
                        childCount: $childCount,
                        createTime: datetime(),
                        updateTime: datetime()
                    })
                    """,
                    nodeId=child_id,
                    graphId=29889,
                    name=child.get("name", ""),
                    desc=child.get("name", ""),
                    position=i,
                    flag=int(child.get("flag", "0")),
                    childCount=len(child.get("grandchildren", [])),
                )

                session.run(
                    """
                    MATCH (root:KnowledgeNode {nodeId: 1})
                    MATCH (child:KnowledgeNode {nodeId: $childId})
                    CREATE (root)-[:HAS_CHILD {position: $position}]->(child)
                    """,
                    childId=child_id,
                    position=i,
                )

                for j, grandchild in enumerate(child.get("grandchildren", [])):
                    gc_id = node_id
                    node_id += 1

                    session.run(
                        """
                        CREATE (gc:KnowledgeNode {
                            nodeId: $nodeId,
                            knowledgeGraphId: $graphId,
                            nodeName: $name,
                            description: $desc,
                            position: $position,
                            flag: $flag,
                            level: 2,
                            childCount: $childCount,
                            createTime: datetime(),
                            updateTime: datetime()
                        })
                        """,
                        nodeId=gc_id,
                        graphId=29889,
                        name=grandchild.get("name", ""),
                        desc=grandchild.get("name", ""),
                        position=j,
                        flag=int(grandchild.get("flag", "0")),
                        childCount=len(grandchild.get("great-grandchildren", [])),
                    )

                    session.run(
                        """
                        MATCH (parent:KnowledgeNode {nodeId: $parentId})
                        MATCH (child:KnowledgeNode {nodeId: $childId})
                        CREATE (parent)-[:HAS_CHILD {position: $position}]->(child)
                        """,
                        parentId=child_id,
                        childId=gc_id,
                        position=j,
                    )

                    for k, ggc in enumerate(grandchild.get("great-grandchildren", [])):
                        ggc_id = node_id
                        node_id += 1

                        session.run(
                            """
                            CREATE (ggc:KnowledgeNode {
                                nodeId: $nodeId,
                                knowledgeGraphId: $graphId,
                                nodeName: $name,
                                description: $desc,
                                position: $position,
                                flag: $flag,
                                level: 3,
                                childCount: 0,
                                createTime: datetime(),
                                updateTime: datetime()
                            })
                            """,
                            nodeId=ggc_id,
                            graphId=29889,
                            name=ggc.get("name", ""),
                            desc=ggc.get("name", ""),
                            position=k,
                            flag=int(ggc.get("flag", "0")),
                        )

                        session.run(
                            """
                            MATCH (parent:KnowledgeNode {nodeId: $parentId})
                            MATCH (child:KnowledgeNode {nodeId: $childId})
                            CREATE (parent)-[:HAS_CHILD {position: $position}]->(child)
                            """,
                            parentId=gc_id,
                            childId=ggc_id,
                            position=k,
                        )

            print(f"✅ Created {node_id - 1} knowledge nodes")

    def create_course_resources(self, graph_data):
        with self._driver.session() as session:
            session.run("MATCH (n:CourseResource) DETACH DELETE n")
            session.run("MATCH (n:Resource) DETACH DELETE n")

            root_name = graph_data.get("root_name", "大数据分析")
            session.run(
                """
                CREATE (root:CourseResource {
                    resourceId: randomUUID(),
                    name: $name,
                    flag: '1',
                    hierarchy: 'root'
                })
                """,
                name=root_name,
            )

            for i, child in enumerate(graph_data.get("children", [])):
                session.run(
                    """
                    CREATE (child:CourseResource {
                        resourceId: randomUUID(),
                        name: $name,
                        flag: $flag,
                        hierarchy: 'children'
                    })
                    """,
                    name=child.get("name", ""),
                    flag=child.get("flag", "0"),
                )

                session.run(
                    """
                    MATCH (parent:CourseResource {hierarchy: 'root'})
                    MATCH (child:CourseResource {name: $childName, hierarchy: 'children'})
                    CREATE (parent)-[:CONTAINS {order: $order}]->(child)
                    """,
                    childName=child.get("name", ""),
                    order=i,
                )

                for j, grandchild in enumerate(child.get("grandchildren", [])):
                    session.run(
                        """
                        CREATE (gc:CourseResource {
                            resourceId: randomUUID(),
                            name: $name,
                            flag: $flag,
                            hierarchy: 'grandchildren'
                        })
                        """,
                        name=grandchild.get("name", ""),
                        flag=grandchild.get("flag", "0"),
                    )

                    session.run(
                        """
                        MATCH (parent:CourseResource {name: $parentName, hierarchy: 'children'})
                        MATCH (child:CourseResource {name: $childName, hierarchy: 'grandchildren'})
                        CREATE (parent)-[:CONTAINS {order: $order}]->(child)
                        """,
                        parentName=child.get("name", ""),
                        childName=grandchild.get("name", ""),
                        order=j,
                    )

                    resources = grandchild.get("resource_path", [])
                    if isinstance(resources, str):
                        resources = [resources] if resources else []

                    for idx, resource_path in enumerate(resources):
                        session.run(
                            """
                            CREATE (r:Resource {
                                resourcePath: $path,
                                resourceType: $type
                            })
                            """,
                            path=resource_path,
                            type="PDF" if resource_path.endswith(".pdf") else "M3U8",
                        )

                        session.run(
                            """
                            MATCH (course:CourseResource {name: $courseName, hierarchy: 'grandchildren'})
                            MATCH (resource:Resource {resourcePath: $path})
                            CREATE (course)-[:HAS_RESOURCE {order: $order}]->(resource)
                            """,
                            courseName=grandchild.get("name", ""),
                            path=resource_path,
                            order=idx,
                        )

            print("✅ Created course resources")

    def create_users_from_json(self):
        with self._driver.session() as session:
            session.run("MATCH (n:Student) DETACH DELETE n")
            session.run("MATCH (n:Teacher) DETACH DELETE n")

            student_file = Path("data/Users/student.json")
            teacher_file = Path("data/Users/teacher.json")

            if student_file.exists():
                with open(student_file, "r", encoding="utf-8") as f:
                    students = json.load(f)

                for student in students:
                    session.run(
                        """
                        CREATE (s:Student {
                            username: $username,
                            stuName: $stuName,
                            password: $password,
                            email: $email,
                            img: $img
                        })
                        """,
                        username=student.get("username"),
                        stuName=student.get("stu_name"),
                        password=student.get("password"),
                        email=student.get("email", ""),
                        img=student.get("img", ""),
                    )

                    for idx, goal in enumerate(student.get("learning_goals", [])):
                        session.run(
                            """
                            MATCH (s:Student {username: $username})
                            MERGE (goal:LearningGoal {goalName: $goalName})
                            CREATE (s)-[:HAS_GOAL {order: $order}]->(goal)
                            """,
                            username=student.get("username"),
                            goalName=goal,
                            order=idx,
                        )

                    for pref in student.get("preference", {}).get("course_topic", []):
                        session.run(
                            """
                            MATCH (s:Student {username: $username})
                            MERGE (topic:CourseTopic {
                                topicName: $topicName,
                                hierarchy: $hierarchy
                            })
                            CREATE (s)-[:PREFERS_TOPIC]->(topic)
                            """,
                            username=student.get("username"),
                            topicName=pref.get("name"),
                            hierarchy=pref.get("hierarchy"),
                        )

                    for pref in student.get("preference", {}).get("course_type", []):
                        session.run(
                            """
                            MATCH (s:Student {username: $username})
                            MERGE (type:CourseType {typeName: $typeName})
                            CREATE (s)-[:PREFERS_TYPE]->(type)
                            """,
                            username=student.get("username"),
                            typeName=pref.get("name"),
                        )

                    for progress in student.get("progress", []):
                        for date_prog in progress.get("date", []):
                            if date_prog[0] and date_prog[1] is not None:
                                session.run(
                                    """
                                    MATCH (s:Student {username: $username})
                                    CREATE (s)-[:HAS_PROGRESS]->(p:Progress {
                                        topic: $topic,
                                        date: date($date),
                                        progressValue: $value
                                    })
                                    """,
                                    username=student.get("username"),
                                    topic=progress.get("topic"),
                                    date=date_prog[0],
                                    value=date_prog[1],
                                )

                    for idx, score in enumerate(student.get("scores", [])):
                        if score != -1:
                            session.run(
                                """
                                MATCH (s:Student {username: $username})
                                CREATE (s)-[:HAS_SCORE]->(sc:Score {
                                    scoreValue: $value,
                                    sequence: $seq,
                                    recordDate: datetime()
                                })
                                """,
                                username=student.get("username"),
                                value=score,
                                seq=idx,
                            )

                print(f"✅ Created {len(students)} students")

            if teacher_file.exists():
                with open(teacher_file, "r", encoding="utf-8") as f:
                    teachers = json.load(f)

                for teacher in teachers:
                    session.run(
                        """
                        CREATE (t:Teacher {
                            username: $username,
                            name: $name,
                            password: $password,
                            email: $email,
                            role: $role
                        })
                        """,
                        username=teacher.get("username"),
                        name=teacher.get("name"),
                        password=teacher.get("password"),
                        email=teacher.get("email", ""),
                        role=teacher.get("role", "teacher"),
                    )

                    for student_name in teacher.get("students", []):
                        session.run(
                            """
                            MATCH (t:Teacher {username: $teacherUsername})
                            MATCH (s:Student {stuName: $studentName})
                            CREATE (t)-[:TEACHES]->(s)
                            """,
                            teacherUsername=teacher.get("username"),
                            studentName=student_name,
                        )

                print(f"✅ Created {len(teachers)} teachers")

    def create_statistics_nodes(self):
        with self._driver.session() as session:
            session.run("MATCH (n:MemberStatistics) DETACH DELETE n")
            session.run("MATCH (n:AvgStatistics) DETACH DELETE n")

            result = session.run("MATCH (kn:KnowledgeNode) RETURN kn.nodeId as nodeId")

            for record in result:
                node_id = record["nodeId"]

                session.run(
                    """
                    MATCH (kn:KnowledgeNode {nodeId: $nodeId})
                    CREATE (ms:MemberStatistics {
                        id: $id,
                        memberId: 1,
                        completionRate: toInteger(rand() * 100),
                        learnedTimeCount: toInteger(rand() * 1000),
                        masteryRate: toInteger(rand() * 100),
                        gmtCreate: timestamp(),
                        gmtModified: timestamp()
                    })
                    CREATE (kn)-[:HAS_MEMBER_STATS]->(ms)
                    """,
                    nodeId=node_id,
                    id=node_id * 100,
                )

                session.run(
                    """
                    MATCH (kn:KnowledgeNode {nodeId: $nodeId})
                    CREATE (as:AvgStatistics {
                        id: $id,
                        avgMasteryRate: toInteger(rand() * 100),
                        questionJoinCount: toInteger(rand() * 50),
                        avgLearnedTimeCount: toInteger(rand() * 500),
                        targetType: 1,
                        targetId: $nodeId,
                        learnCount: toInteger(rand() * 100),
                        avgCompletionRate: toInteger(rand() * 100),
                        hasLearnResource: toInteger(rand() * 2),
                        hasQuestion: toInteger(rand() * 2)
                    })
                    CREATE (kn)-[:HAS_AVG_STATS]->(as)
                    """,
                    nodeId=node_id,
                    id=node_id * 100 + 1,
                )

            print("✅ Created statistics nodes")

    def create_learning_relationships(self):
        with self._driver.session() as session:
            result = session.run(
                """
                MATCH (s:Student)
                MATCH (kn:KnowledgeNode)
                WHERE rand() < 0.3
                RETURN s.username as username, kn.nodeId as nodeId
                LIMIT 100
                """
            )

            for record in result:
                session.run(
                    """
                    MATCH (s:Student {username: $username})
                    MATCH (kn:KnowledgeNode {nodeId: $nodeId})
                    CREATE (s)-[:LEARNING {
                        startDate: date(),
                        currentProgress: toInteger(rand() * 100),
                        completionRate: toInteger(rand() * 100)
                    }]->(kn)
                    """,
                    username=record["username"],
                    nodeId=record["nodeId"],
                )

            print("✅ Created learning relationships")

    def link_goals_to_knowledge(self):
        with self._driver.session() as session:
            result = session.run(
                """
                MATCH (goal:LearningGoal)
                MATCH (kn:KnowledgeNode)
                WHERE kn.nodeName CONTAINS goal.goalName OR goal.goalName CONTAINS kn.nodeName
                RETURN goal.goalName as goalName, kn.nodeId as nodeId
                """
            )

            for record in result:
                session.run(
                    """
                    MATCH (goal:LearningGoal {goalName: $goalName})
                    MATCH (kn:KnowledgeNode {nodeId: $nodeId})
                    CREATE (goal)-[:TARGETS]->(kn)
                    """,
                    goalName=record["goalName"],
                    nodeId=record["nodeId"],
                )

            print("✅ Linked goals to knowledge nodes")

    def create_all_from_json(self, json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                graph_data = json.load(f)
        except Exception as e:
            print(f"❌ Error loading JSON: {e}")
            return False

        with self._driver.session() as session:
            print("🧹 Clearing database...")
            session.run("MATCH (n) DETACH DELETE n")

        print("📋 Creating constraints and indexes...")
        self.create_constraints_and_indexes()

        print("📚 Creating knowledge nodes...")
        self.create_knowledge_nodes(graph_data)

        print("📦 Creating course resources...")
        self.create_course_resources(graph_data)

        print("👥 Creating users...")
        self.create_users_from_json()

        print("📊 Creating statistics...")
        self.create_statistics_nodes()

        print("🔗 Creating learning relationships...")
        self.create_learning_relationships()

        print("🎯 Linking goals to knowledge...")
        self.link_goals_to_knowledge()

        print("✅ Database creation complete")
        return True


if __name__ == "__main__":
    URI = "bolt://localhost:7687"
    USERNAME = "neo4j"
    PASSWORD = os.getenv("NEO4J_PASSWORD", "12345678")
    COURSE_JSON_PATH = "data/course/big_data.json"

    db = None
    try:
        db = Neo4jSchemaCreator(URI, USERNAME, PASSWORD)
        db.create_all_from_json(COURSE_JSON_PATH)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        if db:
            db.close()
