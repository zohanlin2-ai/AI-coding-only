# modules/m2_agent/llm_client.py
"""
llm_client.py — Ollama HTTP API 呼叫封裝
"""

import sys
import json
import os
from pathlib import Path
import requests

# 確保可以 import shared/schemas.py
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared.schemas import Config


def load_config() -> Config:
    """
    讀取 AI_World/config.json，返回 Config 物件。
    """
    config_path = PROJECT_ROOT / "config.json"
    if not config_path.exists():
        raise FileNotFoundError("找不到 config.json，請先執行 M0 Setup 模組。")
    with open(config_path, "r", encoding="utf-8") as f:
        return Config(**json.load(f))


def call_ollama(prompt: str, config: Config) -> str:
    """
    呼叫 Ollama /api/generate endpoint，返回 LLM 生成的文字。
    """
    url = f"{config.ollama_base_url}/api/generate"
    payload = {
        "model": config.ollama_model,
        "prompt": prompt,
        "stream": False
    }

    try:
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        res_text = data.get("response", "").strip()
        if not res_text:
            raise ValueError("Ollama 回傳了空回應。")
        return res_text
    except requests.exceptions.ConnectionError:
        raise ConnectionError(f"無法連線至 Ollama 服務 ({url})，請確認 `ollama serve` 正在背景運行。")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"呼叫 Ollama API 失敗 (HTTP 狀態碼或連線異常): {e}")
