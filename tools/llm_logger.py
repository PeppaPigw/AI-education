import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path
import threading


class LLMLogger:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.log_file = Path("data/Log/llm_log.json")
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.log_file.exists():
            self.log_file.write_text("[]", encoding="utf-8")
        self._initialized = True

    def log_llm_call(
        self,
        messages: List[Dict[str, str]],
        response: Any,
        model: str,
        module: str,
        metadata: Optional[Dict] = None,
    ):
        """Log LLM call with full details"""
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "module": module,
                "metadata": metadata or {},
                "request": {"model": model, "messages": messages},
                "response": self._extract_response_data(response),
            }

            with self._lock:
                logs = self._read_logs()
                logs.append(log_entry)
                self._write_logs(logs)

        except Exception as e:
            print(f"Failed to log LLM call: {e}")

    def _extract_response_data(self, response: Any) -> Dict:
        """Extract response data in the format similar to API response"""
        try:
            if hasattr(response, "response_metadata"):
                metadata = response.response_metadata
                return {
                    "id": metadata.get("id", ""),
                    "object": metadata.get("object", "chat.completion"),
                    "created": metadata.get("created", int(datetime.now().timestamp())),
                    "model": metadata.get("model", ""),
                    "choices": [
                        {
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": getattr(response, "content", str(response)),
                            },
                            "finish_reason": metadata.get("finish_reason", "stop"),
                        }
                    ],
                    "usage": {
                        "prompt_tokens": metadata.get("token_usage", {}).get(
                            "prompt_tokens", 0
                        ),
                        "completion_tokens": metadata.get("token_usage", {}).get(
                            "completion_tokens", 0
                        ),
                        "total_tokens": metadata.get("token_usage", {}).get(
                            "total_tokens", 0
                        ),
                    },
                    "system_fingerprint": metadata.get("system_fingerprint", ""),
                }
            else:
                return {
                    "id": "",
                    "object": "chat.completion",
                    "created": int(datetime.now().timestamp()),
                    "model": "",
                    "choices": [
                        {
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": getattr(response, "content", str(response)),
                            },
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "total_tokens": 0,
                    },
                    "system_fingerprint": "",
                }
        except Exception as e:
            print(f"Failed to extract response data: {e}")
            return {
                "error": str(e),
                "content": str(response),
            }

    def _read_logs(self) -> List[Dict]:
        """Read existing logs"""
        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _write_logs(self, logs: List[Dict]):
        """Write logs to file"""
        try:
            with open(self.log_file, "w", encoding="utf-8") as f:
                json.dump(logs, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Failed to write logs: {e}")


def get_llm_logger() -> LLMLogger:
    """Get singleton LLMLogger instance"""
    return LLMLogger()
