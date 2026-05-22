import re
import random
from typing import List, Dict, Any
from ai_agent import AIAgent

def parse_nomination(text: str, agents: List[AIAgent]) -> int:
    """
    Parses the text for nominations (e.g. @Role) and returns the index of the nominated agent.
    Returns -1 if no valid agent is nominated.
    """
    if not text or len(agents) <= 1:
        return -1
        
    # Match '@' followed by non-whitespace and non-punctuation characters
    mentions = re.findall(r'@([^\s,.;!?，。！？、：:()（）]+)', text)
    
    for mention in mentions:
        mention_clean = mention.strip().lower()
        if not mention_clean:
            continue
            
        # Try to find a matching agent by role or name (case-insensitive substring match)
        for idx, agent in enumerate(agents):
            role_clean = agent.role.strip().lower()
            name_clean = agent.name.strip().lower()
            
            # Match if the mention is a substring of the role/name, or vice-versa
            if (mention_clean in role_clean or role_clean in mention_clean or
                mention_clean in name_clean or name_clean in mention_clean):
                return idx
                
    return -1

def get_next_speaker(
    mode: str, 
    current_index: int, 
    agents: List[AIAgent], 
    last_message_text: str, 
    topic: str,
    conversation_history: List[Dict[str, str]],
    api_keys: Dict[str, str]
) -> int:
    """
    Decides the index of the next speaker based on the selected mode.
    - mode: "Sequential", "Nomination", or "Orchestrator"
    - current_index: the index of the agent who just spoke
    - agents: the list of active AIAgents in the simulation
    - last_message_text: the text of the last spoken message
    """
    num_agents = len(agents)
    if num_agents <= 1:
        return 0

    # 1. Sequential Mode: Just rotate to the next agent in the list
    if mode == "Sequential":
        return (current_index + 1) % num_agents

    # 2. Nomination Mode: Look for @Role in the last message. If not found, do sequential rotation.
    elif mode == "Nomination":
        nominated_idx = parse_nomination(last_message_text, agents)
        if nominated_idx != -1 and nominated_idx != current_index:
            return nominated_idx
        # Fallback to sequential
        return (current_index + 1) % num_agents

    # 3. Orchestrator Mode: Decide using LLM if available, otherwise fallback to smart random rotation.
    elif mode == "Orchestrator":
        # Heuristic/nomination check first (even in Orchestrator mode, direct calls take precedence)
        nominated_idx = parse_nomination(last_message_text, agents)
        if nominated_idx != -1 and nominated_idx != current_index:
            return nominated_idx

        # If API keys are available, try to use LLM to choose the next speaker
        active_provider = None
        active_key = None
        
        # Look for any configured API key to make the orchestrator call
        for provider in ["Gemini", "OpenAI", "DeepSeek", "Claude", "Grok", "Groq", "GitHub"]:
            if api_keys.get(provider.lower()):
                active_provider = provider
                active_key = api_keys[provider.lower()]
                break

        if active_provider and active_key:
            try:
                # Compile characters list
                characters_str = "\n".join([f"- 索引 {idx}: {a.name} (角色: {a.role})" for idx, a in enumerate(agents)])
                
                # Context prompt
                system_instruction = (
                    "你是一個對話主持人，負責引導一個 AI 群聊對話。\n"
                    "請閱讀先前的對話紀錄與主題，並從名單中決定下一個最適合發言的 AI 角色索引。\n"
                    "請只輸出該角色的「數字索引」，絕對不要輸出任何其他文字。"
                )
                
                history_log = "先前對話紀錄：\n"
                for msg in conversation_history[-8:]: # limit history to save tokens
                    history_log += f"[{msg['name']} ({msg['role']})]: {msg['text']}\n"
                
                prompt = (
                    f"討論主題：「{topic}」\n\n"
                    f"候選 AI 角色名單：\n{characters_str}\n\n"
                    f"{history_log}\n"
                    f"請問下一句話由誰說最適合？請從 0 到 {num_agents - 1} 中選擇一個索引：\n"
                    f"（請只輸出一個數字）"
                )

                decision_idx = -1
                if active_provider == "Gemini":
                    import google.generativeai as genai
                    genai.configure(api_key=active_key)
                    model = genai.GenerativeModel("gemini-2.5-flash", system_instruction=system_instruction)
                    response = model.generate_content(prompt)
                    res_text = response.text.strip()
                    # Try to extract the first digit
                    match = re.search(r'\d+', res_text)
                    if match:
                        decision_idx = int(match.group())
                elif active_provider in ["OpenAI", "DeepSeek", "Grok", "Groq", "GitHub"]:
                    from openai import OpenAI
                    if active_provider == "DeepSeek":
                        base_url = "https://api.deepseek.com"
                        model_name = "deepseek-chat"
                    elif active_provider == "Grok":
                        base_url = "https://api.x.ai/v1"
                        model_name = "grok-2-1212"
                    elif active_provider == "Groq":
                        base_url = "https://api.groq.com/openai/v1"
                        model_name = "gemma2-9b-it"
                    elif active_provider == "GitHub":
                        base_url = "https://models.github.ai/inference"
                        model_name = "gpt-4o-mini"
                    else:
                        base_url = None
                        model_name = "gpt-4o-mini"
                    client = OpenAI(api_key=active_key, base_url=base_url)
                    response = client.chat.completions.create(
                        model=model_name,
                        messages=[
                            {"role": "system", "content": system_instruction},
                            {"role": "user", "content": prompt}
                        ],
                        max_tokens=10
                    )
                    res_text = response.choices[0].message.content.strip()
                    match = re.search(r'\d+', res_text)
                    if match:
                        decision_idx = int(match.group())
                elif active_provider == "Claude":
                    from anthropic import Anthropic
                    client = Anthropic(api_key=active_key)
                    response = client.messages.create(
                        model="claude-3-haiku-20240307",
                        max_tokens=10,
                        system=system_instruction,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    res_text = response.content[0].text.strip()
                    match = re.search(r'\d+', res_text)
                    if match:
                        decision_idx = int(match.group())

                if 0 <= decision_idx < num_agents:
                    return decision_idx
            except Exception:
                # On API error, fallback to random heuristic
                pass

        # Smart Heuristic Fallback: Randomly pick another agent (not the current one)
        choices = [i for i in range(num_agents) if i != current_index]
        if choices:
            return random.choice(choices)
        return (current_index + 1) % num_agents

    return (current_index + 1) % num_agents
