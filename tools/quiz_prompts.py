from langchain_core.prompts import ChatPromptTemplate

def generate_topic_list_prompt(subject: str, language: str = "zh") -> ChatPromptTemplate:
    system_message = (
        f"你是教育课程设计方面的专家。你是一位专家导师，根据学生的测验结果来评估他们的知识水平。\n" # 保持原有中文信息
        f"您的任务是生成最可检查的子主题的逻辑结构化列表。\n" # 保持原有中文信息
        f"请**仅**使用 {language} **回复**。**不要**包含任何解释。" # 翻译并保留 {language}
    )

    human_message = (
        f"主题: {subject}\n\n" # 保持原有中文信息和 {subject}
        f"请创建一个核心主题的**项目符号列表**，这些主题可用于**创建测验**。" # 翻译
    )

    return ChatPromptTemplate.from_messages([
        ("system", system_message),
        ("human", human_message)
    ])

def generate_questions_prompt(topic: str, language: str = "en") -> ChatPromptTemplate:
    """
    Generates a prompt template to create multiple-choice quiz questions in the specified language.
    """
    system_message = (
        f"你是一位准备技术主题**多项选择测验题**的专业教育工作者。\n" # 翻译
        f"**所有内容**都**必须严格**使用 {language} **撰写**。\n" # 翻译并保留 {language}
        "对于每个问题：\n"
        "- **精确地**提供 **4 个**答案选项，并标记为 a)、b)、c)、d)\n" # 翻译
        "- 以此行**结束**：Correct Answer: [a/b/c/d]（**必须**是这些选项之一）\n" # 翻译
        "- 问题必须**与领域相关**、**清晰**且**难度多样**\n" # 翻译
        "- **不要**解释答案。**只**输出符合指定格式的问题。\n" # 翻译
        "**重要提示**：**不要**跳过 'Correct Answer' 行。**每个**问题都**必须**有它。" # 翻译
    )

    human_message = (
        f"主题： {topic}\n\n" # 保持原有中文信息和 {topic}
        f"使用 {language} **生成**一组**高质量**的**选择题**。" # 翻译并保留 {language}
    )

    return ChatPromptTemplate.from_messages([
        ("system", system_message),
        ("human", human_message)
    ])


def assess_knowledge_level_prompt(topic: str, score_percentage: float, language: str = "en") -> ChatPromptTemplate:
    system_message = (
        "你是一位专家导师，根据学生的测验结果来评估他们的知识水平。\n" # 保持原有中文信息
        "提供一个**简短而深刻的总结**，并提出**具体的**下一步学习步骤。\n" # 保持原有中文信息
        f"请使用 {language} **回复**。" # 翻译并保留 {language}
    )

    human_message = (
        f"主题: {topic}\n" # 保持原有中文信息和 {topic}
        f"得分百分比: {score_percentage}\n\n" # 保持原有中文信息和 {score_percentage}
        f"评估知识水平，并提出下一步的改进步骤。" # 保持原有中文信息
    )

    return ChatPromptTemplate.from_messages([
        ("system", system_message),
        ("human", human_message)
    ])