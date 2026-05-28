import base64
import json
import logging
from pathlib import Path
import requests

logger = logging.getLogger(__name__)


class OllamaClient:
    """
    Unified client for communicating with the local Ollama service.
    Handles chat requests, model listings, vision capability detection, and routing.
    """

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self._cached_vision_models = []

    def chat(self, model: str, messages: list[dict], images: list[Path] = None) -> str:
        """
        Sends a chat request to Ollama's /api/chat endpoint.
        If images are provided, they are base64-encoded and attached to the last message.
        """
        payload_messages = [msg.copy() for msg in messages]

        # Process and attach images to the last message if they exist
        if images and payload_messages:
            b64_images = []
            for img_path in images:
                try:
                    p = Path(img_path)
                    if p.is_file():
                        img_data = p.read_bytes()
                        b64_str = base64.b64encode(img_data).decode("utf-8")
                        b64_images.append(b64_str)
                    else:
                        logger.warning("Image file not found: %s", img_path)
                except Exception as e:
                    logger.error("Failed to encode image %s: %s", img_path, e)

            if b64_images:
                # Add images to the last user message
                last_msg = payload_messages[-1]
                last_msg["images"] = b64_images

        try:
            logger.info("Sending chat request to Ollama (model: %s)", model)
            resp = requests.post(
                f"{self.base_url}/api/chat",
                json={"model": model, "messages": payload_messages, "stream": False},
                timeout=120,
            )
            resp.raise_for_status()
            return resp.json()["message"]["content"]
        except Exception as e:
            logger.error("Ollama chat request failed: %s", e)
            raise e

    def get_installed_models(self) -> list[str]:
        """Queries /api/tags and returns a list of installed model names."""
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=10)
            resp.raise_for_status()
            models_data = resp.json().get("models", [])
            return [m["name"] for m in models_data]
        except Exception as e:
            logger.error("Failed to get installed models from Ollama: %s", e)
            return []

    def check_model_vision_support(self, model_name: str) -> bool:
        """Queries /api/show to check if a model has vision capabilities (clip/projector family)."""
        # Hardcoded heuristic checks first to avoid redundant API overhead
        name_lower = model_name.lower()
        if any(w in name_lower for w in ["llava", "bakllava", "vision", "minicpm-v", "phi3:vision"]):
            return True

        try:
            resp = requests.post(
                f"{self.base_url}/api/show",
                json={"name": model_name},
                timeout=10,
            )
            if resp.status_code == 200:
                details = resp.json().get("details", {})
                families = details.get("families", [])
                # Fallback to single family if families is empty/null
                if not families and details.get("family"):
                    families = [details["family"]]
                
                # Check for clip or projector architectures (Ollama's multimodal tags)
                has_vision = any(f.lower() in ["clip", "projector"] for f in families)
                if has_vision:
                    logger.info("Detected vision support in model: %s", model_name)
                return has_vision
        except Exception as e:
            logger.debug("Failed to query model details for %s: %s", model_name, e)
        
        return False

    def find_first_vision_model(self) -> str | None:
        """
        Scans local models and returns the name of the first vision-capable model.
        Caches the result to avoid querying Ollama repeatedly.
        """
        try:
            installed = self.get_installed_models()
        except Exception as e:
            logger.error("Failed to fetch installed models for vision detection: %s", e)
            return None

        # Verify cached vision models are still installed
        if self._cached_vision_models:
            valid_cached = [m for m in self._cached_vision_models if m in installed]
            if valid_cached:
                return valid_cached[0]
            self._cached_vision_models.clear()

        # Check installed models
        for model in installed:
            if self.check_model_vision_support(model):
                self._cached_vision_models.append(model)
                return model

        return None
