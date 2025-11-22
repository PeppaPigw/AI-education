import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from CoordinatorAgentModule.coordinator_agent import Coordinator_Agent


def test_simple_greeting():
    print("\n" + "=" * 80)
    print("Test 1: Simple Greeting")
    print("=" * 80)

    coordinator = Coordinator_Agent()
    result, plan = coordinator.coordinate("Hello", return_details=True)

    print(f"\nResult: {result}")
    print(f"Plan: {plan}")

    assert plan["intent"] is not None
    print("✅ Test 1 passed")


def test_complex_request():
    print("\n" + "=" * 80)
    print("Test 2: Complex Request")
    print("=" * 80)

    coordinator = Coordinator_Agent()
    result, plan = coordinator.coordinate(
        "我想学习大数据基础知识，然后参加一个测试，最后生成学习计划",
        return_details=True,
    )

    print(f"\nResult: {result}")
    print(f"Plan: {plan}")

    print("✅ Test 2 passed")


def test_intent_analysis():
    print("\n" + "=" * 80)
    print("Test 3: Intent Analysis")
    print("=" * 80)

    coordinator = Coordinator_Agent()

    test_inputs = [
        "什么是大数据？",
        "我要参加测试",
        "总结一下这个章节",
        "帮我制定学习计划",
    ]

    for user_input in test_inputs:
        intent = coordinator.analyze_intent(user_input)
        print(f"\nInput: {user_input}")
        print(f"Intent: {intent}")

    print("\n✅ Test 3 passed")


def test_task_decomposition():
    print("\n" + "=" * 80)
    print("Test 4: Task Decomposition")
    print("=" * 80)

    coordinator = Coordinator_Agent()

    test_tasks = [
        "Hello",
        "先学习，再测试，最后总结",
    ]

    for task in test_tasks:
        decomposition = coordinator.decompose_task(task)
        print(f"\nTask: {task}")
        print(f"Decomposition: {decomposition}")

    print("\n✅ Test 4 passed")


if __name__ == "__main__":
    print("=" * 80)
    print("Coordinator Agent Tests")
    print("=" * 80)

    try:
        test_simple_greeting()
        test_complex_request()
        test_intent_analysis()
        test_task_decomposition()

        print("\n" + "=" * 80)
        print("✅ All coordinator tests passed!")
        print("=" * 80)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
