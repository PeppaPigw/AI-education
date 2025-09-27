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
        retriever = retriever or self.retriever
        if retriever is None:
            retriever = RAGService().get_retriever()

        ctx = get_context_or_empty(topic, retriever)
        if ctx:
            ctx += "\n\n"

        prompt = (
            f"{ctx}"  # prepend context if available
            f"你是一个人工智能助手，负责推荐学习材料。\n"
            f"提供一个简明的、高质量的推荐书籍、文章或资源列表，以帮助人们学习'{topic}'.\n"
            f"Respond only in {self.user_language}. 如果这种语言的资源有限，您可以包括一些英语资源。"
        )
        try:
            response = self.llm.invoke(prompt)
            materials = [m for m in response.content.split("\n") if m]
            return materials
        except Exception as e:
            print(f"Error while generating materials for topic '{topic}': {e}")
            return ["No materials available"]


    def generate_plan_from_prompt(self, user_input):
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
