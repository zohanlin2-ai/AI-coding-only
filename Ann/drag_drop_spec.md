# Drag and Drop Module Specification

## 1. Purpose

This document defines the specification for the Drag and Drop (DND) module in the PyQt6-based Ann AI assistant application.

The goal is to allow users to easily import files (plain text and images) into the conversation context by dragging them from their system file explorer and dropping them onto either the floating bubble or the chat window. Dropped files can be clicked to open a detailed preview popup window.

---

## 2. Scope

### 2.1 In Scope for Initial Release
- **FloatingBubble (State 1) DND**:
  - Dragging files over the bubble highlights the bubble (visual feedback).
  - Dropping files onto the bubble automatically expands it into the `ChatWindow` and loads the files as attachments.
- **ChatWindow (State 2) DND**:
  - Dragging files over the window shows a semi-transparent drag-and-drop overlay.
  - Dropping files adds them to an attachment list located above the text input field.
- **Attachment Preview**:
  - Clicking on the attachment file name opens a popup window (`AttachmentViewerDialog`) showing the file content.
- **Supported Formats**:
  - **Plain Text / Code**: `.txt`, `.md`, `.py`, `.js`, `.json`, `.csv`, `.html`, `.css`, `.yaml`, `.yml`, `.ini`, `.cfg`, `.log`, `.c`, `.cpp`, `.java`, `.sh`, `.ts`, `.sql`, `.toml`, `.env`, `.xml`.
  - **Images**: `.png`, `.jpg`, `.jpeg`, `.webp`.
- **LLM Integration**:
  - For text files: Automatically appends the content as code blocks to the next user message sent to the LLM.
  - For image files: Prepares them for multimodal Ollama calls (if supported by the model), or displays attachment metadata in the user message.

### 2.2 Out of Scope (TBD for Future Releases)
- **PDF Documents**: `.pdf` (Requires third-party parser, e.g., `pypdf`).
- **Word/Excel Documents**: `.docx`, `.xlsx` (Requires third-party parsers).
- **Audio/Video Media**: `.wav`, `.mp3`, `.mp4` (Requires media players/transcribers).

---

## 3. UI/UX Interaction Design

### 3.1 Floating Bubble (State 1) DND State
- **Idle State**: Standard slate-gray or alarm-active yellow gradient.
- **Drag Hover State**: 
  - The bubble's scale increases slightly (by $10\%$).
  - The blue glowing border changes to a pulsing green/cyan border (`QColor(72, 187, 120)`).
- **Drop Action**:
  - The bubble triggers `expand_to_chat()` immediately.
  - The dropped files are loaded and rendered in the `ChatWindow` attachment list.

### 3.2 Chat Window (State 2) DND State
- **Drag Hover State**:
  - A semi-transparent overlay widget (`DragDropOverlay`) fades in over the message viewport.
  - Text on overlay: `Drop files to load` with a modern dashed border design.
- **Drop Action**:
  - The overlay fades out.
  - Files are processed and appended to the **Attachment Tray**.

### 3.3 Attachment Tray & Preview Dialog
- **Attachment Tray**:
  - Positioned right above the bottom message input area.
  - Displays files horizontally.
  - Each item contains:
    - A file type icon (or image thumbnail for pictures).
    - A clickable link/button with the file name.
    - A small close button `[X]` to remove the attachment.
- **Attachment Viewer Dialog (`AttachmentViewerDialog`)**:
  - Triggered by clicking on the attachment file name.
  - **Text View**: A scrollable, read-only monospace text viewer (`QTextEdit`) displaying file contents.
  - **Image View**: A scrollable viewport (`QLabel` inside a `QScrollArea`) displaying the image scaled to fit, with high-quality rendering.
  - Standard title bar with close button.

---

## 4. Technical Architecture

### 4.1 Component Diagram
```
[External Explorer] -> (Drag & Drop File List)
                             │
                             ▼
              [Drag & Drop Event Handler]
                             │
              ┌──────────────┴──────────────┐
              ▼                             ▼
       [FloatingBubble]               [ChatWindow]
   (Auto-expands to ChatWindow)              │
              │                              │
              └──────────────┬───────────────┘
                             ▼
                    [Attachment Tray]
                             │
           ┌─────────────────┼─────────────────┐
           ▼                 ▼                 ▼
   [Click on Filename]  [Click Send]      [Click Delete]
           │                 │                 │
           ▼                 ▼                 ▼
[AttachmentViewerDialog] [Ollama Message]  [Remove Item]
```

