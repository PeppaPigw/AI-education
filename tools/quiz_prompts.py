from langchain_core.prompts import ChatPromptTemplate

def generate_topic_list_prompt(subject: str, language: str = "en") -> ChatPromptTemplate:
    """
    Generates a prompt template to create a list of quiz topics in the specified language.
    """
    system_message = (
        f"You are an expert in educational curriculum design.\n"
        f"Your task is to generate a logically structured list of the most examinable subtopics.\n"
        f"Respond exclusively in {language}. Do not include explanations."
    )

    human_message = (
        f"Subject: {subject}\n\n"
        f"Create a bullet list of core topics that could be used to create a quiz."
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
        f"You are a professional educator preparing multiple-choice quiz questions for a technical topic.\n"
        f"Write all content STRICTLY in {language}.\n"
        "For each question:\n"
        "- Provide EXACTLY 4 answer options labeled a), b), c), d)\n"
        "- End with the line: Correct Answer: [a/b/c/d] (must be one of these options)\n"
        "- Questions must be domain-relevant, clear, and varied in difficulty\n"
        "- Do NOT explain answers. Only output questions in the specified format.\n"
        "IMPORTANT: Do not skip the 'Correct Answer' line. Every question must have it."
    )

    human_message = (
        f"Topic: {topic}\n\n"
        f"Generate a high-quality set of multiple-choice questions in {language}."
    )

    return ChatPromptTemplate.from_messages([
        ("system", system_message),
        ("human", human_message)
    ])


def assess_knowledge_level_prompt(topic: str, score_percentage: float, language: str = "en") -> ChatPromptTemplate:
    """
    Generates a prompt to assess user's knowledge level based on their quiz performance for a specific topic.
    """
    system_message = (
        "You are an expert tutor assessing a student's knowledge level based on their quiz result. "
        "Provide a short but insightful summary and suggest concrete next steps for learning. "
        f"Respond in {language}."
    )

    human_message = (
        f"Topic: {topic}\n"
        f"Score Percentage: {score_percentage}\n\n"
        f"Assess the knowledge level and suggest next steps for improvement."
    )

    return ChatPromptTemplate.from_messages([
        ("system", system_message),
        ("human", human_message)
    ])
