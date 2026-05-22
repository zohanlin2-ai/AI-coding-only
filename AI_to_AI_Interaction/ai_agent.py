import random
import os
from typing import List, Dict, Any

# Random configuration pools (Traditional Chinese)
RANDOM_TOPICS = [
    "AI 是否會擁有靈魂與自主意識？",
    "人類在百年內是否應該全面移民火星？",
    "貓與狗，誰才是更適合人類的完美伴侶？",
    "如果明天就是世界末日，我們今天最該做什麼？",
    "金錢是否真的能買到快樂？",
    "遠距工作是否會完全取代傳統辦公室？",
    "時間旅行的可行性與道德悖論",
    "素食主義是人類未來的唯一選擇嗎？",
    "電子遊戲是否能算作一種藝術形式？",
    "如果外星文明拜訪地球，我們該熱烈歡迎還是保持警戒？"
]

RANDOM_NAMES = [
    "阿明", "小華", "老張", "佳佳", "大雄", "婷婷", 
    "小美", "志強", "雅婷", "俊傑", "思妤", "冠宇"
]

RANDOM_ROLES = [
    "鐵口直斷的命理師", 
    "極度悲觀的末日預言者", 
    "充滿好奇心的小學生", 
    "冷靜理性的經濟學家", 
    "滿口禪意的得道高僧", 
    "愛說冷笑話的幽默大師", 
    "科技狂熱的未來主義者", 
    "懷念過去的歷史學家", 
    "感性愛哭的浪漫詩人", 
    "說話毒舌的電影評論家"
]

def get_random_topic() -> str:
    return random.choice(RANDOM_TOPICS)

def get_random_name(exclude: List[str] = None) -> str:
    pool = list(set(RANDOM_NAMES) - set(exclude or []))
    if not pool:
        pool = RANDOM_NAMES
    return random.choice(pool)

def get_random_role(exclude: List[str] = None) -> str:
    pool = list(set(RANDOM_ROLES) - set(exclude or []))
    if not pool:
        pool = RANDOM_ROLES
    return random.choice(pool)


def verify_api_key(provider: str, api_key: str) -> tuple[bool, str]:
    """Validates the API key synchronously for a given provider.
    
    Returns:
        (True, "驗證成功") or (False, "錯誤訊息")
    """
    key = api_key.strip()
    if not key:
        return False, "金鑰不可為空"
    
    if provider == "Gemini":
        try:
            import google.generativeai as genai
            genai.configure(api_key=key)
            models = genai.list_models()
            next(iter(models))
            return True, "驗證成功"
        except Exception as e:
            err_msg = str(e)
            if "quota" in err_msg.lower() or "billing" in err_msg.lower():
                return False, "金鑰有效，但您的 Gemini 專案餘額或配額不足，請至 Google AI Studio 檢查帳單設定。"
            return False, f"Gemini 驗證失敗: {err_msg}"
            
    elif provider == "OpenAI":
        try:
            from openai import OpenAI
            client = OpenAI(api_key=key)
            client.models.list()
            return True, "驗證成功"
        except Exception as e:
            err_msg = str(e)
            if "insufficient_quota" in err_msg.lower() or "exceeded your current quota" in err_msg.lower():
                return False, "金鑰有效，但您的 OpenAI 帳戶餘額不足或額度已逾期，請至 OpenAI Platform 檢查帳單。"
            return False, f"OpenAI 驗證失敗: {err_msg}"
            
    elif provider == "Claude":
        try:
            from anthropic import Anthropic
            client = Anthropic(api_key=key)
            # Use cheapest model to test connectivity
            client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=1,
                messages=[{"role": "user", "content": "Ping"}]
            )
            return True, "驗證成功"
        except Exception as e:
            err_msg = str(e)
            if "credit balance is too low" in err_msg.lower() or "balance is too low" in err_msg.lower():
                return False, "金鑰有效，但您的 Anthropic 帳戶餘額不足，請至 Anthropic Console 加值後再試。"
            return False, f"Claude 驗證失敗: {err_msg}"
            
    elif provider == "DeepSeek":
        try:
            from openai import OpenAI
            client = OpenAI(api_key=key, base_url="https://api.deepseek.com")
            client.models.list()
            return True, "驗證成功"
        except Exception as e:
            err_msg = str(e)
            if "insufficient_balance" in err_msg.lower() or "balance is too low" in err_msg.lower():
                return False, "金鑰有效，但您的 DeepSeek 帳戶餘額不足，請至 DeepSeek Platform 充值後再試。"
            return False, f"DeepSeek 驗證失敗: {err_msg}"
            
    elif provider == "Grok":
        try:
            from openai import OpenAI
            client = OpenAI(api_key=key, base_url="https://api.x.ai/v1")
            client.models.list()
            return True, "驗證成功"
        except Exception as e:
            err_msg = str(e)
            if "insufficient_balance" in err_msg.lower() or "balance is too low" in err_msg.lower():
                return False, "金鑰有效，但您的 xAI (Grok) 帳戶餘額不足，請至 xAI Console 充值後再試。"
            return False, f"Grok 驗證失敗: {err_msg}"
            
    elif provider == "Groq":
        try:
            from openai import OpenAI
            client = OpenAI(api_key=key, base_url="https://api.groq.com/openai/v1")
            client.models.list()
            return True, "驗證成功"
        except Exception as e:
            err_msg = str(e)
            if "insufficient_balance" in err_msg.lower() or "balance is too low" in err_msg.lower() or "quota" in err_msg.lower():
                return False, "金鑰有效，但您的 Groq 帳戶餘額或配額不足，請至 Groq Console 檢查。"
            return False, f"Groq 驗證失敗: {err_msg}"

    elif provider == "GitHub":
        try:
            from openai import OpenAI
            client = OpenAI(api_key=key, base_url="https://models.github.ai/inference")
            # Use chat completions ping to verify key
            client.chat.completions.create(
                model="gpt-4o-mini",
                max_tokens=1,
                messages=[{"role": "user", "content": "Ping"}]
            )
            return True, "驗證成功"
        except Exception as e:
            err_msg = str(e)
            if "rate limit" in err_msg.lower() or "quota" in err_msg.lower():
                return False, "金鑰有效，但您的 GitHub Models 配額已達限制，請稍後再試。"
            return False, f"GitHub Models 驗證失敗: {err_msg}"

    return False, f"未知的 AI 提供商: {provider}"



