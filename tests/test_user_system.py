import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools.user_manager import UserManager
from tools.session_manager import get_session_manager


def test_user_authentication():
    print("Testing user authentication...")
    user_manager = UserManager()

    student = user_manager.authenticate_student("stuwangqiyu", "123456")
    assert student is not None, "Student authentication failed"
    assert student["username"] == "stuwangqiyu"
    print("✅ Student authentication successful")

    teacher = user_manager.authenticate_teacher("teawangqiyu", "123456")
    assert teacher is not None, "Teacher authentication failed"
    assert teacher["username"] == "teawangqiyu"
    print("✅ Teacher authentication successful")

    admin = user_manager.authenticate_admin("adminwangqiyu", "123456")
    assert admin is not None, "Admin authentication failed"
    assert admin["username"] == "adminwangqiyu"
    print("✅ Admin authentication successful")


def test_user_paths():
    print("\nTesting user-specific paths...")
    user_manager = UserManager()

    course_path = user_manager.get_user_course_path("stuwangqiyu")
    assert os.path.exists(course_path), f"Course path does not exist: {course_path}"
    print(f"✅ Course path exists: {course_path}")

    graph_path = user_manager.get_user_graph_path("stuwangqiyu")
    assert os.path.exists(graph_path), f"Graph path does not exist: {graph_path}"
    print(f"✅ Graph path exists: {graph_path}")

    plans_dir = user_manager.get_user_learning_plans_dir("stuwangqiyu")
    assert os.path.exists(plans_dir), f"Learning plans dir does not exist: {plans_dir}"
    print(f"✅ Learning plans directory exists: {plans_dir}")


def test_session_management():
    print("\nTesting session management...")
    session_manager = get_session_manager()

    user_data = {"username": "testuser", "role": "student"}
    session_id = session_manager.create_session("testuser", "student", user_data)
    assert session_id is not None, "Session creation failed"
    print(f"✅ Session created: {session_id[:10]}...")

    session = session_manager.get_session(session_id)
    assert session is not None, "Session retrieval failed"
    assert session["username"] == "testuser"
    print("✅ Session retrieval successful")

    session_manager.delete_session(session_id)
    session = session_manager.get_session(session_id)
    assert session is None, "Session deletion failed"
    print("✅ Session deletion successful")


def test_student_registration():
    print("\nTesting student registration...")
    user_manager = UserManager()

    test_username = "test_new_student_123"

    try:
        existing = user_manager.authenticate_student(test_username, "test")
        if existing:
            print(f"⚠️  Test user already exists, skipping registration test")
            return

        new_student = user_manager.register_student(
            username=test_username,
            password="testpass",
            stu_name="Test Student",
            email="test@example.com",
        )
        assert new_student["username"] == test_username
        print(f"✅ Student registered: {test_username}")

        course_path = user_manager.get_user_course_path(test_username)
        assert os.path.exists(course_path), "User course file not created"
        print(f"✅ User course file created: {course_path}")

        authenticated = user_manager.authenticate_student(test_username, "testpass")
        assert (
            authenticated is not None
        ), "Newly registered student authentication failed"
        print("✅ Newly registered student can authenticate")

    except ValueError as e:
        print(f"⚠️  Registration test skipped: {e}")


if __name__ == "__main__":
    print("=" * 50)
    print("Multi-User System Tests")
    print("=" * 50)

    try:
        test_user_authentication()
        test_user_paths()
        test_session_management()
        test_student_registration()

        print("\n" + "=" * 50)
        print("✅ All tests passed!")
        print("=" * 50)
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
