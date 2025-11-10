import easyocr
import numpy as np
from PIL import Image
import io
from typing import Union


class OCRService:
    def __init__(self, languages=["ch_sim", "en"]):
        self.reader = easyocr.Reader(languages, gpu=False)

    def extract_text_from_image(self, image_data: Union[bytes, str, np.ndarray]) -> str:
        try:
            if isinstance(image_data, bytes):
                image = Image.open(io.BytesIO(image_data))
                image_array = np.array(image)
            elif isinstance(image_data, str):
                image = Image.open(image_data)
                image_array = np.array(image)
            else:
                image_array = image_data

            results = self.reader.readtext(image_array)

            text_lines = [result[1] for result in results]
            extracted_text = "\n".join(text_lines)

            return extracted_text
        except Exception as e:
            raise Exception(f"OCR识别失败: {str(e)}")


_ocr_service = None


def get_ocr_service():
    """获取OCR服务单例"""
    global _ocr_service
    if _ocr_service is None:
        _ocr_service = OCRService()
    return _ocr_service