### 4.2 Class Specifications

#### `DragDropOverlay(QWidget)`
A custom overlay widget that covers the entire chat window during drag operations.
- Background color: `rgba(26, 29, 36, 200)` (matches dark mode UI).
- Label: centered text with dashed border stylesheet.

#### `AttachmentItem(QFrame)`
Individual attachment badge in the tray.
- Layout: Horizontal layout containing a thumbnail/icon, a clickable label (`QPushButton` styled as text link), and a remove button (`QPushButton`).
- Clicking the filename button emits `clicked_file(file_path: Path)`.
- Clicking the remove button emits `removed(file_path: Path)`.

#### `AttachmentViewerDialog(QDialog)`
Modal or non-modal popup window to display the attachment contents.
- `__init__(self, file_path: Path, parent=None)`
- Automatically detects file type (via MIME or extension).
- Renders text or image appropriately.

---

## 5. File Formats & Reading Mechanism

### 5.1 File Type Identification
Files are checked by suffix extension:
- **Text Suffixes**: `.txt`, `.md`, `.py`, `.js`, `.json`, `.csv`, `.html`, `.css`, `.yaml`, `.yml`, `.ini`, `.cfg`, `.log`, `.c`, `.cpp`, `.java`, `.sh`, `.ts`, `.sql`, `.toml`, `.env`, `.xml`.
- **Image Suffixes**: `.png`, `.jpg`, `.jpeg`, `.webp`, `.bmp`.

### 5.2 Plain Text Reader
- Read using standard UTF-8 encoding with exception fallbacks (e.g., `utf-8-sig`, `latin-1`).
- File size limit: **5 MB** for safe UI responsiveness (warns user if files exceed this limit).
- Large files are read asynchronously via a worker thread to prevent GUI freezing.

### 5.3 Image Reader
- Loaded using `QPixmap`.
- Displayed as a scaled thumbnail in the attachment tray ($32 \times 32$ pixels).
- Scale-to-fit in the `AttachmentViewerDialog` using `Qt.AspectRatioMode.KeepAspectRatio`.

---

## 6. Prompt Injection & LLM Delivery

When the user clicks "Send" with attachments in the tray:
1. **Text Attachments**:
   - The contents of each text file are read.
   - Formatted into the user message sent to the LLM:
     ```text
     [Attached File: {filename}]
     ```{file_extension}
     {file_contents}
     ```
     
     {user_text_input}
     ```
2. **Image Attachments**:
   - If using Ollama's API:
     - For models supporting vision (multimodal), encode image in base64 and attach in the `"images"` field of the chat message API payload.
     - For non-vision models (e.g., Gemma, Llama 3), append metadata: `[Attached Image: {filename}]` to notify the assistant that the user reference is an image, and prompt the LLM to guide the user accordingly.
3. Once the message is sent, clear the attachment tray.

---

## 7. Dependencies

- `PyQt6` or `PySide6` (standard GUI core libraries).
- No new external pip packages are needed for initial release (all text and image manipulation is handled by standard python libraries and PyQt/PySide).

---

## 8. Verification & Testing

### 8.1 Automated Unit Tests
- Test cases verifying file suffix recognition (`is_text_file(path)`, `is_image_file(path)`).
- Test cases checking files exceeding size limits.

### 8.2 Manual Verification Scenario
1. **Scenario 1**: Drag a `.py` file from Windows Explorer into `FloatingBubble`. Confirm it expands, shows the file name, and clicking the name displays the code in a popup.
2. **Scenario 2**: Drag a `.png` file into `ChatWindow`. Confirm it appears in the tray, clicking it shows the popup, and clicking `X` deletes it.
3. **Scenario 3**: Send a message containing a `.txt` file attachment to Ollama, verify that the assistant successfully answers questions about the file's content.
