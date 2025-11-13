from tools.quiz_prompts import generate_topic_list_prompt, generate_questions_prompt
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableLambda, RunnableParallel
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


class Quiz_Agent:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.llm = ChatOpenAI(
            model=model_name, temperature=0, base_url=base_url, api_key=api_key
        )

    def prepare_quiz_questions(
        self, subject: str, language: str = "en", retriever=None
    ) -> tuple[list[dict], bool]:
        if retriever is None:
            retriever = RAGService().get_retriever()

        context = get_context_or_empty(subject, retriever)
        used_retriever = bool(context)
        self.logger.info("Quiz generation used RAG: %s", used_retriever)

        prompt_subject = subject
        if context:
            prompt_subject = f"{subject}\n\nContext:\n{context}"

        topic_prompt = generate_topic_list_prompt(prompt_subject, language)
        topic_result = self.llm.invoke(
            topic_prompt.format_prompt(subject=prompt_subject)
        )

        llm_logger = get_llm_logger()
        llm_logger.log_llm_call(
            messages=[
                {
                    "role": "user",
                    "content": topic_prompt.format_prompt(
                        subject=prompt_subject
                    ).to_string(),
                }
            ],
            response=topic_result,
            model=model_name,
            module="QuizModule.quiz_agent",
            metadata={
                "function": "prepare_quiz_questions",
                "step": "generate_topics",
                "subject": subject,
                "language": language,
            },
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
                | self.llm
            )
        else:
            question_chain = (
                RunnableLambda(
                    lambda inputs: generate_questions_prompt(
                        inputs["topic"], language=language
                    ).format_prompt(topic=inputs["topic"])
                )
                | self.llm
            )

        question_sets = question_chain.batch([{"topic": t} for t in topics])

        llm_logger = get_llm_logger()
        for topic, qset in zip(topics, question_sets):
            llm_logger.log_llm_call(
                messages=[
                    {
                        "role": "user",
                        "content": f"Generate questions for topic: {topic}",
                    }
                ],
                response=qset,
                model=model_name,
                module="QuizModule.quiz_agent",
                metadata={
                    "function": "prepare_quiz_questions",
                    "step": "generate_questions",
                    "topic": topic,
                    "language": language,
                },
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
