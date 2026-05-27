# Ann: AI Assistant with Self-Updating Mechanism

Welcome to the **Ann** AI assistant project. Ann is a locally-hosted Python AI assistant featuring an automatic self-updating mechanism.

---

## 📌 Project Overview

This project adopts a **Launcher + Core (separated processes)** architecture to overcome the limitation that a Python process cannot overwrite its own running files. Version management and file delivery are handled entirely through the GitHub REST API, enabling painless updates and rollbacks.

---

## 🛠️ Development Language & Tech Stack

- **Core Language**: Python 3.10+
  - **Advantages**: The richest AI/LLM ecosystem (LangChain, Anthropic SDK, OpenAI SDK), easy dynamic module loading (`importlib`), simple subprocess and OS operations.
- **Test Framework**: `pytest`
- **Dependency Management**: `pip` + `virtualenv` / `venv`
- **Communication Protocol**: GitHub REST API (HTTPS)

### Language Comparison

| Language | Pros | Cons | Suitability |
| :--- | :--- | :--- | :---: |
| **Python** | Complete LLM ecosystem, hot-update friendly, rapid development | Slower execution speed | ⭐⭐⭐⭐⭐ (Recommended) |
| **Node.js** | Strong async performance, easy front-end integration | AI ecosystem less mature than Python | ⭐⭐⭐ |
| **Go** | Fast compilation, simple single-binary deployment | Complex dynamic module loading/updating logic | ⭐⭐ |
| **Rust** | Excellent performance and safety | Longer development cycle, weak AI ecosystem | ⭐ |

---

## 🏗️ Core Architecture: Launcher + Core Dual-Module

To solve the "cannot overwrite running code" local limitation, the project splits program logic into two components:

- **`launcher.py`** (Launcher): Always running, rarely updated. Responsible for starting and monitoring the `assistant.py` core, and executing test-and-swap for new versions.
- **`assistant.py`** (Ann Assistant Core): Handles all AI conversation and feature logic. Can be updated and restarted at any time.

```mermaid
graph TD
    Launcher[launcher.py <br><i>Persistent monitor & version management</i>]
    Assistant[current/assistant.py <br><i>Ann AI assistant core & user interaction</i>]
    Staging[staging/ <br><i>New version testing & environment prep</i>]
    Versions[versions/ <br><i>Historical version backups for rollback</i>]
    GitHub[GitHub API <br><i>Online Release / Tag detection</i>]

    Launcher -->|Start & restart monitoring| Assistant
    Assistant -->|Update detected, signal & exit| Launcher
    Launcher -->|1. Fetch file list| GitHub
    Launcher -->|2. Download files| Staging
    Launcher -->|3. Run pytest validation| Staging
    Staging -->|4. Tests pass: atomic swap| Assistant
    Launcher -.->|Tests fail: rollback| Versions
```
---

## ⚙️ Installation & Usage (安裝與使用)

