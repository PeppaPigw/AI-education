import os
import shutil
import subprocess
import logging
import json
import gradio as gr

logger = logging.getLogger(__name__)


def convert_to_pdf(input_path: str, output_dir: str) -> str | None:
    try:
        command = [
            "soffice",
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            output_dir,
            input_path,
        ]

        logger.info(f"🚀 开始转换文件: {os.path.basename(input_path)}")

        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=120,
            check=True,
        )

        filename_without_ext = os.path.splitext(os.path.basename(input_path))[0]
        pdf_path = os.path.join(output_dir, f"{filename_without_ext}.pdf")

        if os.path.exists(pdf_path):
            logger.info(f"✅ 文件转换成功: {pdf_path}")
            return pdf_path
        else:
            logger.error(
                f"❌ 转换失败，未找到输出文件。Stderr: {result.stderr.decode('utf-8', 'ignore')}"
            )
            return None

    except FileNotFoundError:
        logger.error(
            "❌ 命令执行失败：'soffice' 命令未找到。请确保 LibreOffice 已安装并已添加到系统 PATH 环境变量中。"
        )

        raise
    except subprocess.CalledProcessError as e:
        error_message = e.stderr.decode("utf-8", "ignore")
        logger.error(f"❌ 文件转换时发生错误: {error_message}")
        return None
    except Exception as e:
        logger.error(f"❌ 发生未知错误在转换过程中: {e}")
        return None
