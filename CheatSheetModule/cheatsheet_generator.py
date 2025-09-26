from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
import logging
from tools.rag_service import RAGService
from tools.rag_utils import get_context_or_empty

logger = logging.getLogger(__name__)
from dotenv import load_dotenv
import os
load_dotenv()
model_name=os.environ.get("model_name")
base_url=os.environ.get("base_url")
api_key=os.environ.get("api_key")
# TODO: test and optimize

class CheatSheetGenerator:
    """
    Generates concise exam-style cheat sheets with only the most critical facts, formulas, and definitions.
    Ideal for rapid last-minute review. Use the Pareto principle.
    """
    def __init__(self, model_name, temperature=0.3, retriever=None):
        self.llm = ChatOpenAI(model=model_name, temperature=0,base_url=base_url,api_key=api_key)
        if retriever is None:
            retriever = RAGService().get_retriever()
        self.retriever = retriever  # optional document retriever

        # Based on the RStudio cheatsheet guidelines which suggest designing
        # materials in a clear three or four column layout for readability
        # (see https://github.com/rstudio/cheatsheets/blob/main/.github/CONTRIBUTING.md)
        self.prompt = PromptTemplate.from_template(
            """
{context}
You are an assistant that generates compact, exam-focused cheat sheets.

Create a concise **one page** cheat sheet for the topic:
"{input}"

Structure the sheet using these sections:
### Key Terms
- short bullet points (max ~12 words)

### Must-Know Formulas
- clear formulas or equations only

### Quick Facts
- bite-size facts useful for revision

Guidelines:
- Keep bullet lists extremely concise
- Use markdown headers and bullet lists
- Avoid long paragraphs, examples or commentary
- No images – text only for accessibility

Respond only in {language}.
"""
        )

    def generate_cheatsheet(
        self,
        input_text: str,
        language: str = "en",
        retriever=None
    ) -> tuple[str, bool]:
        """
        Generate a cheat sheet with optional retrieved context.

        Args:
            input_text: topic or material for which to generate the cheat sheet
            language: language code for the output
            retriever: optional external retriever to supply context

        Returns:
            Generated cheat sheet as string.
        """
        retriever = retriever or self.retriever
        if retriever is None:
            retriever = RAGService().get_retriever()

        ctx = get_context_or_empty(input_text, retriever)
        used_retriever = bool(ctx)
        logger.info("Cheat sheet generation used RAG: %s", used_retriever)

        response = (self.prompt | self.llm).invoke(
            {"input": input_text, "language": language, "context": ctx}
        )
        return response.content, used_retriever
