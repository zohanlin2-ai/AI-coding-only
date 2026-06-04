"""
file_handler.py — conversational file generation handler.
"""
import re
import json
import logging
from pathlib import Path

from base_intent_parser import BaseIntentParser, ModuleResult

logger = logging.getLogger(__name__)

# Keywords to pre-filter normal messages to avoid unnecessary Ollama parser calls
FILE_KEYWORDS = ["存", "儲存", "匯出", "寫入", "輸出", "保存", "save", "export", "write", "output"]

FILE_SYSTEM_PROMPT = (
    "You are an intent parser for a file-saving assistant.\n"
    "Extract the user's file export/saving intent from the message below.\n"
    "Respond ONLY with a valid JSON object. No explanation, no markdown.\n\n"
    "JSON schema:\n"
    "{\n"
    '  "intent": "export_history | save_code | none",\n'
    '  "filename": "string or null (the name of the file to save/export, e.g. history.md, app.py)",\n'
    '  "target": "string or null (e.g. python, html, css, code, or null to match the target language or block description)"\n'
    "}\n\n"
    "Rules:\n"
    "- 'export_history' intent: User wants to save or export the chat history/conversation logs. (e.g. '把對話紀錄存成 chat.txt', '匯出聊天紀錄')\n"
    "- 'save_code' intent: User wants to save code blocks or code snippets from the conversation to a file. (e.g. '把剛剛寫的 python 程式存到 main.py', '將代碼寫入 app.py')\n"
    "- If no file saving intent is detected, set intent to 'none'.\n"
    "- Extract the filename if the user specified one. If no filename is specified but a saving intent is clear, generate a reasonable default filename based on the context (e.g., 'conversation.md' for export_history, or 'code.py' / 'code.html' based on the target language for save_code).\n"
)


def parse_markdown_blocks(text: str) -> list[dict]:
    """
    Parses response text and splits it into a sequence of text and code blocks.
    Example:
        [
            {"type": "text", "content": "Here is the code:\n"},
            {"type": "code", "language": "python", "content": "print('hello')"},
            {"type": "text", "content": "\nHope this helps!"}
        ]
    """
    pattern = r"```([a-zA-Z0-9+#-]+)?\n(.*?)\n```"
    
    blocks = []
    last_end = 0
    
    for match in re.finditer(pattern, text, re.DOTALL):
        # Add preceding text block if it has content
        pre_text = text[last_end:match.start()]
        if pre_text:
            blocks.append({"type": "text", "content": pre_text})
            
        language = match.group(1) or ""
        code_content = match.group(2) or ""
        blocks.append({
            "type": "code",
            "language": language.strip(),
            "content": code_content
        })
        last_end = match.end()
        
    # Add trailing text block if any
    post_text = text[last_end:]
    if post_text:
        blocks.append({"type": "text", "content": post_text})
        
    # If no blocks were added, return the original text as a single text block
    if not blocks and text:
        blocks.append({"type": "text", "content": text})
        
    return blocks


