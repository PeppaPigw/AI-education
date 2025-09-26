"""Flashcard generation and review utilities.

The module provides classes for representing flashcards, generating them from
quizzes or free‑form prompts, and persisting decks to disk.  Retrieval‑augmented
generation (RAG) can be used to supply additional context when creating new
cards.
"""
import json
import os
import re
from datetime import datetime
import logging

from langchain.schema.runnable import RunnableLambda
from langchain_openai import ChatOpenAI
from tools.auto_answer import auto_answer
from tools.rag_service import RAGService
from tools.rag_utils import get_context_or_empty
from dotenv import load_dotenv
import os
load_dotenv()
model_name=os.environ.get("model_name")
base_url=os.environ.get("base_url")
api_key=os.environ.get("api_key")
logger = logging.getLogger(__name__)


class Flashcard:
    """
    Represents a single flashcard with a question and an answer.
    """

    def __init__(self, question: str, answer: str):
        self.question = question.strip()
        self.answer = answer.strip()

    def to_dict(self):
        return {"question": self.question, "answer": self.answer}

    @staticmethod
    def from_dict(data):
        return Flashcard(question=data["question"], answer=data["answer"])


class FlashcardSet:
    """
    Manages a set of flashcards: generation, review, and saving.
    """

    def __init__(self, topic: str, flashcards=None, retriever=None):
        self.topic = topic.strip()
        self.flashcards = flashcards if flashcards else []
        if retriever is None:
            retriever = RAGService().get_retriever()
        self.retriever = retriever  # optional document retriever

    def add_flashcard(self, flashcard: Flashcard):
        self.flashcards.append(flashcard)

    def generate_from_quiz_text(self, raw_text: str):
        """
        Parses quiz-style text and extracts flashcards from question blocks.
        """
        blocks = raw_text.strip().split("\n\n")
        for block in blocks:
            try:
                question_match = re.search(r"Question:\s*(.*)", block)
                correct_match = re.search(r"Correct Answer:\s*([a-d])", block)
                options = re.findall(r"[a-d]\)\s*(.*)", block)

                if question_match and correct_match and options:
                    idx = ord(correct_match.group(1).lower()) - ord("a")
                    answer = options[idx]
                    self.add_flashcard(
                        Flashcard(question=question_match.group(1), answer=answer)
                    )
            except Exception as e:
                print(f"⚠️ Error parsing block: {e}")

    def generate_from_prompt(
        self,
        topic_prompt: str,
        language: str = "en",
        retriever=None,
    ):
        """
        Uses an LLM to generate flashcards based on a topic prompt.
        If a ``retriever`` is supplied (or the set has one), relevant documents are
        fetched and prepended to the prompt as context.
        """
        llm = ChatOpenAI(model=model_name, temperature=0,base_url=base_url,api_key=api_key)
        retriever = retriever or self.retriever
        if retriever is None:
            retriever = RAGService().get_retriever()

        ctx = get_context_or_empty(topic_prompt, retriever)
        used_retriever = bool(ctx)
        logger.info("Flashcard generation used RAG: %s", used_retriever)

        def _build_prompt(inputs):
            context = inputs["context"]
            topic = inputs["topic_prompt"]
            prompt = ""
            if context:
                prompt += context + "\n\n"
            prompt += (
                f"You are an expert educator preparing students for a rigorous test or exam.\n"
                f'Generate a high-quality, detailed list of flashcards for the topic: "{topic}".\n'
                f"The flashcards should include:\n"
                f"- definitions of core concepts\n"
                f"- names and explanations of key theorems or formulas\n"
                f"- concrete, technical facts that are often tested\n"
                f"- pay attention to the detailed domain knowledge needed by specialists at the level indicated by the user\n"
                f"Each flashcard must follow this format:\n"
                f"Q: [Clear, technical question]\n"
                f"A: [Precise, exam-focused answer]\n\n"
                f"Don't include explanations, examples, or anything besides flashcards.\n"
                f"Respond in {inputs['language']}."
            )
            return prompt

        chain = RunnableLambda(_build_prompt) | llm

        try:
            response = chain.invoke(
                {
                    "topic_prompt": topic_prompt,
                    "language": language,
                    "context": ctx,
                }
            )
            raw_output = response.content

            pairs = re.findall(
                r"(?:\d+\.\s*)?Q:\s*(.+?)\s*A:\s*(.+?)(?=\s*(?:\d+\.\s*)?Q:|\Z)",
                raw_output,
                re.DOTALL,
            )

            for q, a in pairs:
                self.add_flashcard(Flashcard(q.strip(), a.strip()))

            print(f"✅ Generated {len(self.flashcards)} flashcards from prompt.")
        except Exception as e:
            print(f"❌ Error generating flashcards from prompt: {e}")
        return used_retriever

    def run_cli_review(self):
        """Simple CLI loop for reviewing the flashcards."""
        print(f"\n📚 Reviewing flashcards for topic: {self.topic}")
        for i, card in enumerate(self.flashcards, start=1):
            print(f"\n{i}. {card.question}")
            while True:
                user = input("Your answer: ")
                if not auto_answer(user):
                    break
            print(f"✅ Correct answer: {card.answer}")

    def save_to_file(self, base_dir="data/flashcards/"):
        """
        Saves the flashcard set to a JSON file.
        """
        os.makedirs(base_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.topic}_flashcards_{timestamp}.json"
        path = os.path.join(base_dir, filename)

        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.to_dict_list(), f, indent=4, ensure_ascii=False)
            print(f"💾 Flashcards saved to {path}")
            return path
        except Exception as e:
            print(f"❌ Failed to save flashcards: {e}")
            return ""

    @staticmethod
    def load_from_file(path: str):
        """
        Loads a flashcard set from a JSON file.
        """
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                topic = os.path.basename(path).split("_flashcards_")[0]
                cards = [Flashcard.from_dict(fc) for fc in data]
                return FlashcardSet(topic=topic, flashcards=cards)
        except Exception as e:
            print(f"❌ Failed to load flashcards: {e}")
            return None

    def to_dict_list(self):
        """
        Returns list of flashcards as list of dicts (e.g. for JSON API).
        """
        return [fc.to_dict() for fc in self.flashcards]