### 1. Prerequisites (環境要求)
- **Python**: Version 3.10 or higher.
- **Ollama**: Local LLM server running on your machine.
  - Install Ollama from [ollama.com](https://ollama.com).
  - Pull and run the default model specified in [config.yml](file:///c:/Users/zohanlin/Documents/zohan_ai_test/Ann/config.yml) (typically `gemma4:e4b`):
    ```bash
    ollama run gemma4:e4b
    ```

### 2. Dependency Installation (安裝依賴)
Install the required packages from the dependency manifest:
```bash
pip install -r current/requirements.txt
```
This installs `PyQt6` (for GUI), `pygame` (for audio alarms), and `ollama` (for API integration).

### 3. Running Ann (啟動方式)
You can run Ann in two modes. The launcher automatically monitors and updates the core:
- **GUI Mode (Default)**:
  ```bash
  python launcher.py
  ```
  Launches a floating bubble avatar. Click to expand into a full dark-mode chat window, drag to reposition, and click the dismiss button or the bubble itself to shut off active alarms.

- **CLI Mode (Terminal)**:
  ```bash
  python launcher.py --cli
  ```
  Runs as a conversational shell in the terminal. If an alarm triggers, it prints reminder alerts every 2 seconds and can be dismissed by pressing Enter.

### ⏰ Alarm Module (鬧鐘功能)
Ann supports conversational alarm management (create, delete, list) through natural conversation. You can set relative/absolute alarms, check active alarms, and cancel them.
For complete architectural details, audio loop specs, and UI animations, see [alarm_module_spec.md](file:///c:/Users/zohanlin/Documents/zohan_ai_test/Ann/alarm_module_spec.md).

---

## 📂 Recommended Directory Structure

The recommended layout for deployment and development:

```text
~/.ai-assistant/
├── launcher.py              # Core launcher (rarely updated, never overwritten)
├── moral_module_spec.md     # ⚖️ Moral & safety specification (designed by OpenAI, audited by Claude — DO NOT MODIFY)
├── config.yml               # User configuration (preserved across updates)
├── logs/                    # System logs
├── current/                 # Active production version
│   ├── assistant.py         # Ann AI assistant core entry point
│   ├── requirements.txt     # Dependencies for this version
│   └── plugins/             # Plugin extension directory
├── staging/                 # Update buffer (download, install deps, and test here)
└── versions/                # Historical version backups (for rollback)
    ├── v1.0.1/
    └── v1.0.2/
```

---

## 🔄 Self-Updating Flow

This system requires **no local git commands** — it relies entirely on the **GitHub REST API** for version control and file delivery.

> [!IMPORTANT]
> **Strict Design Rule**: The update mechanism MUST use the GitHub REST API (HTTP) for all version checking, file listings, and downloads. Using local `git` commands (such as `git pull` or `git fetch`) within the update flow is strictly prohibited to ensure Ann can self-update even when deployed in non-Git target environments.


### 1. Update Sequence Diagram

```mermaid
sequenceDiagram
    participant U as User
    participant A as current/assistant.py
    participant L as launcher.py
    participant S as staging/
    participant GH as GitHub API

    A->>GH: 1. Check latest commit (GET /commits/{branch})
    GH-->>A: Return latest commit (date & SHA)
    Note over A: Format YYYYMMDD-sha and compare with local version.txt

    rect rgb(230, 245, 255)
        Note over A, U: If a new version is available
        A->>U: 2. "New version detected. Update now?"
        U-->>A: Confirm update (Yes)
    end

    A->>L: 3. Send update signal and exit
    L->>GH: 4. Fetch Ann file list (GET /contents/Ann?ref={branch})
    GH-->>L: Return JSON file list (each entry includes download_url)
    L->>GH: 5. Download Ann files (iterate download_url for each file)
    L->>S: 6. Write files to staging/ at their relative paths

    rect rgb(240, 255, 240)
        Note over L, S: Safety validation phase
        L->>S: 7. Run pytest and dependency check in staging
        S-->>L: All tests pass
    end

    L->>L: 8. Atomic swap: staging/ -> current/
    L->>A: 9. Restart new version of assistant.py (Ann)
```

### 2. GitHub API Details

* **Check latest branch commit:**
  ```http
  GET https://api.github.com/repos/{owner}/{repo}/commits/{branch}
  ```
  Extract `commit.committer.date` (formatted as `YYYYMMDD`) and `sha` (first 7 characters) and combine them into `YYYYMMDD-sha`. Compare this formatted string with the local `version.txt` to determine whether an update is needed.

* **Fetch file list for the Ann directory:**
  ```http
  GET https://api.github.com/repos/zohanlin2-ai/AI-coding-only/contents/Ann?ref={branch}
  ```
  Returns a JSON list of files and subdirectories under `Ann/`.

* **Download a single file (raw content):**
  ```http
  GET https://raw.githubusercontent.com/zohanlin2-ai/AI-coding-only/{branch}/Ann/{path_to_file}
  ```
  Each file's `download_url` from the JSON list is used to download the file directly into the corresponding path under `staging/`. This approach downloads **only the `Ann` project** — not the entire repository.

> [!TIP]
> **API Access & Rate Limits:**
> - **Public Repo**: No token required, but limited to 60 requests/hour.
> - **Private Repo**: Must include a Personal Access Token (PAT) in the header — `Authorization: Bearer <YOUR_TOKEN>`.
> - **Recommendation**: Even for public repos, configuring a token raises the limit to 5,000 requests/hour.


---

## ⚠️ Local Environment Challenges & Solutions

| Challenge | Solution |
| :--- | :--- |
| **File lock / in-use** | Python cannot modify its own running code. `launcher.py` spawns `assistant.py` as a subprocess; during update, the child process is terminated, files are swapped, and it is restarted. |
| **Dependency updates (`pip`)** | New versions may introduce new third-party packages. `virtualenv` isolation in `staging/` validates new dependencies before writing to the production environment. |
| **Interrupting active conversation** | The update prompt is shown at conversation breaks. The user may choose "later" or "skip this version" to avoid unwanted interruptions. |
| **Network unavailable** | GitHub API calls fail when offline. A graceful fallback keeps the existing version running and records the failure in the log. |

### 💬 UX Interaction Example

When a new version is detected, the assistant proactively prompts the user rather than forcing an update:

```text
Ann: "New version v1.2.0 is available. It includes:
      - Added memory feature
      - Improved response speed
      Update now? (yes / later / skip this version)"
```

---

## ⚖️ Moral & Safety Specification Module

This project integrates [moral_module_spec.md](./moral_module_spec.md) to evaluate user requests, system actions, and autonomous decisions, ensuring Ann's behavior aligns with ethical principles, safety constraints, and accountability requirements.

> [!IMPORTANT]
> **Moral Module Authorship & Audit Declaration:**
> - **Designed by**: **OpenAI**
> - **Audited by**: **Claude**
> - **⚠️ Modification strictly prohibited**: **No one is permitted to modify `moral_module_spec.md`.** The integrity of Ann's moral baseline depends on this file remaining unchanged.

### 🛑 Protected Updates in the Self-Updating Mechanism

Per [moral_module_spec.md](./moral_module_spec.md) §20, the moral module is a **protected component**:

1. **No automatic updates**: Any change to the moral module, its prompts, policies, classifiers, tool permissions, or risk thresholds **must never** be applied silently via the auto-update mechanism (`allowAutomaticMoralUpdates: false`).
2. **Explicit confirmation required**: Updates to the moral module require explicit approval from the user or an authorized operator, must pass a safety and regression test suite, and must provide a rollback path to the previous version.

### ⚠️ Current Implementation Status & Limitations

- **Rule-Based Engine**: The moral evaluator currently uses a deterministic regex rules engine for risk classification. It does not yet employ a hybrid/semantic LLM classifier.
- **Risk of Over-Refusal (False Positives)**: Due to the keyword/regex nature, benign or fictional requests containing sensitive terms (e.g., educational or creative writing requests) may trigger unnecessary refusals or safeguards.
- **Simplified Interface**: The current implementation handles basic risk assessment and output decisions but does not yet support the full Section 26 data structure, audit log generation, or E1–E5 local escalation confirmation dialogs.

---

## 🚀 Development Roadmap

To minimize complexity, implement the project in the following order:

1. **Step 1: Persistent Launcher**
   - Implement `launcher.py` to spawn `assistant.py` as a subprocess and monitor its lifecycle.
2. **Step 2: GitHub Version Detection**
   - Implement the API call, compare tag versions, and signal the launcher when an update is available.
3. **Step 3: Secure Download & pytest Validation**
   - Fetch the `Ann/` file list via the Contents API, download each file into `staging/`, then run `pytest` in an isolated environment using `subprocess`.
4. **Step 4: Atomic Swap & Rollback**
   - Implement directory swap logic; on test failure, clear `staging/`, retain the current version, and notify the user.
5. **Step 5: AI Dialogue, Plugin System & Moral Module Integration**
   - Integrate an LLM SDK (e.g. Ollama, LangChain, or Anthropic/OpenAI SDK) into `assistant.py`, and wire up the decision pipeline and risk classifier defined in [moral_module_spec.md](./moral_module_spec.md) to complete Ann's full core functionality.
