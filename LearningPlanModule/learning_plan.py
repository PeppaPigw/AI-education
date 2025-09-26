"""Creation and persistence of personalised learning plans.

The module analyses quiz performance or user‑specified goals to schedule study
sessions.  It can call an LLM to recommend resources and optionally augment
suggestions with context retrieved from a document store.
"""
import json
import os
from datetime import date, timedelta, datetime
from langchain_openai import ChatOpenAI
from tools.rag_service import RAGService
from tools.rag_utils import get_context_or_empty
from dotenv import load_dotenv
import os
load_dotenv()
model_name=os.environ.get("model_name")
base_url=os.environ.get("base_url")
api_key=os.environ.get("api_key")
# TODO: use cases from prompts for edu

class LearningPlan:
    """Container for generated study activities and resource suggestions.

    Parameters
    ----------
    user_name:
        Name of the learner for whom the plan is generated.
    quiz_results:
        Mapping of topics to a ``(correct, total)`` tuple produced by the quiz
        module.  If omitted, ``generate_plan_from_prompt`` can create a plan
        from user goals instead.
    user_goals:
        Optional user-defined objectives used when quiz results are absent.
    user_language:
        Language code for any LLM output.
    retriever:
        Optional retriever for RAG‑enhanced material recommendations.
    """
    def __init__(
        self, user_name, quiz_results=None, user_goals=None, user_language="en", retriever=None
    ):
        self.user_name = user_name
        self.quiz_results = quiz_results if quiz_results else {}
        self.user_goals = user_goals if user_goals else {}
        self.user_language = user_language
        self.learning_plan = []
        self.llm = ChatOpenAI(model=model_name, temperature=0,base_url=base_url,api_key=api_key)
        if retriever is None:
            retriever = RAGService().get_retriever()
        self.retriever = retriever

    def analyze_quiz_results(self):
        """
        Analyze quiz results and classify topics based on knowledge gaps.
        """
        critical_areas = []  # Score below 50%
        moderate_areas = []  # Score between 50% and 70%
        good_areas = []      # Score above 70%

        for topic, (correct_answers, total_questions) in self.quiz_results.items():
            if total_questions == 0:  # Uniknięcie dzielenia przez zero
                percentage_score = 0
            else:
                percentage_score = (correct_answers / total_questions) * 100

            if percentage_score < 50:
                critical_areas.append(topic)
            elif 50 <= percentage_score < 70:
                moderate_areas.append(topic)
            else:
                good_areas.append(topic)

        return critical_areas, moderate_areas, good_areas

    def generate_plan(self):
        """
        Generate a learning plan based on quiz analysis.
        """
        critical_areas, moderate_areas, good_areas = self.analyze_quiz_results()
        plan_start_date = date.today()
        plan = []

        # Critical areas (High priority)
        for i, topic in enumerate(critical_areas):
            plan.append({
                'date': plan_start_date + timedelta(days=i * 2),
                'priority': 'High priority',
                'topic': topic,
                'materials': self.recommend_materials(topic)
            })

        # Moderate areas (Medium priority)
        offset = len(critical_areas)
        for i, topic in enumerate(moderate_areas, start=offset):
            plan.append({
                'date': plan_start_date + timedelta(days=i * 2),
                'priority': 'Medium priority',
                'topic': topic,
                'materials': self.recommend_materials(topic)
            })

        # Good areas (Low priority)
        offset += len(moderate_areas)
        for i, topic in enumerate(good_areas, start=offset):
            plan.append({
                'date': plan_start_date + timedelta(days=i * 2),
                'priority': 'Low priority',
                'topic': topic,
                'materials': self.recommend_materials(topic)
            })

        self.learning_plan = plan
        return plan

    def recommend_materials(self, topic, retriever=None):
        """
        Retrieve recommended materials for a given topic using LLM and optional RAG context.
        The response should prioritize materials in the user's language,
        but can include English resources as fallback.
        """
        retriever = retriever or self.retriever
        if retriever is None:
            retriever = RAGService().get_retriever()

        ctx = get_context_or_empty(topic, retriever)
        if ctx:
            ctx += "\n\n"

        prompt = (
            f"{ctx}"  # prepend context if available
            f"You are an AI assistant tasked with recommending study materials.\n"
            f"Provide a concise, high-quality list of recommended books, articles, or resources to help someone learn about '{topic}'.\n"
            f"Respond only in {self.user_language}. If resources in this language are limited, you may include a few English ones."
        )
        try:
            response = self.llm.invoke(prompt)
            materials = [m for m in response.content.split("\n") if m]
            return materials
        except Exception as e:
            print(f"Error while generating materials for topic '{topic}': {e}")
            return ["No materials available"]


    def generate_plan_from_prompt(self, user_input):
        """
        Generate a learning plan based on user's custom input.
        """
        plan_start_date = date.today()
        plan = []

        goals = user_input.get("goals", [])
        for i, goal in enumerate(goals):
            plan.append({
                'date': plan_start_date + timedelta(days=i * 2),
                'priority': 'User-defined',
                'topic': goal,
                'materials': self.recommend_materials(goal)
            })

        self.learning_plan = plan
        return plan

    def display_plan(self):
        """
        Display the generated learning plan.
        """
        print(f"Learning Plan for {self.user_name}:\n")
        for entry in self.learning_plan:
            print(f"Date: {entry['date']}")
            print(f"Topic: {entry['topic']}")
            print(f"Priority: {entry['priority']}")
            print("Recommended Materials:")
            for material in entry['materials']:
                print(f" - {material}")
            print("\n")

    def save_to_file(self, base_dir="data/learning_plans/"):
        """
        Save the generated learning plan to a JSON file with timestamp and user name.
        """
        os.makedirs(base_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.user_name}_plan_{timestamp}.json"
        path = os.path.join(base_dir, filename)

        try:
            plan_serializable = [
                {
                    **entry,
                    "date": entry["date"].isoformat()
                }
                for entry in self.learning_plan
            ]

            with open(path, "w", encoding="utf-8") as f:
                json.dump(plan_serializable, f, indent=4, ensure_ascii=False)

            print(f"✅ Plan saved to {path}")
        except Exception as e:
            print(f"❌ Error saving plan: {e}")
