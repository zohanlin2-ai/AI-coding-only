# Module M2：Agent 系統

## 你的任務

建立並管理 AI Agent，透過 Ollama 本地 LLM 讓每個 Agent 能夠思考（`agent_think`）與行動（`agent_act`），並將行動結果以 `WorldEvent` 的形式寫入 M1 世界狀態。

---

## 負責範圍

- **負責：**
  - 建立 Agent 並存入 M1 世界狀態
  - 組合 Agent 的思考 Prompt 並呼叫 Ollama LLM
  - 解析 LLM 輸出並轉換為合法行動
  - 執行行動（更新資源、位置）並產生 `WorldEvent`
  - 每 tick 更新 Agent 的 `hunger`、`energy` 等需求數值
  - 透過 M5 驗證行動合法性並檢查存活狀態

- **不負責：**
  - 世界狀態的持久化（由 M1 負責）
  - 記憶的向量搜尋與儲存底層（由 M3 負責）
  - 多 Agent 之間的互動排程（由 M4 負責）
  - 規則的定義與套用（由 M5 負責）
  - 時間推進（由 M6 負責）

---

## 依賴關係

- **需要先完成：**
  - M0（`config.json` 必須存在）
  - M1（`get_world_state`、`update_agent`、`add_event` 必須可呼叫）
  - M3（`get_recent_memory`、`save_memory` 必須可呼叫）
  - M5（`validate_action`、`check_survival` 必須可呼叫）

- **被以下模組使用：**
  - M4（呼叫 `agent_think`、`agent_act`、`list_agents`）
  - M8（整合測試）

---

## 工作目錄

```
c:\Users\zohanlin\Documents\zohan_ai_test\AI_World\modules\m2_agent\
```

> **注意**：所有 `import` 路徑皆以 `AI_World/` 為根目錄執行，例如：
> ```bash
> # 在 AI_World/ 目錄下執行
> python -m modules.m2_agent.main
> ```

---

## 環境安裝

```bash
pip install requests pydantic
```

> `requests` 用於呼叫 Ollama HTTP API；`pydantic` 用於 Schema 驗證。  
> Ollama 本體需另外安裝，請至 https://ollama.ai 下載並確保 `ollama serve` 正在運行。

---

## 需要建立的檔案

```
AI_World/
└── modules/
    └── m2_agent/
        ├── __init__.py     ← 空檔，讓 Python 認識此為 package
        ├── main.py         ← 對外函數（模組介面）
        └── llm_client.py   ← Ollama HTTP API 呼叫封裝
```

---

## 共用 Schema（直接使用，不可修改）

> 所有 Schema 定義於 `AI_World/shared/schemas.py`。  
> 在你的程式碼中一律使用 `from shared.schemas import ...`，**不可自行定義**相同 class。

以下是 M2 會用到的 Schema，供參考：

```python
# shared/schemas.py（節錄，完整版請見 AI_World_Architecture.md）

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid


def gen_id() -> str:
    return str(uuid.uuid4())[:8]


class Resource(BaseModel):
    food: float = 100.0
    water: float = 100.0
    energy: float = 100.0
    money: float = 100.0
    materials: float = 50.0


class AgentPersonality(BaseModel):
    hunger: float = 0.3      # 0.0~1.0，越高越餓
    fear: float = 0.3        # 0.0~1.0，越高越恐懼
    ambition: float = 0.5    # 0.0~1.0，越高越有野心
    loyalty: float = 0.5     # 0.0~1.0，越高越忠誠
    aggression: float = 0.3  # 0.0~1.0，越高越好戰


class Agent(BaseModel):
    id: str = Field(default_factory=gen_id)
    name: str
    location_id: str
    personality: AgentPersonality = Field(default_factory=AgentPersonality)
    resources: Resource = Field(default_factory=Resource)
    skills: dict[str, float] = Field(default_factory=dict)
    relationships: dict[str, float] = Field(default_factory=dict)  # agent_id -> -1.0~1.0
    memory_ids: list[str] = Field(default_factory=list)
    organization_id: Optional[str] = None
    is_alive: bool = True
    age: int = 0  # 單位：tick


class WorldEvent(BaseModel):
    id: str = Field(default_factory=gen_id)
    tick: int
    event_type: str  # "interaction" | "resource" | "conflict" | "discovery" | "death"
    description: str
    affected_agent_ids: list[str] = Field(default_factory=list)
    affected_location_ids: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)


class Config(BaseModel):
    ollama_model: str
    ollama_base_url: str = "http://localhost:11434"
    avg_response_time_sec: float
    tokens_per_sec: float
    recommended_max_agents: int
    tick_interval_sec: int
    concurrency_mode: str = "sequential"
    max_concurrent_requests: int = 1
```

