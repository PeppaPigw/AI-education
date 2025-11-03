from __future__ import annotations

import io
from pathlib import Path
from typing import List

import easyocr
import fitz
from PIL import Image
from langchain_core.documents import Document


class PDFOCRLoader:

    def __init__(self, file_path: str, languages: List[str] = None, gpu: bool = False):
        self.file_path = file_path
        self.languages = languages or ["ch_sim", "en"]
        self.gpu = gpu
        self._reader = None

    @property
    def reader(self):
        if self._reader is None:
            self._reader = easyocr.Reader(self.languages, gpu=self.gpu)
        return self._reader

    def _extract_text_from_image(self, image: Image.Image) -> str:
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format="PNG")
        img_byte_arr = img_byte_arr.getvalue()

        result = self.reader.readtext(img_byte_arr, detail=0)
        return "\n".join(result)

    def load(self) -> List[Document]:
        documents = []

        doc = fitz.open(self.file_path)

        for page_num in range(len(doc)):
            page = doc[page_num]

            text = page.get_text()

            if len(text.strip()) < 50:

                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                img_data = pix.tobytes("png")
                image = Image.open(io.BytesIO(img_data))

                text = self._extract_text_from_image(image)

            if text.strip():
                metadata = {
                    "source": str(self.file_path),
                    "page": page_num + 1,
                }
                documents.append(Document(page_content=text, metadata=metadata))

        doc.close()
        return documents
