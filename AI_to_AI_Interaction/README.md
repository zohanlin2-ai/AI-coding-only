# 🌌 AI-to-AI Dialogue Observer

An interactive web application built with Python and Streamlit. Users can configure 1 to 4 AI characters with customized personalities, voices, and dialogue topics, and observe their conversation and inner thoughts in real-time.

## 🌟 Core Features
1. **Flexible Number of Agents**: Supports 1 to 4 AI agents conversing simultaneously. This can range from a single agent's self-reflection to a multi-agent debate.
2. **Custom Topics & Personalities**: Fully customize dialogue topics and specify individual agent names and roles (e.g., "Extremely Pessimistic Doomsday Prophet", "Cool & Rational Economist").
3. **Random Preset Fill**: If topic or role fields are left blank, the system automatically pulls from a curated preset library. Supports one-click randomization of all fields.
4. **Multi-Model Integration**: Integrated with standard model APIs:
   - **Google Gemini** (default `gemini-2.5-flash`)
   - **OpenAI** (default `gpt-4o-mini`)
   - **Anthropic Claude** (default `claude-3-5-sonnet`)
   - **DeepSeek** (default `deepseek-chat`)
   - **xAI Grok** (default `grok-2-1212`)
   - **Groq Cloud** (default `gemma2-9b-it`)
   - **GitHub Models** (default `gpt-4o-mini`)
   - **Ollama Local AI** (default `gemma4:latest`, custom URL supported, optimized for reasoning models)
   - **Mock Mode**: Fully offline. Combines random templates to simulate dialogue for testing and debugging.
5. **Dialogue Controls**: Set total duration (1 to 120 minutes) and pacing delay (1 to 15 seconds), complete with real-time countdown progress indicators and a manual stop button.
6. **Three Turn-Taking Modes**:
   - **Sequential**: Agents speak in sequence.
   - **Nomination**: Agents can nominate the next speaker using `@Agent` in their speech.
   - **Orchestrator**: A designated LLM acts as coordinator, dynamically deciding the next speaker based on conversation context.
7. **Provider Attribution**: Every message bubble and exported transcript explicitly labels the AI provider (e.g., "via OpenAI", "via Ollama").
8. **Key Validation & Auto-Fallback**: Sidebar inputs validate keys synchronously. If a key fails validation, it is filtered from active options; selected agents automatically fall back to mock mode safely.
9. **Export Transcript**: One-click download of the entire dialogue history as a formatted Markdown file, documenting topics, agent personas, models, and attributed dialogue.

---

## 🛠️ Quick Start

### 1. Install Dependencies
Ensure Python 3.10+ is installed, then run:
```bash
pip install -r requirements.txt
```

### 2. Configure API Keys (Optional)
You can configure API keys in two ways:
- **Option A (UI Sidebar)**: Input keys directly in the sidebar on startup. Click "Verify Key" to run a live connection check (indicates: 🟢 Verified, 🟡 Configured (Unverified), 🔴 Not Configured, ❌ Verification Failed).
- **Option B (.env file)**: Create a `.env` file in the project root:
  ```env
  GEMINI_API_KEY=your_gemini_key_here
  OPENAI_API_KEY=your_openai_key_here
  CLAUDE_API_KEY=your_claude_key_here
  DEEPSEEK_API_KEY=your_deepseek_key_here
  XAI_API_KEY=your_grok_key_here
  GROQ_API_KEY=your_groq_key_here
  GITHUB_TOKEN=your_github_token_here
  OLLAMA_BASE_URL=http://localhost:11434
  ```

### 3. Launch the Application
Run the Streamlit application:
```bash
streamlit run app.py
```
The interface will automatically open in your browser (defaulting to `http://localhost:8501`).

---

## 🧪 Running Unit Tests
This project includes a comprehensive unit test suite (based on Python's `unittest`) to validate the Mock generator, preset randomized completions, nomination regex, turn orchestration, API call mocks, and export schemas.

Run tests in the root folder:
```bash
python -m unittest test_app.py
```

---

## 📂 Project Structure
- [app.py](app.py): Main Streamlit web entrypoint and runtime loop.
- [ai_agent.py](ai_agent.py): AI agent wrapper, API requests, and mock engine.
- [orchestrator.py](orchestrator.py): Nomination parser and turn-taking orchestration.
- [test_app.py](test_app.py): Automated unit tests.
- [CLAUDE.md](CLAUDE.md): Developer guidelines and commands.
- [requirements.txt](requirements.txt): Python dependency list.
- [uml.html](uml.html): UML system Sequence and Activity diagrams with interactive Mermaid rendering and high-resolution export tools.
