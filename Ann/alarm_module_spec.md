# Alarm Module Specification

## 1. Purpose

This document defines the alarm module for a PyQt6-based AI assistant application.

The module integrates with an existing AI chat interface and allows users to set, query, and delete alarms entirely through natural conversation. Ollama handles intent parsing and response generation. The system manages scheduling, persistence, and alarm triggering independently.

---

## 2. Scope

This specification covers:

- Conversational alarm management via Ollama
- Time parsing including absolute, relative, and cross-day expressions
- Local persistence of alarm data
- Alarm triggering with audio and visual effects
- Alarm limit enforcement
- One-time alarm lifecycle (set → trigger → auto-delete)
- Repeating or recurring alarms (daily, weekly, interval-based)

Out of scope for this version:

- User-selectable alarm sounds via conversation (planned for future release)

---

## 3. System Architecture

### 3.1 Component Overview

```
User Input (chat)
      ↓
Ollama Intent Parser
      ↓
Alarm Manager
  ├── Alarm Store (JSON)
  ├── Alarm Scheduler (QTimer)
  └── Alarm Trigger Handler
            ├── Audio Player (pygame)
            └── Visual Effect (PyQt6 animation)
      ↓
Ollama Response Generator
      ↓
Chat UI
```

### 3.2 Ollama Roles

Ollama performs two roles in this module:

**Intent Parsing**
Every user message is first sent to Ollama with a structured system prompt asking it to classify the intent and extract parameters. The output is a JSON object. Natural language generation is not performed in this step.

**Response Generation**
After the system executes the action, Ollama generates a natural language reply to the user based on the action result.

---

## 4. Intent Recognition

### 4.1 Supported Intents

| Intent | Example Utterances |
|--------|-------------------|
| `set_alarm` | "Wake me up at 8 AM tomorrow", "Remind me in 30 minutes", "Set an alarm at 11:50 PM, note: take medicine" |
| `list_alarms` | "What alarms have I set?", "How many alarms do I have?", "List all reminders" |
| `delete_alarm` | "Delete the 8 AM alarm", "Cancel reminder ID 3", "Remove the take-medicine one" |
| `update_alarm` | "Change the 3 PM alarm to 4 PM", "Move the meeting alarm to 5 PM" |
| `none` | Conversation unrelated to alarms |

### 4.2 Ollama Parsing Prompt

The system prompt sent to Ollama for intent parsing should follow this structure:

```
You are an intent parser for an alarm assistant. 
The current datetime is: {ISO-8601 datetime}.

Extract the user's alarm intent from the message below.
Respond ONLY with a valid JSON object. No explanation, no markdown.

JSON schema:
{
  "intent": "set_alarm | list_alarms | delete_alarm | update_alarm | none",
  "time": "ISO-8601 datetime or null",
  "label": "string or null",
  "alarm_id": "string or null",
  "target_alarm": "string or null"
}

Rules:
- For relative times like "30 minutes later", calculate from current datetime.
- For "tonight at 11:50 PM", use today's date.
- For "tomorrow morning at 8", use tomorrow's date.
- If the user says a time without a date and it has already passed today, assume today unless context implies otherwise.
- label is optional free text the user wants attached to the alarm.
- alarm_id is used only for delete_alarm or update_alarm intent if user specifies ID.
- target_alarm is used for delete_alarm or update_alarm to identify which alarm (e.g. '3 PM', 'meeting').
```

### 4.3 Parsed Output Example

```json
{
  "intent": "set_alarm",
  "time": "2026-05-28T08:00:00",
  "label": "take medicine",
  "alarm_id": null
}
```

---

## 5. Time Parsing Rules

| Input Type | Rule |
|------------|------|
| Absolute time, no date | Use today's date. If the time has already passed, keep today (do not auto-advance to tomorrow). |
| Relative time | Calculate from current system time at the moment of parsing. |
| Explicit date + time | Use as stated. |
| Cross-day (e.g. 23:50 tonight) | Use today's date regardless of current time. |
| Ambiguous AM/PM | Ollama should infer from context. If unclear, ask the user. |

---

## 6. Alarm Data Model

### 6.1 Single Alarm Schema

```json
{
  "id": "uuid-string",
  "datetime": "ISO-8601 datetime",
  "label": "string or null",
  "created_at": "ISO-8601 datetime",
  "triggered": false
}
```

### 6.2 Alarm Store

- Format: JSON file
- Default path: `~/.ai-assistant/alarms.json`
- The store is read on application startup.
- All write operations (create, delete, trigger) update the file immediately.
- Expired alarms (past datetime, triggered) are removed on startup and after triggering.

---

## 7. Alarm Limit

- Maximum active alarms: **10**
- When the user attempts to set an alarm and 10 alarms already exist:
  1. The system does not create the new alarm.
  2. Ollama lists the current 10 alarms with their IDs, times, and labels.
  3. Ollama asks the user which one to delete to make room.
  4. The user replies with their choice.
  5. The system deletes the chosen alarm and then sets the new one.

---

## 8. Alarm Scheduling

- Use `QTimer` with a polling interval of **30 seconds** to check for due alarms.
- An alarm is considered due when `current_datetime >= alarm.datetime`.
- On application startup, load all alarms from the store and register them with the scheduler.
- When a new alarm is saved, register it with the scheduler immediately without requiring a restart.

---

## 9. Alarm Triggering

When an alarm is due, the system executes the following in order:

