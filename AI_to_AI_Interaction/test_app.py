import unittest
from unittest.mock import patch, MagicMock
import re

from ai_agent import (
    AIAgent, 
    get_random_topic, 
    get_random_name, 
    get_random_role,
    verify_api_key,
    RANDOM_TOPICS,
    RANDOM_NAMES,
    RANDOM_ROLES
)
from orchestrator import parse_nomination, get_next_speaker

def format_transcript(topic: str, agents: list, history: list) -> str:
    """Helper function to format chat transcript for export."""
    lines = []
    lines.append(f"# 聊天主題：{topic}\n")
    lines.append("## 參與 AI 角色：")
    for agent in agents:
        lines.append(f"- {agent.name} (角色設定: {agent.role}) [模型: {agent.model_provider} - {agent.model_name}]")
    lines.append("\n---\n")
    for msg in history:
        provider_str = f" | 來自 {msg.get('model_provider', 'Mock')}"
        lines.append(f"[{msg['name']} ({msg['role']}{provider_str})]: {msg['text']}")
    return "\n".join(lines)


class TestAIToAIDialogue(unittest.TestCase):
    
    def setUp(self):
        # Create standard agents for testing
        self.agent1 = AIAgent(agent_id=0, name="阿明", role="得道高僧", model_provider="Mock", model_name="Mock Model")
        self.agent2 = AIAgent(agent_id=1, name="小華", role="未來主義者", model_provider="Mock", model_name="Mock Model")
        self.agent3 = AIAgent(agent_id=2, name="老張", role="冷靜理性的經濟學家", model_provider="Mock", model_name="Mock Model")
        self.agents = [self.agent1, self.agent2, self.agent3]
        self.topic = "AI的未來發展"

    def test_random_generation(self):
        """Test random fallback generators return valid choices and respect exclusions."""
        topic = get_random_topic()
        self.assertIn(topic, RANDOM_TOPICS)
        
        name = get_random_name()
        self.assertIn(name, RANDOM_NAMES)
        
        role = get_random_role()
        self.assertIn(role, RANDOM_ROLES)
        
        # Test exclusions
        excluded_names = RANDOM_NAMES[:-1]
        last_name = RANDOM_NAMES[-1]
        self.assertEqual(get_random_name(exclude=excluded_names), last_name)
        
        excluded_roles = RANDOM_ROLES[:-1]
        last_role = RANDOM_ROLES[-1]
        self.assertEqual(get_random_role(exclude=excluded_roles), last_role)

    def test_mock_ai_generation(self):
        """Test that Mock AI generator contains role and topic reference."""
        # Get response
        response = self.agent1.generate_mock_response(self.topic, [])
        self.assertIsInstance(response, str)
        self.assertTrue(len(response) > 0)
        self.assertIn("得道高僧", response)
        self.assertIn("AI的未來發展", response)
        
        # Verify randomness/variation across calls
        response2 = self.agent1.generate_mock_response(self.topic, [])
        # They should differ in most configurations due to random.choice
        # We run it multiple times to ensure we catch variations
        different = False
        for _ in range(10):
            r = self.agent1.generate_mock_response(self.topic, [])
            if r != response:
                different = True
                break
        self.assertTrue(different, "Mock responses should vary across calls")

    def test_nomination_parsing(self):
        """Test regex extraction of @Role in messages."""
        # 1. Direct mention by role
        text1 = "對啊，你覺得如何？ @未來主義者"
        self.assertEqual(parse_nomination(text1, self.agents), 1)
        
        # 2. Mention by role (substring/fuzzy match)
        text2 = "這個問題，可能需要請問 @高僧 的智慧。"
        self.assertEqual(parse_nomination(text2, self.agents), 0)
        
        # 3. Mention by name
        text3 = "我們來問問 @老張 吧！"
        self.assertEqual(parse_nomination(text3, self.agents), 2)
        
        # 4. No mention
        text4 = "這個主題真是太深奧了。"
        self.assertEqual(parse_nomination(text4, self.agents), -1)
        
        # 5. Invalid mention (role not in chat)
        text5 = "不如聽聽 @心理學家 的想法？"
        self.assertEqual(parse_nomination(text5, self.agents), -1)

    def test_orchestration_logic(self):
        """Test turn-taking orchestration under Sequential and Nomination modes."""
        history = [
            {"name": "阿明", "role": "得道高僧", "text": "善哉善哉。"}
        ]
        
        # 1. Sequential: Current is index 0, next should be index 1 (小華)
        next_speaker = get_next_speaker(
            mode="Sequential",
            current_index=0,
            agents=self.agents,
            last_message_text="善哉善哉。",
            topic=self.topic,
            conversation_history=history,
            api_keys={}
        )
        self.assertEqual(next_speaker, 1)

        # 2. Nomination with mention: Current is 0, mentions @老張, next should be 2 (老張)
        next_speaker_nom = get_next_speaker(
            mode="Nomination",
            current_index=0,
            agents=self.agents,
            last_message_text="我非常好奇 @老張 的經濟看法。",
            topic=self.topic,
            conversation_history=history,
            api_keys={}
        )
        self.assertEqual(next_speaker_nom, 2)

        # 3. Nomination without mention: Fallbacks to sequential (index 1)
        next_speaker_nom_fallback = get_next_speaker(
            mode="Nomination",
            current_index=0,
            agents=self.agents,
            last_message_text="這是一個好問題。",
            topic=self.topic,
            conversation_history=history,
            api_keys={}
        )
        self.assertEqual(next_speaker_nom_fallback, 1)

    def test_transcript_formatting(self):
        """Test export transcript formatting matches user requirement."""
        history = [
            {"name": "阿明", "role": "得道高僧", "text": "大德所言甚是。", "model_provider": "Gemini"},
            {"name": "老張", "role": "冷靜理性的經濟學家", "text": "從成本效益來看，我不同意。", "model_provider": "OpenAI"}
        ]
        
        formatted = format_transcript(self.topic, self.agents, history)
        
        # Top shows topic
        self.assertTrue(formatted.startswith(f"# 聊天主題：{self.topic}"))
        
        # Each AI's role is listed in header
        self.assertIn("得道高僧", formatted)
        self.assertIn("未來主義者", formatted)
        self.assertIn("冷靜理性的經濟學家", formatted)
        
        # Each message shows the sender's name, role, and provider attribution
        self.assertIn("[阿明 (得道高僧 | 來自 Gemini)]: 大德所言甚是。", formatted)
        self.assertIn("[老張 (冷靜理性的經濟學家 | 來自 OpenAI)]: 從成本效益來看，我不同意。", formatted)

    @patch('google.generativeai.GenerativeModel')
    @patch('google.generativeai.configure')
    def test_gemini_api_call(self, mock_configure, mock_gen_model):
        """Test Gemini API client integrates correctly under mock."""
        # Setup mock model response
        mock_model_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "這是模擬的 Gemini 回覆。"
        mock_model_instance.generate_content.return_value = mock_response
        mock_gen_model.return_value = mock_model_instance
        
        agent = AIAgent(0, "小明", "哲學家", "Gemini", "gemini-2.5-flash")
        api_keys = {"gemini": "test-gemini-key"}
        
        result = agent.get_response(self.topic, [], [agent], api_keys)
        
        # Verify result and call logic
        self.assertEqual(result, "這是模擬的 Gemini 回覆。")
        mock_configure.assert_called_once_with(api_key="test-gemini-key")
        mock_gen_model.assert_called_once_with(model_name="gemini-2.5-flash", system_instruction=unittest.mock.ANY)

    @patch('openai.resources.chat.completions.Completions.create')
    @patch('openai.OpenAI')
    def test_openai_api_call(self, mock_openai_client, mock_create):
        """Test OpenAI API client integrates correctly under mock."""
        # Setup mock completion
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "這是模擬的 OpenAI 回覆。"
        mock_create.return_value = mock_response
        
        # Setup OpenAI instance mock behavior
        mock_client_instance = MagicMock()
        mock_client_instance.chat.completions.create = mock_create
        mock_openai_client.return_value = mock_client_instance
        
        agent = AIAgent(0, "小明", "哲學家", "OpenAI", "gpt-4o-mini")
        api_keys = {"openai": "test-openai-key"}
        
        result = agent.get_response(self.topic, [], [agent], api_keys)
        
        self.assertEqual(result, "這是模擬的 OpenAI 回覆。")
        mock_openai_client.assert_called_once_with(api_key="test-openai-key")
        mock_create.assert_called_once_with(
            model="gpt-4o-mini",
            messages=unittest.mock.ANY,
            max_tokens=250
        )

    @patch('openai.resources.chat.completions.Completions.create')
    @patch('openai.OpenAI')
    def test_grok_api_call(self, mock_openai_client, mock_create):
        """Test Grok API client integrates correctly under mock."""
        # Setup mock completion
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "這是模擬的 Grok 回覆。"
        mock_create.return_value = mock_response
        
        # Setup OpenAI instance mock behavior
        mock_client_instance = MagicMock()
        mock_client_instance.chat.completions.create = mock_create
        mock_openai_client.return_value = mock_client_instance
        
        agent = AIAgent(0, "小明", "哲學家", "Grok", "grok-2-1212")
        api_keys = {"grok": "test-grok-key"}
        
        result = agent.get_response(self.topic, [], [agent], api_keys)
        
        self.assertEqual(result, "這是模擬的 Grok 回覆。")
        mock_openai_client.assert_called_once_with(api_key="test-grok-key", base_url="https://api.x.ai/v1")
        mock_create.assert_called_once_with(
            model="grok-2-1212",
            messages=unittest.mock.ANY,
            max_tokens=250
        )

    @patch('openai.resources.chat.completions.Completions.create')
    @patch('openai.OpenAI')
    def test_groq_api_call(self, mock_openai_client, mock_create):
        """Test Groq API client integrates correctly under mock."""
        # Setup mock completion
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "這是模擬的 Groq 回覆。"
        mock_create.return_value = mock_response
        
        # Setup OpenAI instance mock behavior
        mock_client_instance = MagicMock()
        mock_client_instance.chat.completions.create = mock_create
        mock_openai_client.return_value = mock_client_instance
        
        agent = AIAgent(0, "小明", "哲學家", "Groq", "gemma2-9b-it")
        api_keys = {"groq": "test-groq-key"}
        
        result = agent.get_response(self.topic, [], [agent], api_keys)
        
        self.assertEqual(result, "這是模擬的 Groq 回覆。")
        mock_openai_client.assert_called_once_with(api_key="test-groq-key", base_url="https://api.groq.com/openai/v1")
        mock_create.assert_called_once_with(
            model="gemma2-9b-it",
            messages=unittest.mock.ANY,
            max_tokens=250
        )

    @patch('openai.resources.chat.completions.Completions.create')
    @patch('openai.OpenAI')
    def test_github_api_call(self, mock_openai_client, mock_create):
        """Test GitHub Models API client integrates correctly under mock."""
        # Setup mock completion
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "這是模擬的 GitHub 回覆。"
        mock_create.return_value = mock_response
        
        # Setup OpenAI instance mock behavior
        mock_client_instance = MagicMock()
        mock_client_instance.chat.completions.create = mock_create
        mock_openai_client.return_value = mock_client_instance
        
        agent = AIAgent(0, "小明", "哲學家", "GitHub", "gpt-4o-mini")
        api_keys = {"github": "test-github-key"}
        
        result = agent.get_response(self.topic, [], [agent], api_keys)
        
        self.assertEqual(result, "這是模擬的 GitHub 回覆。")
        mock_openai_client.assert_called_once_with(api_key="test-github-key", base_url="https://models.github.ai/inference")
        mock_create.assert_called_once_with(
            model="gpt-4o-mini",
            messages=unittest.mock.ANY,
            max_tokens=250
        )

    @patch('openai.resources.chat.completions.Completions.create')
    @patch('openai.OpenAI')
    def test_ollama_api_call(self, mock_openai_client, mock_create):
        """Test Ollama API client integrates correctly under mock."""
        # Setup mock completion
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "這是模擬的 Ollama 回覆。"
        mock_create.return_value = mock_response
        
        # Setup OpenAI instance mock behavior
        mock_client_instance = MagicMock()
        mock_client_instance.chat.completions.create = mock_create
        mock_openai_client.return_value = mock_client_instance
        
        agent = AIAgent(0, "小明", "哲學家", "Ollama", "gemma4:latest")
        api_keys = {"ollama": "http://localhost:11434"}
        
        result = agent.get_response(self.topic, [], [agent], api_keys)
        
        self.assertEqual(result, "這是模擬的 Ollama 回覆。")
        mock_openai_client.assert_called_once_with(
            api_key="ollama",
            base_url="http://localhost:11434/v1",
            timeout=120.0
        )
        mock_create.assert_called_once_with(
            model="gemma4:latest",
            messages=unittest.mock.ANY,
            max_tokens=1024,
            extra_body={"think": False}
        )


    @patch('openai.resources.chat.completions.Completions.create')
    @patch('openai.OpenAI')
    def test_orchestrator_ollama(self, mock_openai_client, mock_create):
        """Test orchestrator next speaker selection using Ollama."""
        # Setup mock completion returning "1"
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "1"
        mock_create.return_value = mock_response
        
        # Setup OpenAI client mock behavior
        mock_client_instance = MagicMock()
        mock_client_instance.chat.completions.create = mock_create
        mock_openai_client.return_value = mock_client_instance
        
        api_keys = {"ollama": "http://localhost:11434"}
        
        next_speaker = get_next_speaker(
            mode="Orchestrator",
            current_index=0,
            agents=self.agents,
            last_message_text="今天天氣很好。",
            topic=self.topic,
            conversation_history=[],
            api_keys=api_keys
        )
        
        self.assertEqual(next_speaker, 1)
        mock_openai_client.assert_called_once_with(api_key="ollama", base_url="http://localhost:11434/v1")

    @patch('google.generativeai.list_models')
    @patch('google.generativeai.configure')
    def test_verify_api_key_gemini(self, mock_configure, mock_list_models):
        # 1. Success case
        mock_list_models.return_value = ["model1"]
        success, msg = verify_api_key("Gemini", "valid-key")
        self.assertTrue(success)
        self.assertEqual(msg, "驗證成功")
        mock_configure.assert_called_with(api_key="valid-key")

        # 2. Failure case
        mock_list_models.side_effect = Exception("Invalid Key")
        success, msg = verify_api_key("Gemini", "invalid-key")
        self.assertFalse(success)
        self.assertIn("Invalid Key", msg)

    @patch('openai.OpenAI')
    def test_verify_api_key_openai(self, mock_openai_client):
        # 1. Success case
        mock_client_instance = MagicMock()
        mock_openai_client.return_value = mock_client_instance
        success, msg = verify_api_key("OpenAI", "valid-key")
        self.assertTrue(success)
        self.assertEqual(msg, "驗證成功")
        mock_openai_client.assert_called_with(api_key="valid-key")
        mock_client_instance.models.list.assert_called_once()

        # 2. Failure case
        mock_client_instance.models.list.side_effect = Exception("Invalid Key")
        success, msg = verify_api_key("OpenAI", "invalid-key")
        self.assertFalse(success)
        self.assertIn("Invalid Key", msg)

    @patch('anthropic.Anthropic')
    def test_verify_api_key_claude(self, mock_anthropic_client):
        # 1. Success case
        mock_client_instance = MagicMock()
        mock_anthropic_client.return_value = mock_client_instance
        success, msg = verify_api_key("Claude", "valid-key")
        self.assertTrue(success)
        self.assertEqual(msg, "驗證成功")
        mock_anthropic_client.assert_called_with(api_key="valid-key")
        mock_client_instance.messages.create.assert_called_once_with(
            model="claude-3-5-haiku-20241022",
            max_tokens=1,
            messages=[{"role": "user", "content": "Ping"}]
        )

        # 2. Failure case
        mock_client_instance.messages.create.side_effect = Exception("Authentication failed")
        success, msg = verify_api_key("Claude", "invalid-key")
        self.assertFalse(success)
        self.assertIn("Authentication failed", msg)

    @patch('openai.OpenAI')
    def test_verify_api_key_deepseek(self, mock_openai_client):
        # 1. Success case
        mock_client_instance = MagicMock()
        mock_openai_client.return_value = mock_client_instance
        success, msg = verify_api_key("DeepSeek", "valid-key")
        self.assertTrue(success)
        self.assertEqual(msg, "驗證成功")
        mock_openai_client.assert_called_with(api_key="valid-key", base_url="https://api.deepseek.com")
        mock_client_instance.models.list.assert_called_once()

        # 2. Failure case
        mock_client_instance.models.list.side_effect = Exception("Invalid DeepSeek Key")
        success, msg = verify_api_key("DeepSeek", "invalid-key")
        self.assertFalse(success)
        self.assertIn("Invalid DeepSeek Key", msg)

    @patch('openai.OpenAI')
    def test_verify_api_key_grok(self, mock_openai_client):
        # 1. Success case
        mock_client_instance = MagicMock()
        mock_openai_client.return_value = mock_client_instance
        success, msg = verify_api_key("Grok", "valid-key")
        self.assertTrue(success)
        self.assertEqual(msg, "驗證成功")
        mock_openai_client.assert_called_with(api_key="valid-key", base_url="https://api.x.ai/v1")
        mock_client_instance.models.list.assert_called_once()

        # 2. Failure case
        mock_client_instance.models.list.side_effect = Exception("Invalid Grok Key")
        success, msg = verify_api_key("Grok", "invalid-key")
        self.assertFalse(success)
        self.assertIn("Invalid Grok Key", msg)

    @patch('openai.OpenAI')
    def test_verify_api_key_groq(self, mock_openai_client):
        # 1. Success case
        mock_client_instance = MagicMock()
        mock_openai_client.return_value = mock_client_instance
        success, msg = verify_api_key("Groq", "valid-key")
        self.assertTrue(success)
        self.assertEqual(msg, "驗證成功")
        mock_openai_client.assert_called_with(api_key="valid-key", base_url="https://api.groq.com/openai/v1")
        mock_client_instance.models.list.assert_called_once()

        # 2. Failure case
        mock_client_instance.models.list.side_effect = Exception("Invalid Groq Key")
        success, msg = verify_api_key("Groq", "invalid-key")
        self.assertFalse(success)
        self.assertIn("Invalid Groq Key", msg)

    @patch('openai.OpenAI')
    def test_verify_api_key_github(self, mock_openai_client):
        # 1. Success case
        mock_client_instance = MagicMock()
        mock_openai_client.return_value = mock_client_instance
        success, msg = verify_api_key("GitHub", "valid-key")
        self.assertTrue(success)
        self.assertEqual(msg, "驗證成功")
        mock_openai_client.assert_called_with(api_key="valid-key", base_url="https://models.github.ai/inference")
        mock_client_instance.chat.completions.create.assert_called_once_with(
            model="gpt-4o-mini",
            max_tokens=1,
            messages=[{"role": "user", "content": "Ping"}]
        )

        # 2. Failure case
        mock_client_instance.chat.completions.create.side_effect = Exception("Invalid GitHub Token")
        success, msg = verify_api_key("GitHub", "invalid-key")
        self.assertFalse(success)
        self.assertIn("Invalid GitHub Token", msg)

    @patch('urllib.request.urlopen')
    def test_verify_api_key_ollama_success(self, mock_urlopen):
        # 1. Success case
        mock_response = MagicMock()
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        success, msg = verify_api_key("Ollama", "http://localhost:11434")
        self.assertTrue(success)
        self.assertEqual(msg, "驗證成功")

    @patch('urllib.request.urlopen')
    def test_verify_api_key_ollama_failure(self, mock_urlopen):
        # 2. Failure case (bad status)
        mock_response = MagicMock()
        mock_response.status = 500
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        success, msg = verify_api_key("Ollama", "http://localhost:11434")
        self.assertFalse(success)
        self.assertIn("Ollama 回傳錯誤代碼: 500", msg)

        # 3. Connection exception case
        mock_urlopen.side_effect = Exception("Connection refused")
        success, msg = verify_api_key("Ollama", "http://localhost:11434")
        self.assertFalse(success)
        self.assertIn("無法連線至 Ollama", msg)

    def test_app_syntax(self):
        """Verify app.py has correct syntax using py_compile."""
        import py_compile
        try:
            py_compile.compile('app.py', doraise=True)
            self.assertTrue(True)
        except py_compile.PyCompileError as e:
            self.fail(f"app.py has syntax errors: {str(e)}")



if __name__ == '__main__':
    unittest.main()
