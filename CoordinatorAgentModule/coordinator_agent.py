from langchain_classic.agents import create_react_agent
from langchain_classic.agents.agent import AgentExecutor
import logging
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain.tools import tool
from tools.language_handler import LanguageHandler
from tools.llm_logger import get_llm_logger
from dotenv import load_dotenv
import os
import json

load_dotenv()
model_name = os.environ.get("model_name")
base_url = os.environ.get("base_url")
api_key = os.environ.get("api_key")


@tool
def intent_classifier(user_input: str) -> str:
    """Classify user intent from input text"""
    intents = {
        "qa": [
            "问",
            "什么",
            "如何",
            "为什么",
            "哪",
            "谁",
            "question",
            "what",
            "how",
            "why",
            "who",
        ],
        "quiz": ["测试", "测验", "考试", "题目", "quiz", "test", "exam"],
        "summary": ["总结", "归纳", "概括", "summary", "summarize"],
        "plan": ["计划", "学习计划", "规划", "plan", "schedule"],
        "greeting": ["你好", "hello", "hi", "嗨"],
        "feedback": ["反馈", "建议", "feedback", "suggestion"],
    }

    user_lower = user_input.lower()
    detected = []

    for intent, keywords in intents.items():
        if any(kw in user_lower for kw in keywords):
            detected.append(intent)

    if not detected:
        detected = ["qa"]

    return json.dumps({"intents": detected, "primary": detected[0]})


@tool
def task_decomposer(user_input: str) -> str:
    """Decompose complex user request into subtasks"""
    llm = ChatOpenAI(
        model=model_name, temperature=0, base_url=base_url, api_key=api_key
    )

    prompt = f"""Decompose the following user request into subtasks. Return a JSON array of subtasks.

User request: {user_input}

Output format:
{{
  "is_complex": true/false,
  "subtasks": [
    {{"step": 1, "action": "action description", "target": "target agent"}},
    ...
  ]
}}

Possible target agents: qa_agent, quiz_agent, summary_agent, plan_agent
"""

    try:
        response = llm.invoke(prompt)
        content = response.content

        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        return content
    except Exception as e:
        return json.dumps(
            {
                "is_complex": False,
                "subtasks": [{"step": 1, "action": user_input, "target": "qa_agent"}],
                "error": str(e),
            }
        )


@tool
def priority_analyzer(tasks: str) -> str:
    """Analyze priority levels for given tasks"""
    try:
        tasks_data = json.loads(tasks)
        subtasks = tasks_data.get("subtasks", [])

        priorities = []
        for task in subtasks:
            action = task.get("action", "").lower()

            if any(kw in action for kw in ["urgent", "立即", "马上", "紧急"]):
                priority = "high"
            elif any(kw in action for kw in ["later", "稍后", "以后"]):
                priority = "low"
            else:
                priority = "medium"

            priorities.append(
                {
                    "step": task.get("step"),
                    "priority": priority,
                    "action": task.get("action"),
                }
            )

        return json.dumps({"priorities": priorities})
    except Exception as e:
        return json.dumps({"error": str(e)})


COORDINATOR_PROMPT = PromptTemplate.from_template(
    """You are a Coordinator Agent responsible for intent recognition and task decomposition. You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]$
Action Input: the input to the action
Observation: the result of the action
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Your responsibilities:
1. Identify user intent using intent_classifier
2. For complex requests, decompose into subtasks using task_decomposer
3. Analyze task priorities using priority_analyzer
4. Return a structured coordination plan

Example 1:
Question: 我想学习大数据并参加测试
Thought: This is a complex request, I should identify intent and decompose it
Action: intent_classifier
Action Input: 我想学习大数据并参加测试
Observation: {{"intents": ["plan", "quiz"], "primary": "plan"}}
Thought: Now I should decompose this into subtasks
Action: task_decomposer
Action Input: 我想学习大数据并参加测试
Observation: {{"is_complex": true, "subtasks": [{{"step": 1, "action": "create learning plan", "target": "plan_agent"}}, {{"step": 2, "action": "take quiz", "target": "quiz_agent"}}]}}
Thought: I should analyze priorities
Action: priority_analyzer
Action Input: {{"is_complex": true, "subtasks": [{{"step": 1, "action": "create learning plan", "target": "plan_agent"}}, {{"step": 2, "action": "take quiz", "target": "quiz_agent"}}]}}
Observation: {{"priorities": [{{"step": 1, "priority": "high", "action": "create learning plan"}}, {{"step": 2, "priority": "medium", "action": "take quiz"}}]}}
Thought: I now have a complete coordination plan
Final Answer: User intent: plan+quiz. Decomposed into 2 subtasks: 1) Create learning plan (high priority, plan_agent), 2) Take quiz (medium priority, quiz_agent).

Example 2:
Question: Hello
Thought: This is a simple greeting
Action: intent_classifier
Action Input: Hello
Observation: {{"intents": ["greeting"], "primary": "greeting"}}
Thought: This is a simple greeting, no decomposition needed
Final Answer: User intent: greeting. Single task, no decomposition needed. Route to qa_agent.

Always answer in {language}.

Begin!

Question: {input}
Thought:{agent_scratchpad}"""
)