---

## 你對外提供的函數（簽名不可修改）

```python
# modules/m2_agent/main.py

def create_agent(name: str, location_id: str, personality: AgentPersonality) -> Agent:
    """建立新 Agent 並存入世界狀態"""

def get_agent(agent_id: str) -> Agent:
    """取得指定 Agent"""

def agent_think(agent_id: str, context: str) -> str:
    """呼叫 LLM，讓 Agent 根據 context 思考，返回行動描述文字"""

def agent_act(agent_id: str) -> WorldEvent:
    """讓 Agent 執行行動，返回對應的 WorldEvent"""

def update_agent_needs(agent_id: str) -> None:
    """每 tick 更新 Agent 的 hunger、energy 等需求數值"""

def list_agents() -> list[Agent]:
    """列出所有存活的 Agent"""
```

> **重要**：函數名稱、參數型別、回傳型別均**不可更改**。內部實作可自由設計。

---

## 你可以呼叫的外部函數

### 來自 M1（World State Engine）

```python
from modules.m1_world_state.main import (
    get_world_state,   # () -> WorldState：取得完整世界狀態
    update_agent,      # (agent: Agent) -> None：更新 Agent 狀態到資料庫
    add_event,         # (event: WorldEvent) -> None：新增世界事件
    get_tick,          # () -> int：取得當前 tick 數
)
```

### 來自 M3（Memory System）

```python
from modules.m3_memory.main import (
    get_recent_memory, # (agent_id: str, n: int = 10) -> list[str]：最近 n 條記憶
    save_memory,       # (agent_id: str, event: str, importance: float) -> str：儲存記憶
)
```

### 來自 M5（Rules Engine）

```python
from modules.m5_rules.main import (
    validate_action,   # (agent: Agent, action: str) -> tuple[bool, str]：驗證行動合法性
    check_survival,    # (agent: Agent) -> bool：檢查 Agent 是否存活
)
```

---

## Prompt 組合邏輯（`agent_think` 內部使用）

`agent_think` 必須按照以下模板組合 Prompt，再傳給 Ollama：

```
你是 {agent.name}，一個生活在 AI 世界中的角色。
個性：hunger={personality.hunger}, ambition={personality.ambition}, aggression={personality.aggression}
位置：{location.name}（{location.terrain}）
資源：food={resources.food}, money={resources.money}
記憶：{recent_memories}
當前世界狀況：{context}

請用一句話描述你現在要做什麼行動。行動必須是以下之一：
- 採集食物
- 休息
- 移動到 [地點名稱]
- 與 [Agent名稱] 交談
- 交易
- 其他（請說明）
```

**欄位說明：**

| 欄位 | 來源 |
|------|------|
| `agent.name` | `Agent.name` |
| `personality.hunger` | `Agent.personality.hunger` |
| `personality.ambition` | `Agent.personality.ambition` |
| `personality.aggression` | `Agent.personality.aggression` |
| `location.name` | 從 `WorldState.locations[agent.location_id].name` 取得 |
| `location.terrain` | 從 `WorldState.locations[agent.location_id].terrain` 取得 |
| `resources.food` | `Agent.resources.food` |
| `resources.money` | `Agent.resources.money` |
| `recent_memories` | 呼叫 `get_recent_memory(agent_id, n=5)` 並用換行合併 |
| `context` | 直接使用傳入的 `context` 參數 |

---

## 實作步驟

### Step 1：建立 `__init__.py`

```python
# modules/m2_agent/__init__.py
# 空檔，讓 Python 認識此為 package
```

---

