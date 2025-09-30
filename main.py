from dotenv import load_dotenv
from QuizModule import generate_quiz, generate_learning_plan_from_quiz
from LearningPlanModule import LearningPlan
from SummaryModule import StudySummaryGenerator
from AgentModule import create_agent
from AgentModule.edu_agent import run_agent
from frontend_service import launch_gradio
from tools.auto_answer import auto_answer
from tools.language_handler import LanguageHandler
from tools.ingest import ingest_folder
from tools.rag_service import get_rag_service
import os
import sys
import warnings
from langchain_core._api import LangChainDeprecationWarning

# Load environment variables from .env
dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path)
model_name=os.environ.get("model_name")
base_url=os.environ.get("base_url")
api_key=os.environ.get("api_key")
# Ensure the OpenAI API key is set before continuing
if not os.getenv("api_key"):
    print("Error: api_key environment variable is not set. "
          "Please set it before running the application.")
    sys.exit(1)

warnings.filterwarnings(
    "ignore",
    message="fields may not start with an underscore",
    category=RuntimeWarning,
)
warnings.filterwarnings("ignore", category=LangChainDeprecationWarning)

# Create a single agent instance for handling on-demand questions
_agent = create_agent()

# Instantiate a global retriever for RAG operations
_rag_service = get_rag_service()
retriever = _rag_service.get_retriever()


def prompt_input(prompt: str) -> str:
    """Input wrapper that auto-runs the agent on questions."""
    user = input(prompt).strip()
    if auto_answer(user, _agent):
        return prompt_input(prompt)
    return user


def chat_with_bot():
    """Chat with the assistant."""
    try:
        print("You can now chat with the bot. Type 'exit' or 'q' to quit.")
        chat_history = []

        while True:
            query = prompt_input("You: ")
            if query.lower() in ["exit", "q"]:
                break
            language = LanguageHandler.choose_or_detect(query)
            answer, used_fallback, used_retriever = run_agent(
                query, executor=_agent, retriever=retriever, return_details=True
            )
            answer = LanguageHandler.ensure_language(answer, language)
            if used_fallback:
                notice = LanguageHandler.ensure_language(
                    "This response may not be accurate. It was created using a LMM fallback mechanism.",
                    language,
                )
                answer = f"{notice}\n{answer}"
            elif used_retriever:
                notice = LanguageHandler.ensure_language(
                    "This response was created using a document retrieval mechanism.",
                    language,
                )
                answer = f"{notice}\n{answer}"
            print(f"AI: {answer}")
            chat_history.append((query, answer))

        print("---- Message History ----")
        for q, a in chat_history:
            print(f"You: {q}")
            print(f"AI: {a}")

    except Exception as e:
        print(f"An error occurred while chatting with the bot: {e}")

if __name__ == "__main__":

    launch_gradio()
