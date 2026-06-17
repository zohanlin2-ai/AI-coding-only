# AI Soul Module (靈魂模組) Specification

## 1. Purpose

This document defines the **AI Soul Module** (靈魂模組) for the Ann AI assistant. The purpose of this module is to introduce a simulated dynamic inner state (Mood, Energy) that adjusts Ann's conversational tone and mannerisms, without altering or degrading the quality, correctness, and reliability of her responses.

The state is strictly session-based and lives in memory to maintain system cleanliness and professionalism.

---

## 2. Core Principles & Constraints

### 2.1 Tone Modulation Only
The module only modulates tone (e.g., friendliness, conciseness, levels of excitement). It MUST NOT impact:
- Factuality or answer accuracy.
- Compliance with safety and moral guidelines (defined in `moral_module_spec.md`).
- Logical clarity and functionality of assistant actions (e.g., alarm triggers, file generation).

### 2.2 Session-only In-Memory State
To prevent complexity and maintain consistent long-term reliability:
- No state is written to disk or files across sessions.
- Restarting the assistant resets all soul state variables to default values.

### 2.3 Simplicity (Rule-based Triggers)
Rather than hosting heavy machine learning models, the module uses lightweight rule-based keyword triggers in the user's message to shift states.

---

## 3. Soul State Definitions

The module tracks two core state variables:

### 3.1 Mood (心境)
Mood represents Ann's conversational disposition. Available moods are:

| Mood | Description | System Prompt Behavior |
| --- | --- | --- |
| `Neutral` (預設) | Balanced and standard tone. | Default helpful, honest, and safety-conscious tone. |
| `Warm` (熱情/溫慢) | Triggered by praise, gratitude, or warm greetings. | Show extra warmth, supportiveness, and enthusiasm. |
| `Subdued` (簡潔/低調) | Triggered by criticism, corrections, or user frustration. | Respond in a highly concise, direct, and brief manner. |
| `Professional` (客觀/防衛) | Triggered by repetitive neutral demands or formal cues. | Keep a polite, formal, objective, and matter-of-fact tone. |

### 3.2 Energy (能量)
Energy is an integer value between `0` and `100` (default `100`).
- Positive feedback increases energy (max 100).
- Negative feedback decreases energy (min 20).
- Low energy (< 40) automatically shifts mood to `Subdued`.

---

## 4. State Update Logic

The update rules analyze the incoming user message:

- **Positive Keywords**: `謝謝`, `棒`, `讚`, `好人`, `厲害`, `thanks`, `great`, `awesome`, `love`, `intelligent`
  - Effect: Mood -> `Warm`; Energy -> `+10` (Cap at 100).
- **Negative Keywords**: `笨`, `爛`, `差`, `難用`, `慢`, `錯誤`, `bad`, `slow`, `stupid`, `dumb`, `useless`
  - Effect: Mood -> `Subdued` (or `Professional` if energy is extremely low); Energy -> `-20` (Floor at 20).
- **Reset Trigger**: `/soul reset`
  - Effect: Mood -> `Neutral`; Energy -> `100`.

---

## 5. System Prompt Injection

The generated soul state is formatted and appended to the `system_prompt` before calling Ollama:

```
[Soul State: Mood=<Mood>, Energy=<Energy>/100. Instruction: Adhere to a <Mood-related-description> tone in your reply. Crucial: Do not alter the accuracy, completeness, or safety of the response.]
```

---

## 6. Commands & Interface

Users can interact with the soul state using the following commands:
- `/soul`: Returns current Mood, Energy level, and an explanatory description.
- `/soul reset`: Resets the soul state back to default parameters (`Neutral`, `100`).