1. Play the alarm sound.
2. Start the visual effect on the appropriate UI element.
3. Display a dismissal prompt (banner or overlay).
4. Wait for user dismissal or timeout.
5. Stop sound and visual effect.
6. Mark the alarm as triggered and remove it from the store.
7. Have Ollama generate a brief contextual message in the chat (e.g. "Time to take your medicine!").

### 9.1 Sound

- **Audio file:** `428157__setuniman__charade-1q62b.wav`
- **Source:** [freesound.org](https://freesound.org), licensed under Creative Commons (CC0).
- **Library:** `pygame.mixer`
- The audio file path should be configurable in the application settings so that it can be replaced without code changes.
- The sound plays in a loop until dismissed or timeout is reached.
- Maximum playback duration: **60 seconds**. After 60 seconds the sound stops automatically even if the user has not dismissed.

> **Future planned feature:** The user will be able to select a different alarm sound through natural conversation. This will follow the same conversational interface pattern used for alarm management.

### 9.2 Visual Effect

The visual effect target is chosen based on application state:

| State | Effect Target |
|-------|--------------|
| Main window is visible and focused | AI icon or avatar widget |
| Main window is minimized or not focused | Entire application window (taskbar flash + shake on restore) |

Effect behavior:

- **Shake:** The target widget translates left and right repeatedly using `QPropertyAnimation` on the `pos` property.
- **Flash:** The target widget alternates opacity or background color using `QPropertyAnimation` on opacity or a stylesheet toggle.
- Both animations run simultaneously in a `QParallelAnimationGroup`.
- Both animations loop until dismissed or timeout.

### 9.3 Dismissal

- A dismissal button or overlay appears when the alarm triggers.
- A single click or tap dismisses the alarm immediately.
- No confirmation is required.
- After dismissal, sound and animation stop within one animation frame.

---

## 10. Alarm Management via Chat

### 10.1 Set Alarm

**Flow:**
1. User sends a message.
2. Ollama parses intent → `set_alarm`.
3. System checks alarm count.
   - If under 10: create and save the alarm, confirm to user.
   - If at 10: trigger limit flow (see Section 7).
4. Ollama confirms the set alarm with time and label.

**Example exchange:**
```
User:   Wake me up at 7:30 AM tomorrow, note: meeting
System: Done. Alarm set for 2026-05-28 07:30, note: meeting.
```

### 10.2 List Alarms

**Flow:**
1. Ollama parses intent → `list_alarms`.
2. System fetches all active alarms from the store.
3. Ollama formats and presents the list.

**Example exchange:**
```
User:   What alarms do I have?
System: You have 2 active alarms:
        1. [ID: a1b2] 2026-05-28 07:30 — meeting
        2. [ID: c3d4] 2026-05-28 12:00 — take medicine
```

### 10.3 Delete Alarm

**Flow:**
1. Ollama parses intent → `delete_alarm` with alarm_id or descriptive match.
2. System locates the alarm.
   - If found: delete and confirm.
   - If ambiguous: Ollama asks the user to clarify which alarm.
   - If not found: Ollama informs the user.
3. Ollama confirms deletion.

**Example exchange:**
```
User:   Delete the meeting alarm
System: Deleted alarm at 2026-05-28 07:30 (meeting).
```

### 10.4 Update Alarm

**Flow:**
1. Ollama parses intent → `update_alarm` with alarm_id, target_alarm, and the new time.
2. System locates the alarm.
   - If found: updates the target datetime, resets triggered status, and saves.
   - If not found: informs the user.
3. Ollama confirms the modification.

**Example exchange:**
```
User:   Move the 3 PM alarm to 4 PM
System: Done. Alarm updated from 15:00 to 16:00.
```

---

## 11. Error Handling

| Situation | Behavior |
|-----------|----------|
| Ollama returns invalid JSON | Retry once. If still invalid, treat as `none` intent and respond normally. |
| Parsed time is in the past | Ollama informs the user and asks for clarification. |
| Audio file not found | Log the error, skip sound, continue with visual effect only. Notify user in chat. |
| Alarm store file corrupted | Log the error, start with an empty alarm list, notify user. |
| Two alarms due at the same time | Trigger sequentially with a 2-second gap between each. |

---

## 12. File Structure

```
project/
├── current/
│   ├── alarms/
│   │   ├── alarm_manager.py       # Create, delete, list, persist alarms
│   │   ├── alarm_scheduler.py     # QTimer-based polling and trigger dispatch
│   │   ├── alarm_trigger.py       # Sound + visual effect on trigger
│   │   └── intent_parser.py       # Ollama JSON intent extraction
│   ├── 428157__setuniman__charade-1q62b.wav  # Sound asset (CC0)
│   └── requirements.txt           # Python dependency specifications
└── ~/.ai-assistant/
    └── alarms.json            # Persistent alarm store (user home directory)
```

---

## 13. Dependencies

| Package | Purpose |
|---------|---------|
| `PyQt6` | UI, animation, timer |
| `pygame` | Audio playback |
| `ollama` | Intent parsing and response generation |
| `uuid` | Alarm ID generation |
| `json` | Alarm store read/write |
| `datetime` | Time comparison and parsing |

---

## 14. Future Enhancements

The following features are explicitly out of scope for this version but are planned:

- **User-selectable alarm sound:** Allow the user to change the alarm audio file by describing their preference in chat, using the same conversational interface pattern as alarm management.