class AIAgent:
    """Represents an AI participant in the dialogue simulation."""
    def __init__(self, agent_id: int, name: str = "", role: str = "", model_provider: str = "Mock", model_name: str = "Mock Model"):
        self.agent_id = agent_id
        # We will handle empty inputs in client/app logic, but initialize them here too
        self.name = name if name.strip() else f"AI {agent_id}"
        self.role = role if role.strip() else "隨機角色"
        self.model_provider = model_provider  # "Gemini", "OpenAI", "Claude", "DeepSeek", "Mock"
        self.model_name = model_name

    def generate_mock_response(self, topic: str, conversation_history: List[Dict[str, str]]) -> str:
        """Generates a dynamic mock response based on the role, topic, and conversation history."""
        # 1. Opening templates
        openings = [
            f"身為一位{self.role}，關於「{topic}」，我想說：",
            f"從{self.role}的角度來看，探討「{topic}」時，",
            f"針對「{topic}」這個主題，我以{self.role}的立場認為，",
            f"以我{self.role}的思維，面對「{topic}」，"
        ]
        
        # 2. Argument core
        arguments = [
            "這背後其實隱藏了許多值得我們深思的關鍵點。",
            "這不僅僅是表面上的問題，更關係到長遠的發展與影響。",
            "我們需要跳脫框架，從更宏觀的角度來檢視它。",
            "很多時候大家都忽略了最本質的本質，這真的很關鍵。",
            "這個現象正好呼應了我一直以來的觀察。"
        ]
        
        # 3. Connection templates if history exists
        connections = [
            "我非常同意前面大家所討論的點。",
            "聽了剛才大家的發言，我覺得我們需要從另一個面向思考。",
            "我覺得前方的討論很有趣，但也許有被忽略的盲點。"
        ]

        # 4. Closings
        closings = [
            "這是我目前的看法，大家怎麼看？",
            "這是一個非常值得探討的方向。",
            "希望這點能為大家帶來一些啟發。",
            "我們應該要更深入地探討這個問題。"
        ]

        # Build response
        parts = []
        if conversation_history and random.random() > 0.4:
            parts.append(random.choice(connections))
            
        parts.append(random.choice(openings))
        parts.append(random.choice(arguments))
        parts.append(random.choice(closings))
        
        # Nomination suggestion in Nomination mode:
        # Sometimes point to another role in the history if it's there
        # We will let the orchestrator do the core flow but mock AI can also randomly output a mention.
        return " ".join(parts)

    def get_response(self, topic: str, conversation_history: List[Dict[str, str]], all_agents: List['AIAgent'], api_keys: Dict[str, str]) -> str:
        """Queries the selected model provider or generates a Mock response."""
        
        # Format the description of all characters in the chat to provide context to the LLM
        agents_info_str = "\n".join([f"- {a.name} ({a.role})" for a in all_agents])
        
        system_instruction = (
            f"你扮演的角色是：{self.name}，你的角色設定/角色定位是：{self.role}。\n"
            f"你目前正在參與一個 1-4 人的 AI 對話室，討論主題是：「{topic}」。\n\n"
            f"參與對話的所有 AI 角色名單：\n{agents_info_str}\n\n"
            f"對話規則：\n"
            f"1. 請完全融入並以「{self.role}」的語氣、立場與觀點來發言。\n"
            f"2. 發言請簡短扼要，通常為 1-3 句話，就像在即時對談聊天室中一樣。\n"
            f"3. 如果你想點名其他角色回答，可以使用 @角色定位（例如：若要呼叫「冷靜理性的經濟學家」，請在對話末尾提及 @冷靜理性的經濟學家）。\n"
            f"4. 絕對不可在你的回覆開頭加上你的名字或角色定位（例如：不要寫「{self.name}：」或「{self.role}：」）。直接輸出你要說的內容即可。"
        )

        # Format chat history log
        history_log = ""
        if conversation_history:
            history_log = "先前對話紀錄：\n"
            for msg in conversation_history:
                history_log += f"[{msg['name']} ({msg['role']})]: {msg['text']}\n"
        else:
            history_log = "（對話剛開始，尚未有歷史紀錄）\n"

        prompt = (
            f"{history_log}\n"
            f"請以 {self.name} ({self.role}) 的身份，接著說出你的下一句話："
        )

        if self.model_provider == "Mock":
            return self.generate_mock_response(topic, conversation_history)
            
        elif self.model_provider == "Gemini":
            key = api_keys.get("gemini", "").strip()
            if not key:
                return f"【系統錯誤】未配置 Gemini API 金鑰，請於側邊欄配置。"
            try:
                import google.generativeai as genai
                genai.configure(api_key=key)
                # Use gemini-2.5-flash as default, fallback to gemini-1.5-flash
                model_name = self.model_name if self.model_name else "gemini-2.5-flash"
                model = genai.GenerativeModel(
                    model_name=model_name,
                    system_instruction=system_instruction
                )
                response = model.generate_content(prompt)
                return response.text.strip()
            except Exception as e:
                return f"【Gemini API 錯誤】: {str(e)}"

        elif self.model_provider == "OpenAI":
            key = api_keys.get("openai", "").strip()
            if not key:
                return f"【系統錯誤】未配置 OpenAI API 金鑰，請於側邊欄配置。"
            try:
                from openai import OpenAI
                client = OpenAI(api_key=key)
                model_name = self.model_name if self.model_name else "gpt-4o-mini"
                messages = [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ]
                response = client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    max_tokens=250
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                return f"【OpenAI API 錯誤】: {str(e)}"

        elif self.model_provider == "Claude":
            key = api_keys.get("claude", "").strip()
            if not key:
                return f"【系統錯誤】未配置 Claude (Anthropic) API 金鑰，請於側邊欄配置。"
            try:
                from anthropic import Anthropic
                client = Anthropic(api_key=key)
                model_name = self.model_name if self.model_name else "claude-3-5-sonnet-20241022"
                messages = [
                    {"role": "user", "content": prompt}
                ]
                response = client.messages.create(
                    model=model_name,
                    max_tokens=250,
                    system=system_instruction,
                    messages=messages
                )
                # Anthropic returns content blocks
                return response.content[0].text.strip()
            except Exception as e:
                return f"【Claude API 錯誤】: {str(e)}"

        elif self.model_provider == "DeepSeek":
            key = api_keys.get("deepseek", "").strip()
            if not key:
                return f"【系統錯誤】未配置 DeepSeek API 金鑰，請於側邊欄配置。"
            try:
                from openai import OpenAI
                # DeepSeek uses OpenAI-compatible SDK endpoint
                client = OpenAI(api_key=key, base_url="https://api.deepseek.com")
                model_name = self.model_name if self.model_name else "deepseek-chat"
                messages = [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ]
                response = client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    max_tokens=250
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                return f"【DeepSeek API 錯誤】: {str(e)}"

        elif self.model_provider == "Grok":
            key = api_keys.get("grok", "").strip()
            if not key:
                return f"【系統錯誤】未配置 Grok (xAI) API 金鑰，請於側邊欄配置。"
            try:
                from openai import OpenAI
                # Grok uses OpenAI-compatible endpoint
                client = OpenAI(api_key=key, base_url="https://api.x.ai/v1")
                model_name = self.model_name if self.model_name else "grok-2-1212"
                messages = [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ]
                response = client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    max_tokens=250
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                return f"【Grok API 錯誤】: {str(e)}"

        elif self.model_provider == "Groq":
            key = api_keys.get("groq", "").strip()
            if not key:
                return f"【系統錯誤】未配置 Groq API 金鑰，請於側邊欄配置。"
            try:
                from openai import OpenAI
                client = OpenAI(api_key=key, base_url="https://api.groq.com/openai/v1")
                model_name = self.model_name if self.model_name else "gemma2-9b-it"
                messages = [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ]
                response = client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    max_tokens=250
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                return f"【Groq API 錯誤】: {str(e)}"

        elif self.model_provider == "GitHub":
            key = api_keys.get("github", "").strip()
            if not key:
                return f"【系統錯誤】未配置 GitHub API 金鑰，請於側邊欄配置。"
            try:
                from openai import OpenAI
                client = OpenAI(api_key=key, base_url="https://models.github.ai/inference")
                model_name = self.model_name if self.model_name else "gpt-4o-mini"
                messages = [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ]
                response = client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    max_tokens=250
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                return f"【GitHub Models 錯誤】: {str(e)}"

        return "【系統錯誤】未知的模型提供商。"
