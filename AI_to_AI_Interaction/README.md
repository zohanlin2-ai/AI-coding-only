# 🌌 AI-to-AI 對話觀測站 (AI-to-AI Dialogue Observer)

這是一個基於 Python 與 Streamlit 開發的互動式 Web 應用程式。使用者可以配置 1 到 4 個 AI 角色，給定任意對話主題，設定其角色定位與說話語氣，並即時觀測 AI 彼此之間的思想碰撞與交談。

## 🌟 核心特色
1. **靈活的角色數量**：支援 1 至 4 個 AI 同時對談。可以是一個 AI 的自我詰問，或是多個 AI 的群聊辯論。
2. **完全自訂的主題與人設**：自由輸入對話主題，並個別為各個 AI 命名與設定詳細的人設（例如：「極度悲觀的末日預言者」、「冷靜理性的經濟學家」）。
3. **隨機補全與生成**：若主題或 AI 角色欄位留空，系統將自動從精心設計的隨機庫（繁體中文）中抽選，甚至可一鍵隨機重設所有配置。
4. **多模型支援**：整合各大主流模型：
   - **Google Gemini** (預設 `gemini-2.5-flash`)
   - **OpenAI** (預設 `gpt-4o-mini`)
   - **Anthropic Claude** (預設 `claude-3-5-sonnet`)
   - **DeepSeek** (預設 `deepseek-chat`)
   - **xAI Grok** (預設 `grok-2-1212`)
   - **Groq Cloud** (預設 `gemma2-9b-it`)
   - **GitHub Models** (預設 `gpt-4o-mini`)
   - **Ollama 本地端 AI** (預設 `gemma4:latest`，可自訂 API 位址，特別針對思考模型優化)
   - **Mock 模式**：完全不需要 API 金鑰與網路連線，透過隨機模板拼接產生生動、擬真的模擬對話，方便調試與測試。
5. **對話時間控制**：可設定對話時長（1 至 120 分鐘）與發言間隔（1 至 15 秒），提供即時倒數計時與進度條，並可隨時手動終止對話。
6. **三種發言順序邏輯**：
   - **輪流模式 (Sequential)**：AI 按順序輪流發言。
   - **點名接力模式 (Nomination)**：AI 在發言最後可使用 `@角色` 指名下一位發言者。若無點名，則自動由下一個接力。
   - **中央協調模式 (Orchestrator)**：每次發言完畢後，由主控大模型根據當前對話上下文決定最適合接話的 AI。
7. **對話來源標註**：每個角色的對話氣泡與匯出的 Markdown 記錄，皆會明確註明發言來自哪一個 AI 提供商（例如：`來自 OpenAI` 或 `來自 Grok`）。
8. **驗證失敗自動過濾**：當進行 API Key 驗證失敗後，該模型提供商會自動被排除於下拉式選單之外，若原本已被選取，將安全降級為 Mock 模式，確保對話穩定運行。
9. **一鍵匯出儲存**：對話結束後，可點選下載 Markdown (.md) 對話紀錄。內容頂部明確標記對話主題、各個 AI 的模型與角色設定，且每句對話皆標示發言的 AI 名稱、角色與所屬的 AI 提供商。

---

## 🛠️ 快速開始

### 1. 安裝環境與依賴項目
確保您的系統已安裝 Python 3.10+，並於終端機執行：
```bash
pip install -r requirements.txt
```

### 2. 設定 API 金鑰 (選用)
您有兩種方式設定 API 金鑰：
- **方式 A (UI 直接輸入)**：在啟動應用程式後的側邊欄中，直接輸入各模型的 API Key。輸入後可點選「驗證 [AI] 金鑰」按鈕，系統會同步連線該 AI 提供商以驗證金鑰的有效性（連線狀態會即時呈現：🟢 驗證成功、🟡 已配置 (未驗證)、🔴 未配置、❌ 驗證失敗，並在失敗時顯示錯誤原因，且驗證失敗後該 AI 將無法被選取）。
- **方式 B (環境變數)**：在專案根目錄下建立 `.env` 檔案，並填入以下內容：
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

### 3. 啟動應用程式
在終端機中執行：
```bash
streamlit run app.py
```
啟動後會自動開啟瀏覽器視窗（預設網址為 `http://localhost:8501`）。

---

## 🧪 執行單元測試
本專案包含完整的自動化測試套件（基於 Python 的 `unittest`），用以評估並驗證 Mock AI 生成、隨機補全邏輯、正則表達式點名解析、順序協調、API 調用 Mock 與存檔格式。

於專案根目錄執行：
```bash
python -m unittest test_app.py
```

---

## 📂 專案檔案結構
- [app.py](file:///c:/Users/zohanlin/Documents/zohan_ai_test/AI_to_AI_Interaction/app.py): Streamlit 網頁 UI 主要入口與即時運行迴圈。
- [ai_agent.py](file:///c:/Users/zohanlin/Documents/zohan_ai_test/AI_to_AI_Interaction/ai_agent.py): AI 角色邏輯封裝、API 呼叫與 Mock 生成器。
- [orchestrator.py](file:///c:/Users/zohanlin/Documents/zohan_ai_test/AI_to_AI_Interaction/orchestrator.py): 點名解析與下一步發言順序決定機制。
- [test_app.py](file:///c:/Users/zohanlin/Documents/zohan_ai_test/AI_to_AI_Interaction/test_app.py): 單元測試。
- [CLAUDE.md](file:///c:/Users/zohanlin/Documents/zohan_ai_test/AI_to_AI_Interaction/CLAUDE.md): AI 助理開發指南與指令說明。
- [requirements.txt](file:///c:/Users/zohanlin/Documents/zohan_ai_test/AI_to_AI_Interaction/requirements.txt): 依賴庫清單。