### Step 2：實作 `llm_client.py`（Ollama HTTP API 封裝）

Ollama 提供本地 REST API，endpoint 為 `POST /api/generate`。

```python
# modules/m2_agent/llm_client.py

import json
import requests
from shared.schemas import Config  # 引入 Config schema


def load_config() -> Config:
    """
    讀取 AI_World/config.json，返回 Config 物件。
    config.json 由 M0 產生，格式範例：
    {
        "ollama_model": "gemma3:4b",
        "ollama_base_url": "http://localhost:11434",
        ...
    }
    """
    # TODO: 用 open() 讀取 config.json，用 Config(**data) 解析
    pass


def call_ollama(prompt: str, config: Config) -> str:
    """
    呼叫 Ollama /api/generate endpoint，返回 LLM 生成的文字。

    API 說明：
    - URL: {config.ollama_base_url}/api/generate
    - Method: POST
    - Content-Type: application/json
    - Request body:
        {
            "model": "{config.ollama_model}",
            "prompt": "{prompt}",
            "stream": false
        }
    - Response body（stream=false 時）：
        {
            "model": "...",
            "response": "LLM 生成的文字",
            "done": true,
            ...
        }

    錯誤處理：
    - 若連線失敗（requests.exceptions.ConnectionError），拋出例外並說明 Ollama 未啟動
    - 若 HTTP status != 200，拋出例外並附上 status code
    - 若 response 為空字串，拋出例外

    :param prompt: 組合好的 Prompt 字串
    :param config: Config 物件（含 model 名稱與 base_url）
    :return: LLM 回傳的行動描述文字（str）
    """
    url = f"{config.ollama_base_url}/api/generate"

    # TODO: 組合 request body
    payload = {
        # ...
    }

    # TODO: 發送 POST request，取出 response["response"] 並返回
    pass
```

---

### Step 3：實作 `main.py`

