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
    """rag_search"""
    try:
        retriever = RAGService().get_retriever()
        return get_context_or_empty(query, retriever)
    except Exception as e:  
        return f"RAG search error: {e}"

DEFAULT_PROMPT = PromptTemplate.from_template(
"""Answer the following questions as best you can. You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
Thought: I now know the final answer
Final Answer: the final answer to the original input question

IMPORTANT GUIDELINES:
1. For simple greetings, directly give Final Answer without using tools
2. When users ask about "PDF", "document", "file", "材料", "文档", or "这个PDF" content, use rag_search tool
3. If the answer is ALREADY in the provided context (from rag_search results), directly give Final Answer - DO NOT try to use tools again
4. NEVER create fake tool names like "无需调用工具" - either use a real tool or give Final Answer directly

Example 1:
Question: hello
Thought: This is a simple greeting, I don't need to use any tools
Final Answer: Hello! How can I assist you today?

Example 2:
Question: 这门课建议学习时长
Context: ...本教材的教学大约需要 60 学时，其中方法教学与上机实践的比例一般不应少于 1:1...
Thought: The answer is already in the provided context - it says the course needs about 60 hours
Final Answer: 根据教材，完成本教材的教学大约需要60学时，其中方法教学与上机实践的比例一般不应少于1:1。

Example 3:
Question: 这个PDF的内容是什么？
Thought: The user is asking about PDF content, I should use rag_search to find relevant information
Action: rag_search
Action Input: PDF内容
Observation: [Retrieved content from PDF]
Thought: I now have the content from the PDF
Final Answer: 根据文档内容，[summarize the content]

Example 4:
Question: What is the capital of France?
Thought: I should search for information about France's capital
Action: wikipedia_search
Action Input: capital of France
Observation: Paris is the capital of France
Thought: I now know the final answer
Final Answer: The capital of France is Paris.

Always answer in {language}. If any tool returns text in a different language, translate it to {language} before giving the final answer.

Begin!

Question: {input}
Thought:{agent_scratchpad}"""
)


def create_agent() -> AgentExecutor:
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
    # 🔥 修复：限制max_iterations为3，避免不必要的重复
    return AgentExecutor(
        agent=agent, 
        tools=tools, 
        verbose=True,
        max_iterations=3,  # 最多3次迭代
        handle_parsing_errors=True,
        early_stopping_method="force"
    )


def run_agent(
    question: str,
    executor: AgentExecutor | None = None,
    retriever=None,
    return_details: bool = False,
) -> str | tuple[str, bool, bool]:
    executor = executor or create_agent()    
    
    logger = logging.getLogger(__name__)
    
    print("\n" + "="*80)
    print("🤔 用户问题:")
    print(f"   {question}")
    logger.info(f"User Question: {question}")

    used_retriever = False
    if retriever:
        context = get_context_or_empty(question, retriever)
        if context:
            # 🔥 增强日志：输出检索到的上下文
            print(f"\n📚 从RAG检索到的上下文 (长度: {len(context)} 字符):")
            print(f"   {context[:200]}..." if len(context) > 200 else f"   {context}")
            logger.info(f"Retrieved context (length: {len(context)}): {context[:500]}")
            
            question = f"{question}\n\nContext:\n{context}"
            used_retriever = True
        else:
            print("\n⚠️  RAG检索未找到相关上下文")
            logger.info("No relevant context found from RAG")

    lang = LanguageHandler.choose_or_detect(question)
    print(f"\n🌐 检测到的语言: {lang}")
    logger.info(f"Detected language: {lang}")
    
    try:
        print("\n🤖 Agent正在处理...")
        print("-" * 80)
        logger.info("Agent processing started")
        
        result = executor.invoke({"input": question, "language": lang})
        
        output = result["output"]
        print("-" * 80)
        print("✅ Agent回答:")
        print(f"   {output}")
        logger.info(f"Agent output: {output}")
    except Exception as e:  # pragma: no cover - agent execution errors
        output = f"Agent error: {e}"
        print(f"\n❌ Agent错误: {e}")
        logger.error(f"Agent error: {e}")

    used_fallback = False

    def _needs_fallback(text: str) -> bool:
        text_stripped = text.strip()
        
        if not text_stripped:
            return True
        
        error_markers = [
            "agent error",
            "agent stopped",
            "i don't know",
            "i cannot",
            "i'm unable",
            "agent 错误",
            "代理错误",
            "我不知道",
            "我无法",
            "抱歉，我无法",
            "抱歉，我不",
        ]
        text_lower = text_stripped.lower()
        return any(m in text_lower for m in error_markers)

    if _needs_fallback(output):
        print("\n⚠️  检测到需要fallback，直接调用LLM...")
        logger.info("Fallback triggered, calling LLM directly")
        
        llm = ChatOpenAI(model=model_name, temperature=0,base_url=base_url,api_key=api_key)
        try:
            msg = llm.invoke(question)
            output = getattr(msg, "content", str(msg))
            print(f"✅ Fallback LLM回答: {output}")
            logger.info(f"Fallback LLM output: {output}")
        except Exception as e: 
            output = f"LLM error: {e}"
            print(f"❌ Fallback LLM错误: {e}")
            logger.error(f"Fallback LLM error: {e}")
        finally:
            used_fallback = True

    output = LanguageHandler.ensure_language(output, lang)
    print("="*80 + "\n")
    
    if return_details:
        return output, used_fallback, used_retriever
    return output
