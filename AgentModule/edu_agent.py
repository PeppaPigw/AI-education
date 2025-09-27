from langchain.agents import AgentExecutor, create_react_agent
import logging

from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain.tools import tool
from tools.language_handler import LanguageHandler
from tools.rag_service import RAGService
from tools.rag_utils import get_context_or_empty
from tools.edu_tools import (
    # wikipedia_search,
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
    """rag_search"""
    try:
        retriever = RAGService().get_retriever()
        return get_context_or_empty(query, retriever)
    except Exception as e:  # pragma: no cover - retrieval errors
        return f"RAG search error: {e}"

DEFAULT_PROMPT = PromptTemplate.from_template(
"""
使用提供的工具尽可能地回答以下问题。

您可以使用以下工具：

{tools}

使用 rag_search 查询文档数据库以获取其他上下文。

使用以下格式：
Question: {input}
Thought: 你应该思考要做什么
Action: 要采取的行动，应该是 {tool_names} 中的一个
Action Input: 行动的输入
Observation: 行动的结果
... (这个 Thought/Action/Action Input/Observation 循环可以重复 N 次)
Thought: 我现在知道最终答案了
Final Answer: 对原始问题的最终答案

始终使用 {language} 回答。如果任何工具返回不同语言的文本，请将其翻译成 {language} 后再给出最终答案。

{agent_scratchpad}
"""
)


def create_agent() -> AgentExecutor:
    tools = [
        # wikipedia_search,
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
        print("Question:    ",question)
        result = executor.invoke({"input": question, "language": lang})
        
        output = result["output"]
        print("Output:    ",output)
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
