# AI World — Architecture Document

> **重要規範**：開始任何模組開發前，請務必詳閱並遵守專案根目錄下的 [CLAUDE.md](file:///c:/Users/zohanlin/Documents/zohan_ai_test/AI_World/CLAUDE.md) 規範（受 Andrej Karpathy 啟發的編碼指南），強調：**編碼前思考**、**簡潔優先**、**精準修改**、與**目標驅動執行**。
>
> 此文件是所有模組開發的聖經。所有人必須遵守此文件定義的 Schema 與介面。
> 如需修改任何 Schema 或介面簽名，必須全員討論後更新此文件，並通知所有模組負責人。

---

## 系統概覽

AI World 是一個多 Agent 世界模擬系統。
多個 AI Agent 在持久化的世界狀態中自主運行、互動、並隨時間演化。

### 核心設計原則

| 原則 | 說明 |
|------|------|
| **Simulation First** | 世界狀態獨立於 LLM，LLM 只負責解讀世界與生成行為 |
| **Contract First** | 所有模組依照此文件定義的介面開發，整合才不會破裂 |
| **Config Driven** | 所有重要參數從 `config.json` 讀取，由 M0 產生 |
| **Local First** | 整個系統可完全離線運行（Ollama + ChromaDB + SQLite）|

---

## 技術規格

| 用途 | 選型 |
|------|------|
| 語言 | Python 3.11+ |
| LLM | Ollama（本地，使用者自選模型）|
| 向量資料庫 | ChromaDB |
| 關聯式資料庫 | SQLite |
| API 框架 | FastAPI |
| 視覺化 | Streamlit |
| 資料驗證 | Pydantic v2 |

---

## 目錄結構

```
AI_World/
├── config.json                    # M0 產生，所有模組讀取（勿手動修改）
├── shared/
│   └── schemas.py                 # 共用資料格式（所有模組 import 此檔）
├── modules/
│   ├── m0_setup/
│   │   └── main.py
│   ├── m1_world_state/
│   │   ├── main.py
│   │   └── database.py
│   ├── m2_agent/
│   │   ├── main.py
│   │   └── llm_client.py
│   ├── m3_memory/
│   │   └── main.py
│   ├── m4_multi_agent/
│   │   └── main.py
│   ├── m5_rules/
│   │   └── main.py
│   ├── m6_time_history/
│   │   └── main.py
│   ├── m7_visualization/
│   │   └── app.py
│   └── m8_integration/
│       ├── main.py
│       └── start.py
├── data/
│   ├── world.db                   # SQLite（由 M1 管理）
│   └── chroma/                    # ChromaDB（由 M3 管理）
└── start.py                       # M8 產生的一鍵啟動腳本
```

---

## 共用 Data Schema

> **所有模組必須 `from shared.schemas import *` 使用以下定義，不可自行建立替代 class。**

```python
# shared/schemas.py
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


class Location(BaseModel):
    id: str = Field(default_factory=gen_id)
    name: str
    x: int
    y: int
    terrain: str  # "plains" | "mountain" | "forest" | "water"
    resources: Resource = Field(default_factory=Resource)


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


class Organization(BaseModel):
    id: str = Field(default_factory=gen_id)
    name: str
    type: str  # "tribe" | "company" | "nation"
    member_ids: list[str] = Field(default_factory=list)
    leader_id: Optional[str] = None
    resources: Resource = Field(default_factory=Resource)
    territory: list[str] = Field(default_factory=list)  # location_id 列表


class WorldEvent(BaseModel):
    id: str = Field(default_factory=gen_id)
    tick: int
    event_type: str  # "interaction" | "resource" | "conflict" | "discovery" | "death"
    description: str
    affected_agent_ids: list[str] = Field(default_factory=list)
    affected_location_ids: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)


class WorldState(BaseModel):
    tick: int = 0
    year: int = 1
    season: str = "spring"  # "spring" | "summer" | "autumn" | "winter"
    locations: dict[str, Location] = Field(default_factory=dict)
    agents: dict[str, Agent] = Field(default_factory=dict)
    organizations: dict[str, Organization] = Field(default_factory=dict)
    events: list[WorldEvent] = Field(default_factory=list)


class Config(BaseModel):
    ollama_model: str
    ollama_base_url: str = "http://localhost:11434"
    avg_response_time_sec: float
    tokens_per_sec: float
    recommended_max_agents: int
    tick_interval_sec: int
    concurrency_mode: str = "sequential"  # "sequential" | "async"
    max_concurrent_requests: int = 1
```

---

## 模組介面合約

> 以下函數簽名為各模組**對外承諾**。簽名（函數名稱、參數型別、回傳型別）**不可更改**。
> 內部實作可自由設計，但對外行為必須符合以下定義。

---

### M1 — World State Engine

```python
# modules/m1_world_state/main.py

def init_world(locations: list[Location], config: Config) -> WorldState:
    """初始化世界，建立資料庫結構，返回初始 WorldState"""

def get_world_state() -> WorldState:
    """讀取當前完整世界狀態"""

def update_agent(agent: Agent) -> None:
    """更新單一 Agent 的狀態到資料庫"""

def update_location_resources(location_id: str, resources: Resource) -> None:
    """更新指定地點的資源"""

def add_event(event: WorldEvent) -> None:
    """新增一個世界事件"""

def get_tick() -> int:
    """取得當前 tick 數"""

def save_state() -> None:
    """將當前世界狀態序列化並儲存"""

def load_state() -> WorldState:
    """從儲存讀取世界狀態"""
```

---

### M2 — Agent System

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

---

### M3 — Memory System

```python
# modules/m3_memory/main.py

def save_memory(agent_id: str, event: str, importance: float) -> str:
    """儲存 Agent 的記憶，返回記憶 id（importance: 0.0~1.0）"""

def recall_memory(agent_id: str, query: str, top_k: int = 5) -> list[str]:
    """根據語意查詢，返回最相關的記憶列表"""

def get_recent_memory(agent_id: str, n: int = 10) -> list[str]:
    """返回 Agent 最近 n 條記憶"""

def save_world_event(event: WorldEvent) -> None:
    """將世界事件存入向量資料庫，供歷史搜尋"""

def search_history(query: str, top_k: int = 10) -> list[WorldEvent]:
    """語意搜尋世界歷史事件"""
```

---

### M4 — Multi-Agent Interaction

```python
# modules/m4_multi_agent/main.py

def run_agent_interaction(agent_id_1: str, agent_id_2: str) -> WorldEvent:
    """驅動兩個 Agent 產生互動，返回互動事件"""

def run_tick() -> list[WorldEvent]:
    """執行一個完整 tick（所有 Agent 依序行動），返回本 tick 所有事件"""

def negotiate(agent_id_1: str, agent_id_2: str, topic: str) -> dict:
    """驅動兩 Agent 就某 topic 談判，返回結果 {success: bool, outcome: str}"""

def get_nearby_agents(agent_id: str, radius: int = 1) -> list[Agent]:
    """返回指定 Agent 附近 radius 格內的所有存活 Agent"""
```

---

### M5 — Rules Engine

```python
# modules/m5_rules/main.py

def validate_action(agent: Agent, action: str) -> tuple[bool, str]:
    """驗證行動是否合法，返回 (是否允許, 原因說明)"""

def apply_resource_decay(world_state: WorldState) -> WorldState:
    """每 tick 套用資源自然消耗規則，返回更新後的 WorldState"""

def check_survival(agent: Agent) -> bool:
    """檢查 Agent 是否存活（food/water/energy 是否耗盡）"""

def apply_economic_rules(world_state: WorldState) -> WorldState:
    """套用經濟規則（市場、交易上限等），返回更新後的 WorldState"""

def get_rules_summary() -> dict:
    """返回所有規則的摘要，供其他模組或視覺化使用"""
```

---

### M6 — Time & History

```python
# modules/m6_time_history/main.py

def advance_tick() -> int:
    """推進世界時間一個 tick，更新季節/年份，返回新 tick 數"""

def get_history(start_tick: int, end_tick: int) -> list[WorldEvent]:
    """取得指定 tick 範圍的歷史事件"""

def save_snapshot() -> None:
    """儲存當前世界狀態快照"""

def get_snapshot(tick: int) -> Optional[WorldState]:
    """取得指定 tick 的世界快照，若不存在返回 None"""

def get_timeline() -> list[dict]:
    """返回所有重大事件的時間軸列表 [{tick, event_type, description}]"""

def get_current_season() -> str:
    """返回當前季節 'spring' | 'summer' | 'autumn' | 'winter'"""
```

---

### M7 — Visualization（Streamlit）

```
無對外函數。
M7 是獨立的 Streamlit App，從 M1、M6 讀取資料並顯示。
啟動方式：streamlit run modules/m7_visualization/app.py
```

---

### M8 — Integration & Testing

```python
# modules/m8_integration/main.py

def run_integration_tests() -> dict:
    """執行所有整合測試，返回 {module: pass/fail, ...}"""

def start_world() -> None:
    """按正確順序啟動所有模組"""

def stop_world() -> None:
    """安全關閉所有模組"""

def health_check() -> dict:
    """檢查所有模組是否正常運行，返回各模組狀態"""
```

---

## 模組依賴關係

```
M0  →  無依賴（產出 config.json）
M1  →  M0
M2  →  M0, M1, M3, M5
M3  →  M0
M4  →  M0, M1, M2, M3, M5
M5  →  M0, M1
M6  →  M0, M1, M3
M7  →  M0, M1, M6
M8  →  M0, M1, M2, M3, M4, M5, M6, M7
```

---

## 開發順序

```
第一批（無依賴）：  M0
第二批（依賴 M0）： M1
第三批（依賴 M1）： M2、M5（可並行）、M3（可並行）
第四批：           M4（需要 M2、M3、M5）、M6（需要 M1、M3）
第五批：           M7（需要 M1、M6）
最後：             M8（全部整合）
```

## 啟動順序

```
Step 1  M0   選模型 + benchmark → 產出 config.json
Step 2  M1   初始化世界資料庫
Step 3  M5   載入規則引擎
Step 4  M3   啟動 ChromaDB 記憶系統
Step 5  M2   建立 Agents
Step 6  M4   啟動多 Agent 互動機制
Step 7  M6   啟動時間系統（開始 tick）
Step 8  M7   啟動 Streamlit 視覺化介面
Step 9  M8   跑整合測試，確認全部正常
```

---

## config.json 格式範例

```json
{
  "ollama_model": "gemma3:4b",
  "ollama_base_url": "http://localhost:11434",
  "avg_response_time_sec": 3.2,
  "tokens_per_sec": 45.0,
  "recommended_max_agents": 8,
  "tick_interval_sec": 30,
  "concurrency_mode": "sequential",
  "max_concurrent_requests": 1
}
```

---

*最後更新：2026-05-25*