class FileIntentParser(BaseIntentParser):
    KEYWORDS = FILE_KEYWORDS

    def _build_system_prompt(self) -> str:
        return FILE_SYSTEM_PROMPT

    def _validate_and_normalize(self, result: dict) -> dict:
        if "intent" not in result:
            result["intent"] = "none"
        if result.get("intent") not in ["export_history", "save_code", "none"]:
            result["intent"] = "none"
        return {
            "intent": result.get("intent", "none"),
            "filename": self._clean_val(result.get("filename")),
            "target": self._clean_val(result.get("target")),
        }

    def _empty_result(self) -> dict:
        return {"intent": "none", "filename": None, "target": None}

    def execute(self, parsed: dict, context: dict) -> ModuleResult:
        """Run the file save/export operation and return a ModuleResult."""
        reply = handle_file_intent(
            parsed,
            context["conversation"],
            context["base_dir"],
        )
        return ModuleResult(reply=reply or "")

    def _regex_fallback(self, text: str) -> dict:
        """Simple rule-based regex fallback when Ollama is offline or fails."""
        text_lower = text.lower()

        # Find potential filename in text
        fn_match = re.search(r"([a-zA-Z0-9_\-]+\.[a-zA-Z0-9]+)", text_lower)
        filename = fn_match.group(1) if fn_match else None

        # Check for history keywords
        history_keywords = ["對話", "聊天", "歷史", "紀錄", "log", "history"]
        if any(w in text_lower for w in history_keywords):
            return {
                "intent": "export_history",
                "filename": filename or "conversation.md",
                "target": None,
            }

        # If there's a filename with a code-like extension, default to save_code
        code_extensions = [
            ".py", ".js", ".json", ".csv", ".html", ".css", ".yaml", ".yml",
            ".ini", ".cfg", ".log", ".c", ".cpp", ".java", ".sh", ".ts",
            ".sql", ".toml", ".env", ".xml"
        ]
        if filename:
            suffix = Path(filename).suffix.lower()
            if suffix in code_extensions:
                return {"intent": "save_code", "filename": filename, "target": suffix[1:]}

        # Check for code keywords
        code_keywords = ["code", "程式", "代碼", "區塊", "snippet"]
        if any(w in text_lower for w in code_keywords) or filename:
            target = None
            if filename:
                suffix = Path(filename).suffix.lower()
                if suffix:
                    target = suffix[1:]
            return {"intent": "save_code", "filename": filename or "code.txt", "target": target}

        return self._empty_result()


def handle_file_intent(parsed: dict, conversation: list[dict], base_dir: Path) -> str | None:
    """
    Executes the file writing/exporting operation based on the parsed intent.
    """
    intent = parsed.get("intent", "none")
    if intent == "none":
        return None
        
    filename = parsed.get("filename") or "output.txt"
    # Sanitize filename to prevent path traversal outside workspace
    filename = Path(filename).name
    target_path = base_dir / filename
    
    if intent == "export_history":
        if not conversation:
            return "目前沒有對話紀錄可以匯出。"
        try:
            lines = []
            for msg in conversation:
                role = "User" if msg["role"] == "user" else "Ann"
                content = msg["content"]
                
                # Strip helper instructions if any
                if msg["role"] == "user" and content.startswith("[Important:"):
                    parts = content.split("User: ", 1)
                    if len(parts) > 1:
                        content = parts[1]
                        
                lines.append(f"### {role}\n{content}\n")
                
            content_to_write = "\n".join(lines)
            target_path.write_text(content_to_write, encoding="utf-8")
            return f"已幫您將對話紀錄匯出至 [{filename}](file:///{target_path.as_posix()})。"
        except Exception as e:
            return f"匯出對話紀錄時發生錯誤：{str(e)}"
            
    elif intent == "save_code":
        code_content = None
        target_lang = parsed.get("target")
        
        # Search backwards to find the last assistant message with a code block
        for msg in reversed(conversation):
            if msg["role"] == "assistant":
                blocks = parse_markdown_blocks(msg["content"])
                code_blocks = [b for b in blocks if b["type"] == "code"]
                if not code_blocks:
                    continue
                    
                if target_lang:
                    # Search specifically for the matching language
                    matched = [b for b in code_blocks if b["language"].lower() == target_lang.lower()]
                    if matched:
                        code_content = matched[-1]["content"]
                        break
                        
                code_content = code_blocks[-1]["content"]
                break
                
        if not code_content:
            return "找不到可以儲存的程式碼區塊。"
            
        try:
            target_path.write_text(code_content, encoding="utf-8")
            return f"已將程式碼儲存至 [{filename}](file:///{target_path.as_posix()})。"
        except Exception as e:
            return f"儲存程式碼時發生錯誤：{str(e)}"
            
    return None
