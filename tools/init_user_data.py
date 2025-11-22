import json
import os
import shutil
from pathlib import Path


def init_existing_users():
    """为现有用户初始化数据目录和文件"""
    users_dir = Path("data/Users")
    student_file = users_dir / "student.json"

    user_data_dir = Path("data/user_data")
    user_data_dir.mkdir(parents=True, exist_ok=True)

    template_course = Path("data/course/big_data.json")
    template_graph = Path("backend/static/vendor/graph.json")

    if not student_file.exists():
        print(f"❌ Student file not found: {student_file}")
        return

    with open(student_file, "r", encoding="utf-8") as f:
        students = json.load(f)

    print(f"Found {len(students)} students")

    for student in students:
        username = student.get("username")
        if not username:
            continue

        print(f"Initializing data for {username}...")

        user_dir = user_data_dir / username
        user_dir.mkdir(parents=True, exist_ok=True)

        user_course_file = user_dir / "big_data.json"
        user_graph_file = user_dir / "graph.json"

        if template_course.exists() and not user_course_file.exists():
            shutil.copy(template_course, user_course_file)
            print(f"  ✅ Created {user_course_file}")
        else:
            print(f"  ⚠️  Course file already exists or template not found")

        if template_graph.exists() and not user_graph_file.exists():
            shutil.copy(template_graph, user_graph_file)
            print(f"  ✅ Created {user_graph_file}")
        else:
            print(f"  ⚠️  Graph file already exists or template not found")

        learning_plans_dir = user_dir / "learning_plans"
        learning_plans_dir.mkdir(parents=True, exist_ok=True)
        print(f"  ✅ Created learning plans directory")

    print(f"\n✅ Initialization complete for {len(students)} students")


if __name__ == "__main__":
    init_existing_users()
