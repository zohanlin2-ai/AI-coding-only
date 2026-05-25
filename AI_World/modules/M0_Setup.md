# Module M0：環境設定與 Ollama Benchmark

## 你的任務

偵測本機 Ollama 安裝狀態、讓使用者選擇模型並執行 benchmark，依測量結果產出 `config.json` 到 `AI_World/` 根目錄，供所有其他模組讀取。

---

## 負責範圍

- **負責：**
  - 呼叫 Ollama API 列出已安裝的模型
  - 讓使用者從清單中選擇模型
  - 對選定模型發送 3 個測試 prompt，**實際計時**每次回應（不可假造數據）
  - 計算平均回應時間（`avg_response_time_sec`）與 tokens/sec（`tokens_per_sec`）
  - 依速度推薦 `MAX_AGENTS` 數量，並允許使用者手動覆寫
  - 產出 `config.json` 並儲存到 `AI_World/` 根目錄

- **不負責：**
  - 安裝 Ollama 本身（請使用者自行安裝）
  - 初始化世界資料庫（M1 負責）
  - 建立 Agent（M2 負責）
  - 任何 config.json 以外的持久化儲存

---

## 依賴關係

- **需要先完成：** 無（M0 是第一個執行的模組）
- **被以下模組使用：** M1、M2、M3、M4、M5、M6、M7、M8（所有模組都從 `config.json` 讀取設定）

---

## 工作目錄

```
c:\Users\zohanlin\Documents\zohan_ai_test\AI_World\modules\m0_setup\
```

---

## 環境安裝

```bash
pip install requests pydantic
```

> **注意：** 執行前請確認 Ollama 已安裝並在背景執行（`ollama serve`）。
> 若尚未安裝，請至 https://ollama.com 下載。

---

## 需要建立的檔案

```
AI_World/
├── config.json                  ← 本模組執行後產出（輸出到根目錄）
└── modules/
    └── m0_setup/
        └── main.py              ← 本模組唯一需要撰寫的檔案
```

---

## 共用 Schema（直接使用，不可修改）

> 來源：`AI_World_Architecture.md`。M0 本身不需要 `import shared.schemas`，但產出的 `config.json` 必須完全符合以下 `Config` schema 的欄位定義。

```python
# shared/schemas.py 中的 Config class（僅供對照，不需 import）
from pydantic import BaseModel

class Config(BaseModel):
    ollama_model: str
    ollama_base_url: str = "http://localhost:11434"
    avg_response_time_sec: float
    tokens_per_sec: float
    recommended_max_agents: int
    tick_interval_sec: int
    concurrency_mode: str = "sequential"   # "sequential" | "async"
    max_concurrent_requests: int = 1
```

### config.json 完整格式範例

```json
{
  "ollama_model": "gemma3:4b",
  "ollama_base_url": "http://localhost:11434",
  "avg_response_time_sec": 3.2,
  "tokens_per_sec": 45.0,
  "recommended_max_agents": 6,
  "tick_interval_sec": 30,
  "concurrency_mode": "sequential",
  "max_concurrent_requests": 1
}
```

**欄位型別要求：**

| 欄位 | 型別 | 說明 |
|------|------|------|
| `ollama_model` | `str` | 使用者選擇的模型名稱，例如 `"gemma3:4b"` |
| `ollama_base_url` | `str` | 固定為 `"http://localhost:11434"` |
| `avg_response_time_sec` | `float` | benchmark 平均回應時間（秒），四捨五入到小數點後 2 位 |
| `tokens_per_sec` | `float` | 平均 tokens/sec，四捨五入到小數點後 2 位 |
| `recommended_max_agents` | `int` | 依速度推薦的最大 Agent 數，使用者可覆寫 |
| `tick_interval_sec` | `int` | 固定為 `30`（此欄位由 M0 寫入，其他模組讀取） |
| `concurrency_mode` | `str` | 固定為 `"sequential"` |
| `max_concurrent_requests` | `int` | 固定為 `1` |

---

## 你對外提供的函數（簽名不可修改）

> M0 為一次性執行腳本，**不對外暴露函數**。
> 其他模組只需讀取 M0 產出的 `config.json`，不會直接 `import` M0 的任何函數。

---

## 你可以呼叫的外部函數

> M0 不依賴其他模組的函數。
> M0 只與 **Ollama REST API** 直接溝通：

| Endpoint | Method | 說明 |
|----------|--------|------|
| `http://localhost:11434/api/tags` | `GET` | 列出本機已安裝的所有模型 |
| `http://localhost:11434/api/generate` | `POST` | 向指定模型發送 prompt 並取得回應 |

**`/api/tags` 回應格式（簡化）：**
```json
{
  "models": [
    { "name": "gemma3:4b", "size": 2637211648 },
    { "name": "llama3.2:3b", "size": 1234567890 }
  ]
}
```

