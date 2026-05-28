# AI Engine Module Specification

## 1. Purpose

This document defines the specification for the **AI Engine** module of the Ann AI assistant. 

The AI Engine acts as the central interface between the Ann application (CLI/GUI) and the underlying local language/multimodal models. It unifies all client communication, checks model metadata and capabilities (e.g., text-only vs. vision support), manages message histories, handles prompt formatting, and routes incoming tasks to the most suitable local models.

---

## 2. Scope

### 2.1 In Scope
- **AI Client Interface (`OllamaClient`)**:
  - Unified connection client interacting with Ollama's endpoints (`/api/chat`, `/api/tags`, `/api/show`).
  - Extensible design allowing future backend adapters (e.g. Llama.cpp, local SDKs, or secure remote endpoints).
- **Model Registry & Capability Detection**:
  - Query local registry to get installed models.
  - Automatically analyze model structures and layers (inspecting `families` or architectural details for `"clip"` or `"projector"`) to identify vision-capable models.
- **Multimodal Message Formatting**:
  - Automatically encode image files into base64 strings and structure the JSON request payload under the `"images"` list.
  - Inject text files and code attachments in properly tagged Markdown blocks inside the prompt.
- **Dynamic Task Routing**:
  - Match task inputs (text, image attachments, or specialized requests) with appropriate model configurations.
  - Switch models dynamically on a per-request basis (e.g., routing to `llava` for image queries and returning to `gemma4:e4b` for coding/text queries).
  - Handle exceptions gracefully, advising users to download models if a required capability is missing.

### 2.2 Out of Scope
- Direct download management of models from the Ollama library.
- Fine-tuning or local model weight modifications.

---

## 3. Architecture & Interface Design

### 3.1 Architecture Overview
```
           [User Input (Chat / Files)]
                       │
                       ▼
               [Assistant GUI/CLI]
                       │
                       ▼
                [AI Engine Core] 
          (Prompt building, History sync)
                       │
               [OllamaClient]
          (Capability Check & Routing)
         ┌─────────────┴─────────────┐
         ▼                           ▼
  [Text Model Tag]           [Vision Model Tag]
  (e.g., gemma4:e4b)          (e.g., llava:7b)
         │                           │
         └─────────────┬─────────────┘
                       ▼
             [Local Ollama Server]
```

### 3.2 Dynamic Model Selection Flow
1. **Initialize**: At startup, the AI Engine queries `/api/tags` and `/api/show` to cache which local models support text and which support vision.
2. **Evaluate Message**: When a message is sent:
   - If **images** are present:
     - Select the first cached model supporting the `"clip"` family.
     - Convert images to base64 and structure them in the API payload.
     - If no vision model is cached, fail gracefully with an action prompt to the user.
   - If **text-only**:
     - Route to the configured default model.

---

## 4. API Specification

### 4.1 Client Class (`OllamaClient`)

```python
class OllamaClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self._cached_vision_models = []

    def chat(self, model: str, messages: list[dict], images: list[str] = None) -> str:
        """Sends chat request, embedding base64 images into the last message if provided."""
        # ...

    def get_installed_models(self) -> list[str]:
        """Queries /api/tags and returns a list of installed model names."""
        # ...

    def check_model_vision_support(self, model_name: str) -> bool:
        """Queries /api/show to inspect if the model belongs to a vision family."""
        # ...

    def find_first_vision_model(self) -> str | None:
        """Scans local models and returns the first vision-capable model, or None."""
        # ...
```

---

## 5. Backward Compatibility

To maintain complete backward compatibility with CLI operations and intent parsing, the core client retains a legacy function mapping in `assistant.py`:
```python
def call_ollama(base_url: str, model: str, messages: list[dict]) -> str:
    from ollama_client import OllamaClient
    client = OllamaClient(base_url)
    return client.chat(model, messages)
```
This guarantees no breaking changes occur in non-GUI interfaces.
