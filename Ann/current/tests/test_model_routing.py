"""
Unit tests for the AI Engine (OllamaClient capability detection & dynamic routing).
"""
import base64
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

# Ensure path is set up to import current/ modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from ollama_client import OllamaClient


@pytest.fixture
def mock_client():
    return OllamaClient("http://localhost:11434")


def test_heuristic_vision_check(mock_client):
    # Test that model names containing known vision keywords return True directly
    assert mock_client.check_model_vision_support("llava:latest") is True
    assert mock_client.check_model_vision_support("minicpm-v:latest") is True
    assert mock_client.check_model_vision_support("phi3:vision") is True
    
    # Text-only model should fall through to API check
    with patch("requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "details": {
                "families": ["llama"]
            }
        }
        mock_post.return_value = mock_resp
        
        assert mock_client.check_model_vision_support("gemma4:e4b") is False


def test_api_vision_check_positive(mock_client):
    with patch("requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "details": {
                "families": ["llama", "clip"]
            }
        }
        mock_post.return_value = mock_resp
        
        assert mock_client.check_model_vision_support("custom-eye-model") is True
        mock_post.assert_called_once_with(
            "http://localhost:11434/api/show",
            json={"name": "custom-eye-model"},
            timeout=10
        )


def test_find_first_vision_model(mock_client):
    installed_models = ["gemma4:e4b", "llava:latest", "llama3:latest"]
    
    def mock_post_impl(url, json, timeout):
        name = json["name"]
        resp = MagicMock()
        resp.status_code = 200
        if "llava" in name:
            resp.json.return_value = {"details": {"families": ["llama", "clip"]}}
        else:
            resp.json.return_value = {"details": {"families": ["llama"]}}
        return resp

    with patch.object(mock_client, "get_installed_models", return_value=installed_models), \
         patch("requests.post", side_effect=mock_post_impl):
        
        first_vision = mock_client.find_first_vision_model()
        assert first_vision == "llava:latest"
        
        # Test caching: calling again should not re-query
        with patch.object(mock_client, "get_installed_models") as mock_get_tags:
            # But wait, find_first_vision_model verifies if the model is still installed, so it calls get_installed_models
            mock_get_tags.return_value = installed_models
            assert mock_client.find_first_vision_model() == "llava:latest"
            mock_get_tags.assert_called_once()


def test_resolve_model_preferred_available(mock_client):
    # Preferred model is installed → it is used as-is.
    with patch.object(mock_client, "get_installed_models",
                      return_value=["gemma4:e4b", "llama3:latest"]):
        assert mock_client.resolve_model("gemma4:e4b") == "gemma4:e4b"


def test_resolve_model_falls_back_to_first(mock_client):
    # Preferred not installed → fall back to the first available model.
    with patch.object(mock_client, "get_installed_models",
                      return_value=["llama3:latest", "qwen2:latest"]):
        assert mock_client.resolve_model("gemma4:e4b") == "llama3:latest"


def test_resolve_model_none_available(mock_client):
    # No models at all (Ollama down or empty) → None signals LLM-free mode.
    with patch.object(mock_client, "get_installed_models", return_value=[]):
        assert mock_client.resolve_model("gemma4:e4b") is None


def test_chat_payload_image_encoding(mock_client, tmp_path):
    # Create a dummy image file
    img_file = tmp_path / "dummy.png"
    img_data = b"fake_png_data"
    img_file.write_bytes(img_data)
    
    expected_b64 = base64.b64encode(img_data).decode("utf-8")
    
    messages = [
        {"role": "user", "content": "What is in this image?"}
    ]
    
    with patch("requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "message": {
                "content": "An image with dummy content."
            }
        }
        mock_post.return_value = mock_resp
        
        reply = mock_client.chat("llava:latest", messages, images=[img_file])
        
        assert reply == "An image with dummy content."
        
        # Verify post payload contains base64 encoded images list in the last message
        called_args, called_kwargs = mock_post.call_args
        json_payload = called_kwargs["json"]
        
        last_msg = json_payload["messages"][-1]
        assert "images" in last_msg
        assert last_msg["images"] == [expected_b64]
        assert json_payload["model"] == "llava:latest"
