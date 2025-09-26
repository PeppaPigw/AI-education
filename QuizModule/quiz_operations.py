"""Utility functions for quiz generation and learning plan creation.

The module drives the question generation workflow by composing LangChain
``Runnable`` chains.  Each quiz can optionally leverage a retrieval-augmented
generation (RAG) pipeline: when a retriever is supplied, additional context is
fetched and appended to prompts.  Generated quiz results may later feed into
``LearningPlanModule`` to build personalised study schedules.
"""

from tools.quiz_prompts import generate_topic_list_prompt, generate_questions_prompt
from langchain_openai import ChatOpenAI
from langchain.schema.runnable import RunnableLambda, RunnableParallel
from LearningPlanModule.learning_plan import LearningPlan
from tools.auto_answer import auto_answer
from tools.rag_service import RAGService
from tools.rag_utils import get_context_or_empty
import logging
from dotenv import load_dotenv
import os
load_dotenv()
model_name=os.environ.get("model_name")
base_url=os.environ.get("base_url")
api_key=os.environ.get("api_key")
logger = logging.getLogger(__name__)


def prepare_quiz_questions(
    subject: str, language: str = "en", retriever=None
) -> tuple[list[dict], bool]:
    """Generate a list of quiz questions for ``subject``.

    The function expands the subject into sub-topics and then uses parallel
    LangChain pipelines to build multiple‑choice questions.  When a retriever is
    provided, context retrieved from the vector store is prepended to prompts to
    enable RAG-assisted question generation.

    Returns a tuple of the question dictionaries and a flag indicating whether
    the retriever was utilised.
    """
    llm = ChatOpenAI(model=model_name, temperature=0,base_url=base_url,api_key=api_key)

    if retriever is None:
        retriever = RAGService().get_retriever()

    context = get_context_or_empty(subject, retriever)
    used_retriever = bool(context)
    logger.info("Quiz generation used RAG: %s", used_retriever)

    prompt_subject = subject
    if context:
        prompt_subject = f"{subject}\n\nContext:\n{context}"

    # Generate topics
    topic_prompt = generate_topic_list_prompt(prompt_subject, language)
    topic_result = llm.invoke(topic_prompt.format_prompt(subject=prompt_subject))
    topics = [t.strip() for t in topic_result.content.split("\n") if t.strip()]
    if not topics:
        return [], used_retriever

    max_questions = 20
    max_topics = min(len(topics), 5)
    topics = topics[:max_topics]
    if max_topics == 0:
        return [], used_retriever

    questions_per_topic = max_questions // max_topics

    # Generate questions in parallel
    if retriever:
        def _topic_ctx(inputs):
            return get_context_or_empty(inputs["topic"], retriever)

        context_chain = RunnableLambda(_topic_ctx)
        prompt_chain = RunnableLambda(
            lambda inputs: generate_questions_prompt(
                inputs["topic"], language=language
            ).format_prompt(topic=inputs["topic"])
        )
        question_chain = (
            RunnableParallel({"ctx": context_chain, "prompt": prompt_chain})
            | RunnableLambda(lambda d: (d["ctx"] + "\n\n" if d["ctx"] else "") + d["prompt"].to_string())
            | llm
        )
    else:
        question_chain = RunnableLambda(
            lambda inputs: generate_questions_prompt(
                inputs["topic"], language=language
            ).format_prompt(topic=inputs["topic"])
        ) | llm

    question_sets = question_chain.batch([{"topic": t} for t in topics])

    questions_list = []
    for topic, qset in zip(topics, question_sets):
        q_texts = qset.content.split("\n\n")[:questions_per_topic]
        for q in q_texts:
            raw_correct = q.split("Correct Answer: ")[-1].strip().lower()
            correct = (
                raw_correct[0]
                if raw_correct and raw_correct[0] in ["a", "b", "c", "d"]
                else "?"
            )
            text = q.rsplit("Correct Answer", 1)[0].strip()
            questions_list.append({"topic": topic, "question": text, "correct": correct})

    return questions_list, used_retriever

def generate_quiz(subject: str, language: str = "en", retriever=None):
    """Run an interactive quiz in the terminal and return the results.

    A ``retriever`` may be provided to enrich question prompts with additional
    context.
    """
    if retriever is None:
        retriever = RAGService().get_retriever()

    try:
        questions, used_retriever = prepare_quiz_questions(
            subject, language=language, retriever=retriever
        )
        if not questions:
            print("\u26a0\ufe0f No quiz topics generated.")
            return {}
        logger.info("Interactive quiz used RAG: %s", used_retriever)

        print("\nStarting the quiz...\n")
        user_scores = {}
        total_questions = 0
        total_correct = 0

        for q in questions:
            topic = q["topic"]
            question = q["question"]
            correct = q["correct"]
            if topic not in user_scores:
                user_scores[topic] = [0, 0]
                print(f"Topic: {topic}\n")

            try:
                print(question)
                while True:
                    user_answer = input("Your answer: ")
                    if not auto_answer(user_answer):
                        break
                user_answer = user_answer.strip().lower()
                if user_answer == correct:
                    print("Correct!\n")
                    user_scores[topic][0] += 1
                elif correct == "?":
                    user_scores[topic][0] += 1
                else:
                    print(f"Wrong! The correct answer is: {correct}\n")
                user_scores[topic][1] += 1
                total_correct += 1 if user_answer == correct or correct == "?" else 0
                total_questions += 1
            except Exception as e:
                print(f"Error parsing question or answer: {e}")

        print("\nFinal Results:")
        overall_percentage = 0
        for topic, (correct_num, total_num) in user_scores.items():
            percentage = (correct_num / total_num) * 100 if total_num > 0 else 0
            overall_percentage += percentage
            print(f"Topic: {topic} - Score: {correct_num}/{total_num} ({percentage:.2f}%)")
        overall_percentage /= len(user_scores) if user_scores else 1
        print(f"\nOverall Score: {total_correct}/{total_questions} ({overall_percentage:.2f}%)")

        return user_scores

    except Exception as e:
        print(f"An error occurred while generating the quiz: {e}")
        return {}

def generate_learning_plan_from_quiz(user_name, quiz_results, language="en"):
    """
    Generates a learning plan based on quiz results.
    """
    plan = LearningPlan(user_name=user_name, quiz_results=quiz_results, user_language=language)
    learning_plan = plan.generate_plan()
    plan.display_plan()
    return learning_plan
