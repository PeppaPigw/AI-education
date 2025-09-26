from langchain.agents import AgentExecutor, create_react_agent
import logging

from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain.tools import tool
from tools.language_handler import LanguageHandler
from tools.rag_service import RAGService
from tools.rag_utils import get_context_or_empty
from tools.edu_tools import (
    wikipedia_search,
    define_word,
    calculator,
    current_date,
    current_weekday,
    detect_language,
)
from dotenv import load_dotenv
import os
load_dotenv()
model_name=os.environ.get("model_name")
base_url=os.environ.get("base_url")
api_key=os.environ.get("api_key")

@tool
def rag_search(query: str) -> str:
    """Retrieve relevant document chunks using the RAG service."""
    try:
        retriever = RAGService().get_retriever()
        return get_context_or_empty(query, retriever)
    except Exception as e:  # pragma: no cover - retrieval errors
        return f"RAG search error: {e}"

DEFAULT_PROMPT = PromptTemplate.from_template(
    """
Answer the following question as best as you can using the provided tools.
You have access to the following tools:

{tools}

Use rag_search to query the document database for additional context.

Use the following format:
Question: {input}
Thought: you should think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original question

Always respond in {language}. If any tool returns text in a different language,
translate it to {language} before giving the final answer.

{agent_scratchpad}"""
)


def create_agent() -> AgentExecutor:
    """Create an agent executor with default tools."""
    tools = [
        wikipedia_search,
        define_word,
        calculator,
        current_date,
        current_weekday,
        detect_language,
        rag_search,
    ]
    
  
    llm = ChatOpenAI(model=model_name, temperature=0,base_url=base_url,api_key=api_key)
    agent = create_react_agent(llm, tools, DEFAULT_PROMPT)
    return AgentExecutor(agent=agent, tools=tools, verbose=True)


def run_agent(
    question: str,
    executor: AgentExecutor | None = None,
    retriever=None,
    return_details: bool = False,
) -> str | tuple[str, bool, bool]:
    """Run the default agent on a question and return the answer.

    If a ``retriever`` is supplied, relevant documents are fetched and appended
    to the question as context before execution. If the agent cannot provide a
    useful response (e.g. tool errors), the question is answered directly by
    the LLM as a fallback.

    Set ``return_details=True`` to also return whether the LLM fallback was
    used and whether document context was retrieved.
    """
    executor = executor or create_agent()    

    used_retriever = False
    if retriever:
        context = get_context_or_empty(question, retriever)
        if context:
            question = f"{question}\n\nContext:\n{context}"
            used_retriever = True
            logging.getLogger(__name__).info("Retrieved context for query")

    lang = LanguageHandler.choose_or_detect(question)
    try:
        result = executor.invoke({"input": question, "language": lang})
        output = result["output"]
    except Exception as e:  # pragma: no cover - agent execution errors
        output = f"Agent error: {e}"

    used_fallback = False

    def _needs_fallback(text: str) -> bool:
        markers = [
            "error",
            "not found",
            "couldn't",
            "could not",
            "unable to",
            "sorry",
            "unfortunately",
            "niestety",
            "nie uda",
            "nie mog",
            "brak",
        ]
        text = text.lower()
        return any(m in text for m in markers)

    if _needs_fallback(output):
        llm = ChatOpenAI(model=model_name, temperature=0,base_url=base_url,api_key=api_key)
        try:
            msg = llm.invoke(question)
            output = getattr(msg, "content", str(msg))
        except Exception as e:  # pragma: no cover - API errors
            output = f"LLM error: {e}"
        finally:
            used_fallback = True

    output = LanguageHandler.ensure_language(output, lang)
    if return_details:
        return output, used_fallback, used_retriever
    return output
