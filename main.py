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


def main_menu():
    """Main menu for the application."""
    while True:
        print("\nSelect an option:")
        print("0. Set preferred language")
        print("1. Chat with the bot (no articles required)")
        print("2. Generate a quiz")
        print("3. Create a personalized learning plan")
        print("4. Flashcards: Generate from prompt")
        print("5. Flashcards: Review from file")
        print("6. Generate TL;DR Summary")
        print("7. Generate Cheat Sheet")
        print("8. Exit")
        print("9. Refresh knowledge base")

        choice = prompt_input("Enter the number of your choice: ").strip()

        if choice == "0":
            print(
                "Enter your preferred language code (e.g. en, pl, de, fr) or 'auto' to detect automatically each time:"
            )
            lang = prompt_input("Language: ").strip()
            LanguageHandler.set_language(lang)
            print(f"Language set to: {lang}")

        elif choice == "1":
            chat_with_bot()

        elif choice == "2":
            subject = prompt_input("Enter the subject for the quiz: ")
            language = LanguageHandler.choose_or_detect(subject)
            generate_quiz(subject, language=language, retriever=retriever)

        elif choice == "3":
            print("\nSelect an option:")
            print("1. Take a quiz to generate a learning plan")
            print("2. Input custom learning goals")
            sub_choice = prompt_input("Enter your choice: ").strip()

            if sub_choice == "1":
                subject = prompt_input("Enter the subject for the quiz: ")
                language = LanguageHandler.choose_or_detect(subject)
                quiz_results = generate_quiz(
                    subject, language=language, retriever=retriever
                )
                user_name = prompt_input("Enter your name: ")
                generate_learning_plan_from_quiz(user_name, quiz_results, language)
            elif sub_choice == "2":
                user_name = prompt_input("Enter your name: ")
                goals_input = prompt_input(
                    "Enter your learning goals (comma-separated): "
                )
                language = LanguageHandler.choose_or_detect(goals_input)
                user_input = {
                    "goals": [goal.strip() for goal in goals_input.split(",")]
                }
                plan = LearningPlan(user_name=user_name, user_language=language)
                plan.generate_plan_from_prompt(user_input)
                plan.display_plan()
                plan.save_to_file()
            else:
                print("Invalid choice. Please try again.")

        elif choice == "4":
            topic = prompt_input("Enter a topic for flashcard generation: ")
            language = LanguageHandler.choose_or_detect(topic)
            flashcards = FlashcardSet(topic, retriever=retriever)
            flashcards.generate_from_prompt(
                topic_prompt=topic, language=language, retriever=retriever
            )
            flashcards.save_to_file()

        elif choice == "5":
            path = prompt_input("Enter path to flashcard JSON file: ")
            flashcards = FlashcardSet.load_from_file(path)
            if flashcards:
                flashcards.run_cli_review()

        elif choice == "6":
            topic = prompt_input("Enter the topic or material for TL;DR summary: ")
            language = LanguageHandler.choose_or_detect(topic)
            summarizer = StudySummaryGenerator(retriever=retriever)
            summary = summarizer.generate_summary(
                topic, language=language, retriever=retriever
            )
            print("\n📘 Summary:\n")
            print(summary)

        elif choice == "7":
            topic = prompt_input("Enter the topic or material for the cheat sheet: ")
            language = LanguageHandler.choose_or_detect(topic)
            
            cheatsheet = generator.generate_cheatsheet(
                topic, language=language, retriever=retriever
            )
            print("\n📄 Cheat Sheet:\n")
            print(cheatsheet)

        elif choice == "9":
            docs, chunks = ingest_folder()
            if docs:
                print(f"Ingested {docs} documents as {chunks} chunks.")
            else:
                print("No documents found for ingestion.")

        elif choice in ("8", "q", "quit"):
            print("Goodbye!")
            break

        else:
            print("Invalid choice. Please try again.")


if __name__ == "__main__":

    launch_gradio()
