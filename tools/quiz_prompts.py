from langchain_core.prompts import ChatPromptTemplate


def generate_topic_list_prompt(
    subject: str, language: str = "zh"
) -> ChatPromptTemplate:
    system_message = (
        f"你是教育课程设计方面的专家。你是一位专家导师，根据学生的测验结果来评估他们的知识水平。\n"
        f"您的任务是生成最可检查的子主题的逻辑结构化列表。\n"
        f"请**仅**使用 {language} **回复**。**不要**包含任何解释。"
    )

    human_message = (
        f"主题: {subject}\n\n"
        f"请创建一个核心主题的**项目符号列表**，这些主题可用于**创建测验**。"
    )

    return ChatPromptTemplate.from_messages(
        [("system", system_message), ("human", human_message)]
    )


def generate_questions_prompt(topic: str, language: str = "en") -> ChatPromptTemplate:
    """
    生成包含选择题和主观题的测验题目提示词模板
    """
    system_message = f"""
        # 角色与任务 🎯
你是一位资深的**教育评估专家**和**专业命题人**。你的任务是根据给定的核心主题，生成一套高质量、严谨的测验题。

# 核心主题
本套测验的核心主题是：**{core_topic}**

# 质量与严谨性要求 🧐
1.  **专业性**：题目必须反映该主题的核心概念和关键知识点。
2.  **严谨性**：问题表述清晰无歧义，答案唯一且正确。
3.  **迷惑性（选择题）**：错误选项 (Distractors) 必须具有高度的迷惑性，是基于常见误解设计的，而不能是明显无关的选项。

# 数量与格式要求 (【强制】)
请**严格且仅**输出一个符合以下格式的 JSON 对象。**禁止**在 JSON 对象前后添加任何开场白、解释、总结或 Markdown 标记 (如 ```json ... ```)。

**数量**：必须包含 **8 个** `single-choice` 题目 和 **2 个** `short-answer` 题目。

**JSON 格式**：
{{
  "title": "{core_topic}",
  "single-choice": [
    {{
      "question": "（这里是第 1 个选择题问题）",
      "options": ["A. 选项A", "B. 选项B", "C. 选项C", "D. 选项D"],
      "right-answer": "（A, B, C 或 D）"
    }},
    {{
      "question": "（这里是第 2 个选择题问题）",
      "options": ["A. 选项A", "B. 选项B", "C. 选项C", "D. 选项D"],
      "right-answer": "（A, B, C 或 D）"
    }},
    {{
      "question": "（这里是第 3 个选择题问题）",
      "options": ["A. 选项A", "B. 选项B", "C. 选项C", "D. 选项D"],
      "right-answer": "（A, B, C 或 D）"
    }},
    {{
      "question": "（这里是第 4 个选择题问题）",
      "options": ["A. 选项A", "B. 选项B", "C. 选项C", "D. 选项D"],
      "right-answer": "（A, B, C 或 D）"
    }},
    {{
      "question": "（这里是第 5 个选择题问题）",
      "options": ["A. 选项A", "B. 选项B", "C. 选项C", "D. 选项D"],
      "right-answer": "（A, B, C 或 D）"
    }},
    {{
      "question": "（这里是第 6 个选择题问题）",
      "options": ["A. 选项A", "B. 选项B", "C. 选项C", "D. 选项D"],
      "right-answer": "（A, B, C 或 D）"
    }},
    {{
      "question": "（这里是第 7 个选择题问题）",
      "options": ["A. 选项A", "B. 选项B", "C. 选项C", "D. 选项D"],
      "right-answer": "（A, B, C 或 D）"
    }},
    {{
      "question": "（这里是第 8 个选择题问题）",
      "options": ["A. 选项A", "B. 选项B", "C. 选项C", "D. 选项D"],
      "right-answer": "（A, B, C 或 D）"
    }}
  ],
  "short-answer": [
    {{
      "question": "（这里是第 1 个简答题）"
    }},
    {{
      "question": "（这里是第 2 个简答题）"
    }}
  ]
}}
请使用 {language} **回复**。
"""

    human_message = (
        f"主题：{topic}\n\n"
        f"请使用 {language} 生成高质量的测验题目，包含15个选择题和5个主观题。"
        f"题目应该覆盖该主题的核心概念、关键技术和实际应用。"
    )

    return ChatPromptTemplate.from_messages(
        [("system", system_message), ("human", human_message)]
    )


