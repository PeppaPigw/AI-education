from tools.quiz_prompts import generate_topic_list_prompt, generate_questions_prompt
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableLambda, RunnableParallel
from LearningPlanModule.learning_plan import LearningPlan
from tools.auto_answer import auto_answer
from tools.rag_service import RAGService
from tools.rag_utils import get_context_or_empty
from tools.llm_logger import get_llm_logger
import logging
from dotenv import load_dotenv
import os

load_dotenv()
model_name = os.environ.get("model_name")
base_url = os.environ.get("base_url")
api_key = os.environ.get("api_key")
logger = logging.getLogger(__name__)


def prepare_quiz_questions(
    subject: str, language: str = "en", retriever=None
) -> tuple[list[dict], bool]:
    llm = ChatOpenAI(
        model=model_name, temperature=0, base_url=base_url, api_key=api_key
    )

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
    
    llm_logger = get_llm_logger()
    llm_logger.log_llm_call(
        messages=[{"role": "user", "content": topic_prompt.format_prompt(subject=prompt_subject).to_string()}],
        response=topic_result,
        model=model_name,
        module="QuizModule.quiz_operations",
        metadata={"function": "prepare_quiz_questions", "step": "generate_topics", "subject": subject, "language": language}
    )
    
    topics = [t.strip() for t in topic_result.content.split("\n") if t.strip()]
    if not topics:
        return [], used_retriever

    max_questions = 20
    max_topics = min(len(topics), 5)
    topics = topics[:max_topics]
    if max_topics == 0:
        return [], used_retriever

    questions_per_topic = max_questions // max_topics

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
            | RunnableLambda(
                lambda d: (d["ctx"] + "\n\n" if d["ctx"] else "")
                + d["prompt"].to_string()
            )
            | llm
        )
    else:
        question_chain = (
            RunnableLambda(
                lambda inputs: generate_questions_prompt(
                    inputs["topic"], language=language
                ).format_prompt(topic=inputs["topic"])
            )
            | llm
        )

    question_sets = question_chain.batch([{"topic": t} for t in topics])

    llm_logger = get_llm_logger()
    for topic, qset in zip(topics, question_sets):
        llm_logger.log_llm_call(
            messages=[{"role": "user", "content": f"Generate questions for topic: {topic}"}],
            response=qset,
            model=model_name,
            module="QuizModule.quiz_operations",
            metadata={"function": "prepare_quiz_questions", "step": "generate_questions", "topic": topic, "language": language}
        )

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
            questions_list.append(
                {"topic": topic, "question": text, "correct": correct}
            )

    return questions_list, used_retriever


def generate_quiz(subject: str, language: str = "en", retriever=None):
    if retriever is None:
        retriever = RAGService().get_retriever()

    try:
        questions, used_retriever = prepare_quiz_questions(
            subject, language=language, retriever=retriever
        )
        if not questions:
            print("\u26a0\ufe0f No quiz topics generated.")
            return {}
        logger.info("小测基于 RAG 生成: %s", used_retriever)

        print("\n开始测验...\n")
        user_scores = {}
        total_questions = 0
        total_correct = 0

        for q in questions:
            topic = q["topic"]
            question = q["question"]
            correct = q["correct"]
            if topic not in user_scores:
                user_scores[topic] = [0, 0]
                print(f"主题: {topic}\n")

            try:
                print(question)
                while True:
                    user_answer = input("你的作答: ")
                    if not auto_answer(user_answer):
                        break
                user_answer = user_answer.strip().lower()
                if user_answer == correct:
                    print("正确!\n")
                    user_scores[topic][0] += 1
                elif correct == "?":
                    user_scores[topic][0] += 1
                else:
                    print(f"错误的！正确的答案是： {correct}\n")
                user_scores[topic][1] += 1
                total_correct += 1 if user_answer == correct or correct == "?" else 0
                total_questions += 1
            except Exception as e:
                print(f"解析问题或答案错误: {e}")

        print("\n最终结果:")
        overall_percentage = 0
        for topic, (correct_num, total_num) in user_scores.items():
            percentage = (correct_num / total_num) * 100 if total_num > 0 else 0
            overall_percentage += percentage
            print(
                f"主题: {topic} - Score: {correct_num}/{total_num} ({percentage:.2f}%)"
            )
        overall_percentage /= len(user_scores) if user_scores else 1
        print(f"\n总分: {total_correct}/{total_questions} ({overall_percentage:.2f}%)")

        return user_scores

    except Exception as e:
        print(f"在生成测试时发生错误： {e}")
        return {}


def generate_learning_plan_from_quiz(user_name, quiz_results, language="en"):
    plan = LearningPlan(
        user_name=user_name, quiz_results=quiz_results, user_language=language
    )
    learning_plan = plan.generate_plan()
    plan.display_plan()
    return learning_plan