```python
# modules/m2_agent/main.py

from shared.schemas import Agent, AgentPersonality, Resource, WorldEvent
from modules.m1_world_state.main import get_world_state, update_agent, add_event, get_tick
from modules.m3_memory.main import get_recent_memory, save_memory
from modules.m5_rules.main import validate_action, check_survival
from modules.m2_agent.llm_client import call_ollama, load_config

# 模組層級快取：儲存各 agent 的「最後思考結果」，供 agent_act 使用
# key: agent_id, value: 行動文字（str）
_last_action: dict[str, str] = {}


def create_agent(name: str, location_id: str, personality: AgentPersonality) -> Agent:
    """
    建立新 Agent 並存入世界狀態。

    實作步驟：
    1. 建立 Agent 物件（id 自動生成，resources 使用預設值）
    2. 呼叫 M1 的 update_agent(agent) 存入資料庫
    3. 返回建立好的 Agent

    注意：location_id 必須是世界狀態中已存在的地點 id。
    """
    # TODO
    pass


def get_agent(agent_id: str) -> Agent:
    """
    從世界狀態取得指定 Agent。

    實作步驟：
    1. 呼叫 get_world_state() 取得 WorldState
    2. 從 world_state.agents[agent_id] 取得 Agent
    3. 若 agent_id 不存在，拋出 KeyError（附上清楚的錯誤訊息）

    :raises KeyError: 若 agent_id 不存在於世界狀態
    """
    # TODO
    pass


def agent_think(agent_id: str, context: str) -> str:
    """
    組合 Prompt，呼叫 Ollama LLM，讓 Agent 思考並返回行動文字。

    實作步驟：
    1. 取得 Agent（呼叫 get_agent）
    2. 取得 WorldState，找到 Agent 所在 Location
    3. 呼叫 get_recent_memory(agent_id, n=5) 取得最近記憶
    4. 按照 Prompt 模板組合 prompt 字串（見「Prompt 組合邏輯」章節）
    5. 呼叫 call_ollama(prompt, config) 取得 LLM 回應
    6. 將回應文字存入 _last_action[agent_id]（供 agent_act 使用）
    7. 返回行動文字

    :param agent_id: 目標 Agent 的 id
    :param context: 當前世界狀況描述（由呼叫方提供，例如 M4）
    :return: LLM 生成的行動描述文字（非空字串）
    """
    # TODO: 組合 prompt
    prompt_template = """你是 {name}，一個生活在 AI 世界中的角色。
個性：hunger={hunger}, ambition={ambition}, aggression={aggression}
位置：{location_name}（{terrain}）
資源：food={food}, money={money}
記憶：{memories}
當前世界狀況：{context}

請用一句話描述你現在要做什麼行動。行動必須是以下之一：
- 採集食物
- 休息
- 移動到 [地點名稱]
- 與 [Agent名稱] 交談
- 交易
- 其他（請說明）"""

    # TODO: 填入 prompt_template，呼叫 call_ollama，儲存並返回結果
    pass


def agent_act(agent_id: str) -> WorldEvent:
    """
    讓 Agent 執行 _last_action 中記錄的行動，更新世界狀態，返回 WorldEvent。

    實作步驟：
    1. 取得 _last_action[agent_id]（若不存在，先呼叫 agent_think 取得行動）
    2. 取得 Agent 物件
    3. 呼叫 validate_action(agent, action) 驗證行動合法性
       - 若不合法，將 action 改為「休息」（fallback 行為）
    4. 根據行動文字執行對應邏輯（解析文字後分支處理）：
       - "採集食物"   → agent.resources.food += 10.0，event_type = "resource"
       - "休息"       → agent.resources.energy = min(100.0, energy + 20.0)，event_type = "resource"
       - "移動到 ..." → 解析目標地點名稱，更新 agent.location_id，event_type = "interaction"
       - "與 ... 交談" → 更新關係值（relationships），event_type = "interaction"
       - "交易"       → 簡單資源交換邏輯，event_type = "resource"
       - 其他         → 僅記錄事件，event_type = "discovery"
    5. 呼叫 check_survival(agent)，若返回 False，設 agent.is_alive = False，event_type = "death"
    6. 呼叫 update_agent(agent) 存回 M1
    7. 建立並返回 WorldEvent，同時呼叫 add_event(event) 寫入世界狀態
    8. 呼叫 save_memory(agent_id, event.description, importance=0.5) 存入記憶

    行動文字解析規則（使用 str.startswith 或 in 判斷）：
    - 包含 "採集食物" → 採集食物
    - 包含 "休息"     → 休息
    - 包含 "移動到"   → 移動（格式：「移動到 {地點名稱}」）
    - 包含 "交談"     → 交談（格式：「與 {Agent名稱} 交談」）
    - 包含 "交易"     → 交易
    - 其他            → 其他

    :param agent_id: 目標 Agent 的 id
    :return: 代表本次行動的 WorldEvent
    """
    # TODO
    pass


def update_agent_needs(agent_id: str) -> None:
    """
    每 tick 呼叫一次，模擬 Agent 自然需求的增加。

    實作步驟：
    1. 取得 Agent
    2. 每次呼叫，依以下規則更新數值：
       - hunger（personality.hunger）增加：+= 0.01，最大值 1.0
         （表示 Agent 越來越餓，hunger 越高代表需求越迫切）
       - energy（resources.energy）減少：-= 2.0，最小值 0.0
         （表示 Agent 隨時間消耗體力）
       - water（resources.water）減少：-= 1.5，最小值 0.0
         （表示 Agent 隨時間消耗水分）
    3. 呼叫 check_survival(agent)，若返回 False，設 agent.is_alive = False
    4. 呼叫 update_agent(agent) 存回 M1

    注意：personality.hunger 是 float，使用 min/max 限制範圍在 0.0~1.0。

    :param agent_id: 目標 Agent 的 id
    """
    # TODO
    pass


def list_agents() -> list[Agent]:
    """
    列出所有存活（is_alive=True）的 Agent。

    實作步驟：
    1. 呼叫 get_world_state() 取得 WorldState
    2. 過濾 world_state.agents.values() 中 is_alive == True 的 Agent
    3. 返回 list

    :return: 所有存活 Agent 的列表
    """
    # TODO
    pass
```

---

### Step 4：行動解析輔助函數（建議放在 `main.py` 內部）

