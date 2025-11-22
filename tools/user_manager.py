import json
import os
import shutil
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime


class UserManager:
    def __init__(self):
        self.users_dir = Path("data/Users")
        self.users_dir.mkdir(parents=True, exist_ok=True)
        self.student_file = self.users_dir / "student.json"
        self.teacher_file = self.users_dir / "teacher.json"
        self.admin_file = self.users_dir / "admin.json"

        self.user_data_dir = Path("data/user_data")
        self.user_data_dir.mkdir(parents=True, exist_ok=True)

        self.template_course = Path("data/course/big_data.json")
        self.template_graph = Path("backend/static/vendor/graph.json")

    def _load_users(self, filepath: Path) -> list:
        if not filepath.exists():
            return []
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_users(self, filepath: Path, users: list):
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=2, ensure_ascii=False)

    def authenticate_student(
        self, username: str, password: str
    ) -> Optional[Dict[str, Any]]:
        students = self._load_users(self.student_file)
        for student in students:
            if student["username"] == username and student["password"] == password:
                return student
        return None

    def authenticate_teacher(
        self, username: str, password: str
    ) -> Optional[Dict[str, Any]]:
        teachers = self._load_users(self.teacher_file)
        for teacher in teachers:
            if teacher["username"] == username and teacher["password"] == password:
                return teacher
        return None

    def authenticate_admin(
        self, username: str, password: str
    ) -> Optional[Dict[str, Any]]:
        admins = self._load_users(self.admin_file)
        for admin in admins:
            if admin["username"] == username and admin["password"] == password:
                return admin
        return None

    def register_student(
        self,
        username: str,
        password: str,
        stu_name: str,
        email: str = "",
        teacher: str = "",
        img: str = "/static/img/member-02.jpg",
    ) -> Dict[str, Any]:
        students = self._load_users(self.student_file)

        for student in students:
            if student["username"] == username:
                raise ValueError(f"Username {username} already exists")

        new_student = {
            "stu_name": stu_name,
            "img": img,
            "username": username,
            "password": password,
            "email": email,
            "teacher": teacher,
            "learning_goals": [],
            "preference": {"course_topic": [], "course_type": []},
            "progress": [],
            "scores": [-1] * 40,
        }

        students.append(new_student)
        self._save_users(self.student_file, students)

        self._initialize_user_data(username)

        return new_student

    def register_teacher(
        self,
        username: str,
        password: str,
        name: str,
        email: str = "",
    ) -> Dict[str, Any]:
        teachers = self._load_users(self.teacher_file)

        for teacher in teachers:
            if teacher["username"] == username:
                raise ValueError(f"Username {username} already exists")

        new_teacher = {
            "name": name,
            "username": username,
            "password": password,
            "email": email,
            "role": "teacher",
            "students": [],
        }

        teachers.append(new_teacher)
        self._save_users(self.teacher_file, teachers)

        return new_teacher

    def _initialize_user_data(self, username: str):
        user_dir = self.user_data_dir / username
        user_dir.mkdir(parents=True, exist_ok=True)

        user_course_file = user_dir / "big_data.json"
        user_graph_file = user_dir / "graph.json"

        if self.template_course.exists() and not user_course_file.exists():
            shutil.copy(self.template_course, user_course_file)

        if self.template_graph.exists() and not user_graph_file.exists():
            shutil.copy(self.template_graph, user_graph_file)

        learning_plans_dir = user_dir / "learning_plans"
        learning_plans_dir.mkdir(parents=True, exist_ok=True)

    def get_user_course_path(self, username: str) -> str:
        return str(self.user_data_dir / username / "big_data.json")

    def get_user_graph_path(self, username: str) -> str:
        return str(self.user_data_dir / username / "graph.json")

    def get_user_learning_plans_dir(self, username: str) -> str:
        return str(self.user_data_dir / username / "learning_plans")

    def update_student_profile(self, username: str, updates: Dict[str, Any]) -> bool:
        students = self._load_users(self.student_file)

        for student in students:
            if student["username"] == username:
                student.update(updates)
                self._save_users(self.student_file, students)
                return True
        return False

    def get_student_profile(self, username: str) -> Optional[Dict[str, Any]]:
        students = self._load_users(self.student_file)
        for student in students:
            if student["username"] == username:
                return student
        return None

    def get_teacher_profile(self, username: str) -> Optional[Dict[str, Any]]:
        teachers = self._load_users(self.teacher_file)
        for teacher in teachers:
            if teacher["username"] == username:
                return teacher
        return None
