from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
import logging
from tools.language_handler import LanguageHandler
from tools.rag_service import RAGService
from tools.rag_utils import get_context_or_empty
from tools.llm_logger import get_llm_logger

logger = logging.getLogger(__name__)

from dotenv import load_dotenv
import os

load_dotenv()
model_name = os.environ.get("model_name")
base_url = os.environ.get("base_url")
api_key = os.environ.get("api_key")


class StudySummaryGenerator:

    def __init__(self, temperature=0.5, retriever=None):
        self.llm = ChatOpenAI(
            model=model_name, temperature=0, base_url=base_url, api_key=api_key
        )
        if retriever is None:
            retriever = RAGService().get_retriever()
        self.retriever = retriever  # optional document retriever

        self.base_prompt = PromptTemplate.from_template(
            """
你是一位专业的大学讲师，帮助学生准备一场困难的考试。

你的任务是为以下主题创建一个详细的、结构良好的学习指南：
"{input}"

这不是小抄。相反，它应该是一个多节，丰富的总结，可以跨越多个页面。


包括:
- 核心术语的定义清晰准确
- 对主要概念的详细解释
- 包含概念的示例
- 定理和定律，解释和用法
- 关键的公式和符号，写得清楚，符合上下文
- 有助于解释如何应用知识的代表性示例
- 项目符号列表或粗体文本突出显示最重要的内容
- 上下文用法：在实际任务/测试中应用这些知识的位置/原因
- 有用的地方：图表，公式，逻辑步骤

风格:
- 使用类似标记的格式（标题、项目符号、代码块）
- 明确分段分隔
- 友好和略带解释性的语气（像一个好的导师）

IMPORTANT:
- 写得足够长，就像准备学生通过考试一样
- 避免对话式的语气。应该是结构化的内容

只输出内容。没有介绍或评论。

Respond in {language}.
"""
        )

    def generate_summary(
        self, input_text: str, language: str = "en", retriever=None
    ) -> tuple[str, bool]:
        lang = (
            LanguageHandler.choose_or_detect(input_text)
            if language == "auto"
            else language
        )

        retriever = retriever or self.retriever
        if retriever is None:
            retriever = RAGService().get_retriever()

        ctx = get_context_or_empty(input_text, retriever)
        used_retriever = bool(ctx)
        if ctx:
            input_text = f"{ctx}\n\n### 主题:\n{input_text}"
        logger.info("总结基于RAG生成: %s", used_retriever)

        chain = self.base_prompt | self.llm
        response = chain.invoke({"input": input_text, "language": lang})
        
        llm_logger = get_llm_logger()
        llm_logger.log_llm_call(
            messages=[{"role": "user", "content": f"Generate summary for: {input_text[:200]}..."}],
            response=response,
            model=model_name,
            module="SummaryModule.summary_generator",
            metadata={"function": "generate_summary", "language": lang, "used_retriever": used_retriever}
        )
        
        return response.content, used_retriever