def assess_knowledge_level_prompt(
    topic: str, score_percentage: float, language: str = "en"
) -> ChatPromptTemplate:
    system_message = (
        "你是一位专家导师，根据学生的测验结果来评估他们的知识水平。\n"
        "提供一个**简短而深刻的总结**，并提出**具体的**下一步学习步骤。\n"
        f"请使用 {language} **回复**。"
    )

    human_message = (
        f"主题: {topic}\n"
        f"得分百分比: {score_percentage}\n\n"
        f"评估知识水平，并提出下一步的改进步骤。"
    )

    return ChatPromptTemplate.from_messages(
        [("system", system_message), ("human", human_message)]
    )


def generate_QUESTION_TEMPLATE(core_topic):
    return f"""
# 角色与任务 🎯
你是一位资深的**教育评估专家**和**专业命题人**。你的任务是根据给定的核心主题，生成一套高质量、严谨的测验题。

# 核心主题
本套测验的核心主题是：**{core_topic}**

# 质量与严谨性要求 🧐
1.  **专业性**：题目必须反映该主题的核心概念和关键知识点。
2.  **严谨性**：问题表述清晰无歧义，答案唯一且正确。
3.  **迷惑性（选择题）**：错误选项 (Distractors) 必须具有高度的迷惑性，是基于常见误解设计的，而不能是明显无关的选项。

# 数量与格式要求 (【强制】)
请**严格且仅**输出一个符合以下格式的 JSON 对象。**禁止**在 JSON 对象前后添加任何开场白、解释、总结或 Markdown 标记 (如 ```json ... ```)。

**数量**：必须包含 **8 个** `single-choice` 题目 和 **2 个** `short-answer` 题目。

!!!注意fillinblank是简答题而不是填空题。选择题需要给出答案。选择题包含三个字段[question,options,right-answer]。主观题包含一个字段"question"

**JSON 格式**：
{{
  "title": "{core_topic}",
  "single-choice": [
    {{
      "question": "（这里是第 1 个选择题问题）",
      "options": ["A. 选项A", "B. 选项B", "C. 选项C", "D. 选项D"],
      "right-answer": "（A, B, C 或 D）"
    }},
    {{
      "question": "（这里是第 2 个选择题问题）",
      "options": ["A. 选项A", "B. 选项B", "C. 选项C", "D. 选项D"],
      "right-answer": "（A, B, C 或 D）"
    }},
    {{
      "question": "（这里是第 3 个选择题问题）",
      "options": ["A. 选项A", "B. 选项B", "C. 选项C", "D. 选项D"],
      "right-answer": "（A, B, C 或 D）"
    }},
    {{
      "question": "（这里是第 4 个选择题问题）",
      "options": ["A. 选项A", "B. 选项B", "C. 选项C", "D. 选项D"],
      "right-answer": "（A, B, C 或 D）"
    }},
    {{
      "question": "（这里是第 5 个选择题问题）",
      "options": ["A. 选项A", "B. 选项B", "C. 选项C", "D. 选项D"],
      "right-answer": "（A, B, C 或 D）"
    }},
    {{
      "question": "（这里是第 6 个选择题问题）",
      "options": ["A. 选项A", "B. 选项B", "C. 选项C", "D. 选项D"],
      "right-answer": "（A, B, C 或 D）"
    }},
    {{
      "question": "（这里是第 7 个选择题问题）",
      "options": ["A. 选项A", "B. 选项B", "C. 选项C", "D. 选项D"],
      "right-answer": "（A, B, C 或 D）"
    }},
    {{
      "question": "（这里是第 8 个选择题问题）",
      "options": ["A. 选项A", "B. 选项B", "C. 选项C", "D. 选项D"],
      "right-answer": "（A, B, C 或 D）"
    }}
  ],
  "short-answer": [
    {{
      "question": "（这里是第 1 个简答题）"
    }},
    {{
      "question": "（这里是第 2 个简答题）"
    }}
  ]
}}
再次提示：
1.主观题不是填空题，应该是答题者用一段话回答。
2. 选择题必须把答案一起输出在json中
"""