```python
def _parse_action(action_text: str) -> str:
    """
    解析 LLM 回傳的行動文字，返回行動類型。

    :return: "採集食物" | "休息" | "移動" | "交談" | "交易" | "其他"
    """
    # TODO: 使用 in 或 startswith 判斷行動類型
    # 範例：
    # if "採集食物" in action_text:
    #     return "採集食物"
    pass


def _find_location_by_name(location_name: str, world_state) -> str | None:
    """
    根據地點名稱查找 location_id。

    :param location_name: 地點名稱（從 LLM 回傳的行動文字解析出）
    :param world_state: 當前 WorldState
    :return: location_id，若找不到返回 None
    """
    # TODO: 遍歷 world_state.locations，找出 name 匹配的 location
    pass
```

---

## 驗證標準（全部通過才算完成）

- [ ] **`create_agent()` 成功建立 Agent**
  - 呼叫 `create_agent("小明", "<valid_location_id>", AgentPersonality())` 不拋例外
  - 返回的 `Agent` 物件 `.name == "小明"`，`.is_alive == True`
  - 呼叫 `get_world_state().agents` 可找到該 Agent 的 id

- [ ] **`get_agent()` 正確取得 Agent**
  - 以有效 id 呼叫，返回對應 `Agent`
  - 以無效 id 呼叫，拋出 `KeyError`

- [ ] **`agent_think()` 實際呼叫 Ollama 並返回非空文字**
  - 需要 Ollama 服務正在運行（`ollama serve`）且模型已下載
  - 返回的字串長度 > 0
  - 字串內容包含行動描述（包含「採集」「休息」「移動」「交談」「交易」其中之一）
  - `_last_action[agent_id]` 被正確更新

- [ ] **`agent_act()` 返回合法的 `WorldEvent`**
  - 返回物件型別為 `WorldEvent`
  - `event.event_type` 為 `"interaction"` | `"resource"` | `"conflict"` | `"discovery"` | `"death"` 之一
  - `event.affected_agent_ids` 包含目標 `agent_id`
  - `event.tick` 等於 `get_tick()` 的返回值
  - 呼叫後 `get_world_state().events` 中包含此事件

- [ ] **`update_agent_needs()` 後 hunger 數值增加**
  - 呼叫前記錄 `agent.personality.hunger`
  - 呼叫後重新取得 Agent，`.personality.hunger` 數值增加約 0.01
  - `agent.resources.energy` 數值減少約 2.0

- [ ] **`check_survival` 失敗的 Agent 設 `is_alive=False`**
  - 手動將某 Agent 的 `resources.food = 0`、`resources.water = 0`、`resources.energy = 0`
  - 呼叫 `update_agent_needs(agent_id)` 後
  - 從 `get_world_state()` 取得該 Agent，`.is_alive == False`

- [ ] **`list_agents()` 只返回存活 Agent**
  - 若有 Agent 的 `is_alive=False`，不出現在 `list_agents()` 結果中
  - 返回值型別為 `list[Agent]`

- [ ] **所有函數皆有型別標注**
  - 每個參數都有型別標注（如 `name: str`）
  - 每個函數都有回傳型別標注（如 `-> Agent`）
  - 執行 `python -m mypy modules/m2_agent/main.py --ignore-missing-imports` 無 error（warning 可接受）

---

## 常見問題排查

| 問題 | 可能原因 | 解法 |
|------|----------|------|
| `ConnectionError` | Ollama 服務未啟動 | 執行 `ollama serve` |
| `404 Not Found` | 模型名稱錯誤 | 確認 `config.json` 中的 `ollama_model` 與 `ollama list` 輸出一致 |
| `KeyError: agent_id` | Agent 未建立或 M1 未初始化 | 先確認 M1 `init_world` 已執行 |
| `ModuleNotFoundError` | 執行目錄不正確 | 必須在 `AI_World/` 目錄下執行，而非在 `m2_agent/` 內 |
| LLM 回傳空字串 | 模型 context 太長或模型問題 | 縮短 `recent_memories` 數量（n=3），或更換模型 |

---

*本文件依據 `AI_World_Architecture.md`（最後更新：2026-05-25）撰寫。*
*如 Schema 或介面有異動，請以 `AI_World_Architecture.md` 為準。*