class Coordinator_Agent:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.llm = ChatOpenAI(
            model=model_name, temperature=0, base_url=base_url, api_key=api_key
        )
        self.tools = [
            intent_classifier,
            task_decomposer,
            priority_analyzer,
        ]
        agent = create_react_agent(self.llm, self.tools, COORDINATOR_PROMPT)
        self.executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            max_iterations=5,
            handle_parsing_errors=True,
            early_stopping_method="force",
        )

    def coordinate(self, user_input: str, return_details: bool = False):
        print("\n" + "=" * 80)
        print("🎯 协调器启动:")
        print(f"   用户输入: {user_input}")
        self.logger.info(f"Coordinator processing: {user_input}")

        lang = LanguageHandler.choose_or_detect(user_input)
        print(f"🌐 语言: {lang}")

        try:
            print("🤖 协调器分析中...")
            print("-" * 80)

            result = self.executor.invoke({"input": user_input, "language": lang})
            output = result["output"]

            llm_logger = get_llm_logger()
            llm_logger.log_llm_call(
                messages=[{"role": "user", "content": user_input}],
                response=type(
                    "Response", (), {"content": output, "response_metadata": {}}
                )(),
                model=model_name,
                module="AgentModule.coordinator_agent",
                metadata={
                    "function": "coordinate",
                    "language": lang,
                },
            )

            print("-" * 80)
            print("✅ 协调结果:")
            print(f"   {output}")
            self.logger.info(f"Coordination output: {output}")

            coordination_plan = self._parse_coordination_output(output)

        except Exception as e:
            output = f"Coordination error: {e}"
            coordination_plan = {
                "intent": "unknown",
                "is_complex": False,
                "subtasks": [],
                "error": str(e),
            }
            print(f"❌ 协调错误: {e}")
            self.logger.error(f"Coordination error: {e}")

        print("=" * 80 + "\n")

        if return_details:
            return output, coordination_plan
        return output

    def _parse_coordination_output(self, output: str):
        coordination = {
            "intent": "unknown",
            "is_complex": False,
            "subtasks": [],
            "routing": "qa_agent",
        }

        try:
            output_lower = output.lower()

            if "intent:" in output_lower:
                intent_part = output.split("intent:")[1].split(".")[0].strip()
                coordination["intent"] = intent_part

            if "subtasks" in output_lower or "decomposed" in output_lower:
                coordination["is_complex"] = True

                import re

                matches = re.findall(r"(\d+)\)\s*(.+?)\s*\((.+?)\)", output)
                if matches:
                    subtasks = []
                    for step, action, target in matches:
                        subtasks.append(
                            {
                                "step": int(step),
                                "action": action.strip(),
                                "target": target.strip(),
                            }
                        )
                    coordination["subtasks"] = subtasks

            if "route to" in output_lower:
                route_part = output.split("route to")[1].split(".")[0].strip()
                coordination["routing"] = route_part

        except Exception as e:
            self.logger.error(f"Parse coordination output error: {e}")

        return coordination

    def analyze_intent(self, user_input: str):
        lang = LanguageHandler.choose_or_detect(user_input)

        prompt = f"""Analyze the user's intent from the following input and classify it into one or more categories.

Categories: qa (question answering), quiz (testing), summary (summarization), plan (learning plan), greeting, feedback

User input: {user_input}

Return JSON format:
{{
  "primary_intent": "...",
  "secondary_intents": [...],
  "confidence": 0.0-1.0
}}

Answer in {lang}."""

        try:
            response = self.llm.invoke(prompt)
            content = response.content

            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            return json.loads(content)
        except Exception as e:
            return {
                "primary_intent": "qa",
                "secondary_intents": [],
                "confidence": 0.5,
                "error": str(e),
            }

    def decompose_task(self, user_input: str):
        lang = LanguageHandler.choose_or_detect(user_input)

        prompt = f"""Decompose the following task into sequential subtasks if it's complex. If it's simple, return a single task.

User task: {user_input}

Return JSON format:
{{
  "is_complex": true/false,
  "subtasks": [
    {{
      "step": 1,
      "description": "...",
      "target_agent": "...",
      "dependencies": []
    }},
    ...
  ]
}}

Possible agents: qa_agent, quiz_agent, summary_agent, plan_agent

Answer in {lang}."""

        try:
            response = self.llm.invoke(prompt)
            content = response.content

            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            return json.loads(content)
        except Exception as e:
            return {
                "is_complex": False,
                "subtasks": [
                    {
                        "step": 1,
                        "description": user_input,
                        "target_agent": "qa_agent",
                        "dependencies": [],
                    }
                ],
                "error": str(e),
            }