**`/api/generate` 請求格式：**
```json
{
  "model": "gemma3:4b",
  "prompt": "你好，請用一句話介紹自己。",
  "stream": false
}
```

**`/api/generate` 回應格式（簡化）：**
```json
{
  "response": "我是一個語言模型...",
  "eval_count": 42,
  "eval_duration": 1234567890
}
```

> `eval_count`：本次回應產生的 token 數量
> `eval_duration`：本次回應的 LLM 推理時間（單位：奈秒 ns）

---

## 實作步驟

### Step 1：從 Ollama 取得已安裝模型清單

```python
import requests

OLLAMA_BASE_URL = "http://localhost:11434"

def list_models() -> list[str]:
    """
    呼叫 GET /api/tags，回傳模型名稱列表。
    若 Ollama 未啟動或無法連線，印出友善錯誤訊息後 exit(1)。
    """
    # TODO: 呼叫 requests.get(f"{OLLAMA_BASE_URL}/api/tags")
    # TODO: 解析 response.json()["models"]，提取每個模型的 "name" 欄位
    # TODO: 若 models 列表為空，提示使用者先執行 `ollama pull <model>` 後 exit(1)
    # TODO: 回傳 list[str]
    pass
```

---

### Step 2：讓使用者選擇模型

```python
def select_model(models: list[str]) -> str:
    """
    印出模型清單（附編號），讓使用者輸入編號選擇。
    驗證輸入合法後回傳選定的模型名稱。
    """
    # TODO: 用 enumerate 印出 "1. gemma3:4b"、"2. llama3.2:3b" 格式的清單
    # TODO: 用 input() 等待使用者輸入編號
    # TODO: 驗證輸入是有效整數且在範圍內，無效則重新詢問
    # TODO: 回傳 models[選擇索引]
    pass
```

---

### Step 3：執行 Benchmark（實際計時，禁止假造數據）

```python
import time

BENCHMARK_PROMPTS = [
    "請用繁體中文，一句話描述你所在的世界。",
    "現在是春天，你感覺如何？請用一句話回答。",
    "你的名字叫什麼？你最想做的事是什麼？請簡短回答。",
]

def benchmark_model(model_name: str) -> dict:
    """
    對指定模型依序發送 BENCHMARK_PROMPTS 中的 3 個 prompt。
    每次均使用 time.time() 實際計時（wall clock time）。
    回傳包含以下資訊的 dict：
    {
        "avg_response_time_sec": float,  # 3 次回應的平均時間（秒）
        "tokens_per_sec": float,         # 平均 tokens/sec（使用 eval_count 與 eval_duration）
        "raw_results": [                 # 每次 benchmark 的原始資料（供除錯）
            {
                "prompt": str,
                "response_time_sec": float,
                "eval_count": int,
                "eval_duration_ns": int,
                "response_preview": str  # 回應前 50 字
            },
            ...
        ]
    }
    """
    # TODO: 建立空列表 results = []
    # TODO: 對每個 prompt 執行以下流程：
    #   1. 記錄 start = time.time()
    #   2. 呼叫 POST /api/generate，payload = {"model": model_name, "prompt": prompt, "stream": False}
    #   3. 記錄 elapsed = time.time() - start
    #   4. 從 response.json() 取出 eval_count 與 eval_duration（奈秒）
    #   5. 計算此次 tokens_per_sec = eval_count / (eval_duration / 1e9)
    #   6. 將結果 append 到 results
    #   7. 印出進度，例如 "[1/3] 回應時間：2.34 秒，tokens/sec：45.2"
    # TODO: 計算 avg_response_time_sec = mean(所有 response_time_sec)
    # TODO: 計算 tokens_per_sec = mean(所有單次 tokens_per_sec)
    # TODO: 回傳 dict
    pass
```

---

### Step 4：依速度推薦 MAX_AGENTS

```python
def recommend_max_agents(avg_response_time_sec: float) -> int:
    """
    依平均回應時間推薦最大 Agent 數量：
      < 2 秒  → 推薦 10
      2~5 秒  → 推薦 6
      5~10 秒 → 推薦 3
      > 10 秒 → 推薦 1
    回傳推薦的整數值。
    """
    # TODO: 用 if/elif/else 實作上述邏輯
    pass
```

---

### Step 5：讓使用者確認或修改推薦數量

```python
def confirm_max_agents(recommended: int) -> int:
    """
    顯示推薦的 max_agents，讓使用者確認（按 Enter）或輸入自訂數字。
    驗證輸入為正整數，無效則重新詢問。
    回傳最終確認的整數值。
    """
    # TODO: 印出 f"推薦 MAX_AGENTS = {recommended}（按 Enter 確認，或輸入自訂數字）："
    # TODO: 取得 user_input = input().strip()
    # TODO: 若 user_input 為空，回傳 recommended
    # TODO: 嘗試 int(user_input)，驗證 > 0，無效則重新詢問
    # TODO: 回傳最終值
    pass
```

---

### Step 6：產出並儲存 config.json

```python
import json
import os

# config.json 輸出到 AI_World/ 根目錄（main.py 的上兩層）
CONFIG_OUTPUT_PATH = os.path.join(
    os.path.dirname(__file__),  # m0_setup/
    "..",                        # modules/
    "..",                        # AI_World/
    "config.json"
)

def save_config(
    model_name: str,
    avg_response_time_sec: float,
    tokens_per_sec: float,
    max_agents: int,
) -> None:
    """
    建立 config dict，寫入 JSON 檔案到 CONFIG_OUTPUT_PATH。
    欄位值必須完全符合 Config schema，數值四捨五入到小數點後 2 位。
    """
    config = {
        "ollama_model": model_name,
        "ollama_base_url": "http://localhost:11434",
        "avg_response_time_sec": round(avg_response_time_sec, 2),
        "tokens_per_sec": round(tokens_per_sec, 2),
        "recommended_max_agents": max_agents,
        "tick_interval_sec": 30,
        "concurrency_mode": "sequential",
        "max_concurrent_requests": 1,
    }
    # TODO: 用 json.dump 寫入 CONFIG_OUTPUT_PATH，ensure_ascii=False，indent=2
    # TODO: 印出成功訊息，包含檔案的絕對路徑（os.path.abspath(CONFIG_OUTPUT_PATH)）
    pass
```

---

### Step 7：主程式入口

```python
def main():
    """
    整合所有步驟的主流程：
    1. list_models()
    2. select_model()
    3. benchmark_model()（印出進度）
    4. recommend_max_agents()
    5. confirm_max_agents()
    6. save_config()
    7. 印出完成摘要
    """
    print("=" * 50)
    print("  AI World — M0 環境設定與 Benchmark")
    print("=" * 50)

    # TODO: 依序呼叫 Step 1 ~ Step 6 的函數
    # TODO: 最後印出摘要，例如：
    #   模型：gemma3:4b
    #   平均回應時間：3.24 秒
    #   Tokens/sec：45.20
    #   MAX_AGENTS：6
    #   Config 已儲存至：C:\...\AI_World\config.json
    pass


if __name__ == "__main__":
    main()
```

---

## 執行方式

在 `AI_World/` 根目錄下執行（以確保相對路徑正確）：

```bash
cd c:\Users\zohanlin\Documents\zohan_ai_test\AI_World
python modules/m0_setup/main.py
```

或直接在 `m0_setup/` 目錄下執行：

```bash
cd c:\Users\zohanlin\Documents\zohan_ai_test\AI_World\modules\m0_setup
python main.py
```

---

## 驗證標準（全部通過才算完成）

- [ ] `AI_World/config.json` 存在且可被 `json.load()` 正常解析
- [ ] `config.json` 包含以下所有欄位，型別完全符合 schema：
  - `ollama_model`（str）
  - `ollama_base_url`（str，值為 `"http://localhost:11434"`）
  - `avg_response_time_sec`（float）
  - `tokens_per_sec`（float）
  - `recommended_max_agents`（int）
  - `tick_interval_sec`（int，值為 `30`）
  - `concurrency_mode`（str，值為 `"sequential"`）
  - `max_concurrent_requests`（int，值為 `1`）
- [ ] 程式能成功呼叫 `GET /api/tags` 並列出模型（Ollama 需事先啟動）
- [ ] Benchmark 確實呼叫 LLM 3 次並計時，`avg_response_time_sec` 為真實測量值（非 hardcode）
- [ ] `tokens_per_sec` 基於 Ollama API 回傳的 `eval_count` 與 `eval_duration` 計算，非估算
- [ ] 使用者可在 Step 5 輸入自訂數字覆寫 `recommended_max_agents`，覆寫後的數值會正確寫入 `config.json`
- [ ] 輸入非法值（非數字、負數、超出範圍的索引）時，程式提示錯誤並重新詢問，不 crash
- [ ] Ollama 未啟動時，程式印出友善錯誤訊息（不是 Python traceback）後退出

---

## 常見問題

**Q：Ollama API 的 `eval_duration` 單位是什麼？**
A：奈秒（nanoseconds）。換算成秒：`eval_duration / 1e9`。

**Q：tokens/sec 要怎麼計算？**
A：使用 Ollama 回傳的 `eval_count`（token 數）除以 `eval_duration / 1e9`（秒）。
若 `eval_duration` 為 0 或缺失，則 fallback 使用 wall clock time（`response_time_sec`）作分母。

**Q：`CONFIG_OUTPUT_PATH` 路徑若在 Windows 上有反斜線問題怎麼辦？**
A：使用 `os.path.join()` 與 `os.path.abspath()` 處理，不要硬寫路徑字串。

**Q：benchmark prompt 可以改嗎？**
A：可以，但必須至少發送 3 個 prompt 並對回應時間取平均，且所有 prompt 必須要求 LLM 實際生成文字（不可使用空字串或導致 0 token 的 prompt）。
