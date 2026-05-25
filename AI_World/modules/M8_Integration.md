# Module M8：Integration & Testing（整合與測試）

## 你的任務

負責將 M0–M7 所有模組串接起來，撰寫一鍵啟動腳本 `start.py`，執行端對端整合測試，並驗證整個 AI World 系統能正常運作。

---

## 負責範圍

- **負責：**
  - 撰寫 `modules/m8_integration/main.py`（health_check、run_integration_tests、start_world、stop_world）
  - 撰寫 `modules/m8_integration/test_integration.py`（整合測試腳本）
  - 撰寫根目錄 `start.py`（一鍵啟動整個系統）
  - 確認所有模組可正常被呼叫
  - 生成整合測試報告

- **不負責：**
  - 任何 M0–M7 內部邏輯的修改
  - ChromaDB 或 SQLite 的初始化（由各自模組負責）
  - Streamlit UI 的設計（由 M7 負責）
  - config.json 的生成（由 M0 負責）

---

## 依賴關係

- **需要先完成：** M0、M1、M2、M3、M4、M5、M6、M7（全部）
- **被以下模組使用：** 無（M8 是最終整合層）

---

## 工作目錄

```
c:\Users\zohanlin\Documents\zohan_ai_test\AI_World\modules\m8_integration\
```

---

## 環境安裝

M8 本身無額外的第三方依賴，所有依賴均已由 M0–M7 安裝。  
確認以下套件已存在（由前面模組安裝）：

```bash
pip install pydantic chromadb ollama streamlit fastapi uvicorn
```

如有缺漏，補裝：

```bash
pip install requests subprocess32
```

> **注意：** Python 內建的 `subprocess` 已足夠使用，無需額外安裝。

---

## 需要建立的檔案

```
AI_World/
├── start.py                          ← 一鍵啟動腳本（M8 負責人撰寫）
└── modules/
    └── m8_integration/
        ├── main.py                   ← health_check, run_integration_tests, start_world, stop_world
        └── test_integration.py       ← 整合測試腳本（3 Agent，5 tick）
```

---

## Pre-flight Checklist（整合前必須全部勾選）

在開始撰寫任何 M8 程式碼之前，請確認以下每一項都已完成：

### M0 — Setup & Config
- [ ] `config.json` 存在於 `AI_World/` 根目錄
- [ ] `config.json` 包含 `ollama_model`、`recommended_max_agents`、`tick_interval_sec` 等欄位
- [ ] `shared/schemas.py` 存在且可正常 import

### M1 — World State Engine
- [ ] `modules/m1_world_state/main.py` 存在
- [ ] `init_world()`、`get_world_state()`、`add_event()`、`get_tick()`、`save_state()` 均可呼叫
- [ ] `data/world.db` 可被建立

### M2 — Agent System
- [ ] `modules/m2_agent/main.py` 存在
- [ ] `create_agent()`、`agent_act()`、`list_agents()`、`update_agent_needs()` 均可呼叫
- [ ] Ollama 服務已啟動（`http://localhost:11434`）

### M3 — Memory System
- [ ] `modules/m3_memory/main.py` 存在
- [ ] `save_memory()`、`recall_memory()`、`save_world_event()` 均可呼叫
- [ ] `data/chroma/` 目錄可被建立

### M4 — Multi-Agent Interaction
- [ ] `modules/m4_multi_agent/main.py` 存在
- [ ] `run_tick()`、`run_agent_interaction()` 均可呼叫

### M5 — Rules Engine
- [ ] `modules/m5_rules/main.py` 存在
- [ ] `get_rules_summary()`、`apply_resource_decay()`、`check_survival()` 均可呼叫

### M6 — Time & History
- [ ] `modules/m6_time_history/main.py` 存在
- [ ] `advance_tick()`、`save_snapshot()`、`get_snapshot()` 均可呼叫
- [ ] `data/snapshots/` 目錄可被建立

### M7 — Visualization
- [ ] `modules/m7_visualization/app.py` 存在
- [ ] `streamlit run modules/m7_visualization/app.py` 指令可執行（不要求現在開啟）

---

## 共用 Schema（直接使用，不可修改）

> 來源：`AI_World_Architecture.md`。所有模組都使用同一份 schema，**不可自行建立替代 class**。

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
    relationships: dict[str, float] = Field(default_factory=dict)
    memory_ids: list[str] = Field(default_factory=list)
    organization_id: Optional[str] = None
    is_alive: bool = True
    age: int = 0


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
    season: str = "spring"
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
    concurrency_mode: str = "sequential"
    max_concurrent_requests: int = 1
```

**Import 方式（在 M8 的所有檔案頂端加上）：**

```python
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from shared.schemas import Config, Agent, AgentPersonality, WorldState, WorldEvent, Resource
```

---

## 你對外提供的函數（簽名不可修改）

```python
# modules/m8_integration/main.py

def health_check() -> dict:
    """
    檢查所有模組（M1–M7）及 Ollama 服務是否正常運行。
    返回各模組狀態字典，每個值為 "ok" 或 "error"。
    """

def run_integration_tests() -> dict:
    """
    執行端對端整合測試（3 個 Agent，5 個 tick）。
    返回測試結果摘要。
    """

def start_world() -> None:
    """
    按正確順序（M1→M5→M3→M2→M4→M6→M7）啟動所有模組。
    """

def stop_world() -> None:
    """
    安全關閉所有模組，停止背景執行的 Streamlit 進程。
    """
```

### `health_check()` 返回格式

```python
{
    "m1_world_state": "ok" | "error",
    "m2_agent": "ok" | "error",
    "m3_memory": "ok" | "error",
    "m4_multi_agent": "ok" | "error",
    "m5_rules": "ok" | "error",
    "m6_time_history": "ok" | "error",
    "m7_visualization": "ok" | "error",
    "ollama": "ok" | "error"
}
```

### `run_integration_tests()` 返回格式

```python
{
    "total_ticks": 5,
    "total_events": int,        # 所有 tick 累積的事件數
    "agents_alive": int,        # 測試結束時存活的 Agent 數
    "memories_saved": int,      # 成功寫入 ChromaDB 的記憶數
    "snapshots_saved": int,     # 成功儲存的快照數
    "passed": bool,             # True = 全部驗證通過
    "errors": list[str]         # 失敗項目的錯誤訊息列表（通過時為空 []）
}
```

---

## 你可以呼叫的外部函數

以下是 M8 在整合時需要呼叫的其他模組函數：

### M1 — World State Engine
```python
from modules.m1_world_state.main import (
    init_world,           # (locations: list[Location], config: Config) -> WorldState
    get_world_state,      # () -> WorldState
    update_agent,         # (agent: Agent) -> None
    add_event,            # (event: WorldEvent) -> None
    get_tick,             # () -> int
    save_state,           # () -> None
)
```

### M2 — Agent System
```python
from modules.m2_agent.main import (
    create_agent,         # (name: str, location_id: str, personality: AgentPersonality) -> Agent
    agent_act,            # (agent_id: str) -> WorldEvent
    list_agents,          # () -> list[Agent]
    update_agent_needs,   # (agent_id: str) -> None
)
```

### M3 — Memory System
```python
from modules.m3_memory.main import (
    save_memory,          # (agent_id: str, event: str, importance: float) -> str
    recall_memory,        # (agent_id: str, query: str, top_k: int = 5) -> list[str]
    save_world_event,     # (event: WorldEvent) -> None
)
```

### M4 — Multi-Agent Interaction
```python
from modules.m4_multi_agent.main import (
    run_tick,             # () -> list[WorldEvent]
    run_agent_interaction,# (agent_id_1: str, agent_id_2: str) -> WorldEvent
)
```

### M5 — Rules Engine
```python
from modules.m5_rules.main import (
    get_rules_summary,    # () -> dict
    apply_resource_decay, # (world_state: WorldState) -> WorldState
    check_survival,       # (agent: Agent) -> bool
)
```

### M6 — Time & History
```python
from modules.m6_time_history.main import (
    advance_tick,         # () -> int
    save_snapshot,        # () -> None
    get_snapshot,         # (tick: int) -> Optional[WorldState]
    get_history,          # (start_tick: int, end_tick: int) -> list[WorldEvent]
)
```

---

## 實作步驟

### 步驟 1：建立目錄結構

確認以下目錄存在（若不存在則建立）：

```
AI_World/modules/m8_integration/
AI_World/data/snapshots/
```

```python
# 在 main.py 開頭加上此工具函數
import os

def _ensure_dirs():
    """確保必要目錄存在"""
    dirs = [
        "data/snapshots",
        "data/chroma",
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)
```

---

### 步驟 2：實作 `health_check()`

邏輯：對每個模組呼叫一個輕量級函數，若成功則 `"ok"`，若 exception 則 `"error"`。  
對 Ollama，使用 `requests.get` 呼叫 `http://localhost:11434`。

```python
# modules/m8_integration/main.py

import sys, os, requests
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from shared.schemas import Config, Agent, AgentPersonality, WorldEvent

# ---- 載入 config ----
def _load_config() -> Config:
    import json
    config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        return Config(**json.load(f))


def health_check() -> dict:
    """
    對每個模組呼叫最輕量的函數，捕捉 Exception 即標記為 error。
    回傳格式：{"m1_world_state": "ok"|"error", ..., "ollama": "ok"|"error"}
    """
    result = {}

    # --- M1：呼叫 get_tick() ---
    try:
        from modules.m1_world_state.main import get_tick
        get_tick()
        result["m1_world_state"] = "ok"
    except Exception as e:
        result["m1_world_state"] = "error"
        # 可選：print(f"M1 error: {e}")

    # --- M2：呼叫 list_agents() ---
    try:
        # TODO: 實作
        result["m2_agent"] = "ok"
    except Exception:
        result["m2_agent"] = "error"

    # --- M3：呼叫 get_recent_memory（任意 agent_id，允許空結果）---
    try:
        # TODO: 實作
        result["m3_memory"] = "ok"
    except Exception:
        result["m3_memory"] = "error"

    # --- M4：呼叫 get_nearby_agents（允許空結果）---
    try:
        # TODO: 實作
        result["m4_multi_agent"] = "ok"
    except Exception:
        result["m4_multi_agent"] = "error"

    # --- M5：呼叫 get_rules_summary() ---
    try:
        from modules.m5_rules.main import get_rules_summary
        summary = get_rules_summary()
        assert isinstance(summary, dict)
        result["m5_rules"] = "ok"
    except Exception:
        result["m5_rules"] = "error"

    # --- M6：呼叫 get_current_season() ---
    try:
        # TODO: 實作
        result["m6_time_history"] = "ok"
    except Exception:
        result["m6_time_history"] = "error"

    # --- M7：確認 app.py 檔案存在 ---
    try:
        app_path = os.path.join(
            os.path.dirname(__file__), '..', 'm7_visualization', 'app.py'
        )
        assert os.path.exists(app_path), "app.py not found"
        result["m7_visualization"] = "ok"
    except Exception:
        result["m7_visualization"] = "error"

    # --- Ollama：HTTP GET ---
    try:
        config = _load_config()
        resp = requests.get(config.ollama_base_url, timeout=3)
        result["ollama"] = "ok" if resp.status_code == 200 else "error"
    except Exception:
        result["ollama"] = "error"

    return result
```

---

### 步驟 3：實作 `run_integration_tests()`

整合測試場景：
- 建立 3 個個性不同的 Agent（A/B/C）
- 執行 5 個 tick，每 tick 呼叫 `run_tick()`
- tick 結束後呼叫 `advance_tick()` 與 `save_snapshot()`
- 對每個 Agent 呼叫 `save_memory()`
- 最終驗證 4 個條件

```python
def run_integration_tests() -> dict:
    """
    執行 3 Agent × 5 tick 的整合測試。
    注意：此函數會修改世界狀態，請在乾淨環境下執行。
    """
    errors = []
    total_events = 0
    memories_saved = 0
    snapshots_saved = 0

    try:
        config = _load_config()

        # ── Step 1：初始化世界 ──────────────────────────────
        from modules.m1_world_state.main import init_world, get_world_state, get_tick
        from shared.schemas import Location, Resource

        # 建立測試用地點（至少 1 個）
        locations = [
            Location(name="TestPlain", x=0, y=0, terrain="plains"),
        ]
        world = init_world(locations, config)
        location_id = list(world.locations.keys())[0]

        # ── Step 2：建立 3 個 Agent ────────────────────────
        from modules.m2_agent.main import create_agent, list_agents, update_agent_needs

        agent_a = create_agent(
            name="AgentA",
            location_id=location_id,
            personality=AgentPersonality(ambition=0.8),   # 高野心
        )
        agent_b = create_agent(
            name="AgentB",
            location_id=location_id,
            personality=AgentPersonality(aggression=0.7), # 高攻擊性
        )
        agent_c = create_agent(
            name="AgentC",
            location_id=location_id,
            personality=AgentPersonality(loyalty=0.9),    # 高忠誠度
        )

        # 記錄初始 food/water 值，供後面驗證
        initial_resources = {
            agent_a.id: (agent_a.resources.food, agent_a.resources.water),
            agent_b.id: (agent_b.resources.food, agent_b.resources.water),
            agent_c.id: (agent_c.resources.food, agent_c.resources.water),
        }

        # ── Step 3：執行 5 個 tick ─────────────────────────
        from modules.m4_multi_agent.main import run_tick
        from modules.m6_time_history.main import advance_tick, save_snapshot
        from modules.m3_memory.main import save_memory, save_world_event

        for tick_num in range(1, 6):
            # 執行 tick（所有 Agent 行動）
            events = run_tick()
            total_events += len(events)

            # 將事件存入 Memory
            for event in events:
                try:
                    save_world_event(event)
                except Exception as e:
                    errors.append(f"tick {tick_num} save_world_event 失敗: {e}")

            # 對每個 Agent 儲存本 tick 的記憶
            for agent in [agent_a, agent_b, agent_c]:
                try:
                    mem_id = save_memory(
                        agent_id=agent.id,
                        event=f"tick {tick_num} 完成，共 {len(events)} 個事件",
                        importance=0.5,
                    )
                    if mem_id:
                        memories_saved += 1
                except Exception as e:
                    errors.append(f"tick {tick_num} save_memory({agent.name}) 失敗: {e}")

            # 更新 Agent 需求
            for agent in [agent_a, agent_b, agent_c]:
                try:
                    update_agent_needs(agent.id)
                except Exception as e:
                    errors.append(f"tick {tick_num} update_agent_needs({agent.name}) 失敗: {e}")

            # 推進時間並儲存快照
            advance_tick()
            try:
                save_snapshot()
                snapshots_saved += 1
            except Exception as e:
                errors.append(f"tick {tick_num} save_snapshot 失敗: {e}")

        # ── Step 4：驗證結果 ───────────────────────────────
        # 驗證 1：每個 tick 都有至少 1 個 WorldEvent（共 5 tick，至少 5 個事件）
        if total_events < 5:
            errors.append(
                f"驗證失敗：total_events={total_events}，期望 >= 5"
            )

        # 驗證 2：Agent 的 food/water 比初始值低
        world_final = get_world_state()
        for agent_id, (init_food, init_water) in initial_resources.items():
            agent_final = world_final.agents.get(agent_id)
            if agent_final is None:
                errors.append(f"驗證失敗：agent {agent_id} 不存在於最終世界狀態")
                continue
            # TODO: 比較 food/water，若沒有下降則 append error
            # if agent_final.resources.food >= init_food:
            #     errors.append(f"驗證失敗：{agent_id} food 未下降")
            # if agent_final.resources.water >= init_water:
            #     errors.append(f"驗證失敗：{agent_id} water 未下降")

        # 驗證 3：Memory 有被寫入
        if memories_saved == 0:
            errors.append("驗證失敗：memories_saved = 0，ChromaDB 未寫入任何記憶")

        # 驗證 4：快照存在
        if snapshots_saved == 0:
            errors.append("驗證失敗：snapshots_saved = 0，未儲存任何快照")

        agents_alive = sum(
            1 for a in world_final.agents.values() if a.is_alive
        )

    except Exception as e:
        errors.append(f"整合測試發生嚴重錯誤：{e}")
        agents_alive = 0

    return {
        "total_ticks": 5,
        "total_events": total_events,
        "agents_alive": agents_alive,
        "memories_saved": memories_saved,
        "snapshots_saved": snapshots_saved,
        "passed": len(errors) == 0,
        "errors": errors,
    }
```

---

### 步驟 4：實作 `start_world()` 與 `stop_world()`

```python
import subprocess

# 全域變數：儲存 Streamlit 進程
_streamlit_process = None


def start_world() -> None:
    """
    按正確順序啟動整個 AI World。
    啟動順序：M1 → M5 → M3 → M2（建立 Agents）→ M4 → M6 → M7（背景）
    """
    global _streamlit_process

    print("=== AI World 啟動中 ===")
    config = _load_config()

    # Step 1：M1 初始化世界
    print("[1/7] M1：初始化世界狀態...")
    from modules.m1_world_state.main import init_world
    from shared.schemas import Location
    # TODO: 建立初始地點列表（建議至少 4 個不同地形）
    locations = [
        Location(name="北方平原", x=0, y=0, terrain="plains"),
        Location(name="東方山脈", x=1, y=0, terrain="mountain"),
        Location(name="南方森林", x=0, y=1, terrain="forest"),
        Location(name="西方湖泊", x=1, y=1, terrain="water"),
    ]
    world = init_world(locations, config)
    print(f"    世界初始化完成，locations={len(world.locations)}")

    # Step 2：M5 確認規則引擎
    print("[2/7] M5：載入規則引擎...")
    from modules.m5_rules.main import get_rules_summary
    rules = get_rules_summary()
    print(f"    規則載入完成，規則數={len(rules)}")

    # Step 3：M3 確認記憶系統
    print("[3/7] M3：啟動記憶系統...")
    from modules.m3_memory.main import save_memory
    # 用一筆測試記憶確認 ChromaDB 正常
    # TODO: 呼叫 save_memory("__test__", "系統啟動", 0.1)
    print("    記憶系統正常")

    # Step 4：M2 建立初始 Agents
    print(f"[4/7] M2：建立 {config.recommended_max_agents} 個初始 Agent...")
    from modules.m2_agent.main import create_agent
    location_ids = list(world.locations.keys())
    for i in range(config.recommended_max_agents):
        # TODO: 建立 Agent，名稱為 f"Agent_{i+1:02d}"，隨機分配 location
        # 建議使用 random.choice(location_ids) 分配位置
        pass
    print(f"    {config.recommended_max_agents} 個 Agent 建立完成")

    # Step 5：M4 確認多 Agent 互動機制
    print("[5/7] M4：確認多 Agent 互動機制...")
    # M4 本身是無狀態的，只需確認 import 成功
    from modules.m4_multi_agent.main import run_tick
    print("    M4 就緒")

    # Step 6：M6 啟動時間管理
    print("[6/7] M6：啟動時間管理...")
    from modules.m6_time_history.main import advance_tick, get_current_season
    season = get_current_season()
    print(f"    當前季節：{season}")

    # Step 7：M7 用 subprocess 背景啟動 Streamlit
    print("[7/7] M7：背景啟動 Streamlit 視覺化介面...")
    app_path = os.path.join(
        os.path.dirname(__file__), '..', 'm7_visualization', 'app.py'
    )
    # TODO: 用 subprocess.Popen 啟動 streamlit，儲存至 _streamlit_process
    # _streamlit_process = subprocess.Popen(
    #     ["streamlit", "run", app_path, "--server.headless", "true"],
    #     stdout=subprocess.DEVNULL,
    #     stderr=subprocess.DEVNULL,
    # )
    print(f"    Streamlit 已於背景啟動（PID: {_streamlit_process.pid if _streamlit_process else 'N/A'}）")
    print("    瀏覽器開啟：http://localhost:8501")

    print("\n=== AI World 啟動完成 ✓ ===\n")


def stop_world() -> None:
    """
    安全關閉 AI World。
    - 儲存當前世界狀態
    - 終止 Streamlit 背景進程
    """
    global _streamlit_process

    print("=== AI World 關閉中 ===")

    # 儲存世界狀態
    try:
        from modules.m1_world_state.main import save_state
        save_state()
        print("    世界狀態已儲存")
    except Exception as e:
        print(f"    警告：世界狀態儲存失敗 - {e}")

    # 儲存最終快照
    try:
        from modules.m6_time_history.main import save_snapshot
        save_snapshot()
        print("    最終快照已儲存")
    except Exception as e:
        print(f"    警告：快照儲存失敗 - {e}")

    # 終止 Streamlit
    if _streamlit_process is not None:
        _streamlit_process.terminate()
        _streamlit_process = None
        print("    Streamlit 已關閉")

    print("=== AI World 已安全關閉 ===")
```

---

### 步驟 5：撰寫 `test_integration.py`

這個腳本可以獨立執行（`python test_integration.py`），會印出完整測試報告。

```python
# modules/m8_integration/test_integration.py

import sys
import os
import json
from datetime import datetime

# 路徑設定：從 m8_integration/ 往上兩層到 AI_World/
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT)
os.chdir(ROOT)  # 確保相對路徑（data/、config.json）都正確

from modules.m8_integration.main import health_check, run_integration_tests


def print_separator(char="─", width=60):
    print(char * width)


def run_health_check_report():
    """執行 health_check 並印出格式化報告"""
    print_separator("═")
    print("  AI World Health Check")
    print(f"  執行時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print_separator("═")

    results = health_check()

    all_ok = True
    for module, status in results.items():
        icon = "✓" if status == "ok" else "✗"
        print(f"  {icon}  {module:<25} {status}")
        if status != "ok":
            all_ok = False

    print_separator()
    print(f"  整體狀態：{'全部正常 ✓' if all_ok else '有模組異常 ✗'}")
    print_separator("═")
    return all_ok


def run_integration_test_report():
    """執行整合測試並印出格式化報告"""
    print_separator("═")
    print("  AI World Integration Test（3 Agent × 5 Tick）")
    print(f"  執行時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print_separator("═")

    print("  正在執行整合測試，請稍候...\n")
    results = run_integration_tests()

    print(f"  Total Ticks    : {results['total_ticks']}")
    print(f"  Total Events   : {results['total_events']}")
    print(f"  Agents Alive   : {results['agents_alive']}")
    print(f"  Memories Saved : {results['memories_saved']}")
    print(f"  Snapshots Saved: {results['snapshots_saved']}")
    print_separator()

    if results["passed"]:
        print("  結果：整合測試全部通過 ✓")
    else:
        print("  結果：整合測試失敗 ✗")
        print("  錯誤列表：")
        for err in results["errors"]:
            print(f"    - {err}")

    print_separator("═")
    return results["passed"]


def save_report(health_ok: bool, test_results: dict):
    """將測試報告儲存為 JSON 檔"""
    report = {
        "generated_at": datetime.now().isoformat(),
        "health_check_passed": health_ok,
        "integration_test": test_results,
    }
    report_path = os.path.join(ROOT, "data", "integration_report.json")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n  報告已儲存至：{report_path}")


if __name__ == "__main__":
    # 執行 health check
    health_ok = run_health_check_report()

    if not health_ok:
        print("\n  有模組未通過 health check，請先修復後再執行整合測試。")
        sys.exit(1)

    print()

    # 執行整合測試
    test_results = run_integration_tests()
    test_ok = run_integration_test_report()

    # 儲存報告
    save_report(health_ok, test_results)

    sys.exit(0 if (health_ok and test_ok) else 1)
```

---

### 步驟 6：撰寫根目錄 `start.py`

這是整個系統的一鍵啟動腳本，使用者執行 `python start.py` 即可啟動 AI World 並進入互動模式。

```python
# AI_World/start.py
"""
AI World 一鍵啟動腳本
執行方式：python start.py
"""

import sys
import os
import time
import signal

# 確保在 AI_World/ 根目錄下執行
ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
sys.path.insert(0, ROOT)


def check_config():
    """確認 config.json 存在"""
    config_path = os.path.join(ROOT, "config.json")
    if not os.path.exists(config_path):
        print("✗ 找不到 config.json！")
        print("  請先執行 M0 進行設定：")
        print("  python modules/m0_setup/main.py")
        sys.exit(1)
    print("✓ config.json 存在")


def run_health_check():
    """執行 health check，若有模組異常則警告"""
    from modules.m8_integration.main import health_check
    results = health_check()
    failed = [k for k, v in results.items() if v != "ok"]
    if failed:
        print(f"⚠  以下模組 health check 未通過：{failed}")
        ans = input("   是否仍要繼續啟動？[y/N] ").strip().lower()
        if ans != "y":
            print("   啟動已取消。")
            sys.exit(1)
    else:
        print("✓ 所有模組 health check 通過")


def graceful_shutdown(signum, frame):
    """收到 Ctrl+C 時安全關閉"""
    print("\n\n收到關閉訊號，正在安全關閉 AI World...")
    try:
        from modules.m8_integration.main import stop_world
        stop_world()
    except Exception as e:
        print(f"警告：關閉過程發生錯誤 - {e}")
    sys.exit(0)


def main():
    print("╔══════════════════════════════════════╗")
    print("║       AI World — 系統啟動            ║")
    print("╚══════════════════════════════════════╝\n")

    # 1. 確認 config.json
    check_config()

    # 2. Health check
    print("\n[Pre-flight] 執行模組健康檢查...")
    run_health_check()

    # 3. 啟動世界
    print("\n[啟動] 開始初始化 AI World...\n")
    from modules.m8_integration.main import start_world, stop_world
    signal.signal(signal.SIGINT, graceful_shutdown)

    start_world()

    # 4. 進入 tick 循環
    print("AI World 運行中。按 Ctrl+C 可安全關閉。\n")
    print("Streamlit 視覺化介面：http://localhost:8501\n")

    from modules.m4_multi_agent.main import run_tick
    from modules.m6_time_history.main import advance_tick, save_snapshot
    from shared.schemas import Config
    import json

    with open(os.path.join(ROOT, "config.json"), "r") as f:
        config = Config(**json.load(f))

    tick_count = 0
    while True:
        tick_count += 1
        print(f"─── Tick {tick_count} ───────────────────────")

        # 執行 tick
        try:
            events = run_tick()
            print(f"    本 tick 發生 {len(events)} 個事件")
        except Exception as e:
            print(f"    ✗ run_tick 失敗：{e}")

        # 推進時間
        try:
            new_tick = advance_tick()
            print(f"    時間推進至 tick {new_tick}")
        except Exception as e:
            print(f"    ✗ advance_tick 失敗：{e}")

        # 每 10 tick 儲存一次快照
        if tick_count % 10 == 0:
            try:
                save_snapshot()
                print(f"    快照已儲存（tick {tick_count}）")
            except Exception as e:
                print(f"    ✗ save_snapshot 失敗：{e}")

        # 等待下一個 tick
        time.sleep(config.tick_interval_sec)


if __name__ == "__main__":
    main()
```

---

## 驗證標準（全部通過才算完成）

### 基礎環境
- [ ] `config.json` 存在於 `AI_World/` 根目錄，且格式符合 `Config` schema
- [ ] `shared/schemas.py` 可被 `from shared.schemas import *` 正常 import

### 模組健康檢查
- [ ] `health_check()` 執行不拋出 exception
- [ ] `health_check()` 所有模組回傳 `"ok"`（包含 `"ollama": "ok"`）

### 整合測試
- [ ] `run_integration_tests()` 執行不拋出 exception
- [ ] `run_integration_tests()` 回傳 `passed = True`
- [ ] `total_events >= 5`（5 個 tick，每 tick 至少 1 個 WorldEvent）
- [ ] 所有存活 Agent 的 `food` / `water` 值都低於初始值（100.0）
- [ ] `memories_saved >= 1`（ChromaDB 至少寫入 1 筆記憶）
- [ ] `snapshots_saved >= 1`（`data/snapshots/` 有快照檔案）

### 資料驗證
- [ ] `data/world.db` 存在且有資料
- [ ] `data/chroma/` 目錄存在且有資料
- [ ] `data/snapshots/` 目錄存在且有至少 1 個快照檔案
- [ ] `data/integration_report.json` 存在（執行 `test_integration.py` 後生成）

### 啟動腳本
- [ ] `start.py` 存在於 `AI_World/` 根目錄
- [ ] `python start.py` 可以成功執行，不拋出 ImportError 或 FileNotFoundError
- [ ] Streamlit 介面可在 `http://localhost:8501` 正常開啟

### 獨立測試腳本
- [ ] `python modules/m8_integration/test_integration.py` 可以獨立執行
- [ ] 輸出顯示 `整合測試全部通過 ✓`

---

## 常見問題排解

### `ModuleNotFoundError: No module named 'shared'`
確認執行腳本時的工作目錄為 `AI_World/`，或在腳本頂端加上：
```python
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
```

### `health_check()` 回傳 `"ollama": "error"`
確認 Ollama 服務已啟動：
```bash
ollama serve
```
然後確認 `http://localhost:11434` 可以被存取。

### `run_integration_tests()` 回傳 `memories_saved = 0`
ChromaDB 可能未正確初始化。確認 M3 的 `save_memory()` 可以獨立正常呼叫：
```python
from modules.m3_memory.main import save_memory
mem_id = save_memory("test_agent", "測試記憶", 0.5)
print(mem_id)  # 應印出記憶 ID
```

### Streamlit 未啟動
確認 M7 的 `app.py` 路徑正確，並手動測試：
```bash
streamlit run modules/m7_visualization/app.py
```

### `total_events < 5`
確認 M4 的 `run_tick()` 有正確返回 `list[WorldEvent]`，且列表不為空。可先單獨測試：
```python
from modules.m4_multi_agent.main import run_tick
events = run_tick()
print(f"本 tick 事件數：{len(events)}")
```

---

## 參考：完整啟動流程圖

```
python start.py
    │
    ├─ check_config()
    │   └─ config.json ✓
    │
    ├─ health_check()（所有模組 "ok"）
    │
    └─ start_world()
        ├─ [1] M1: init_world()        → data/world.db
        ├─ [2] M5: get_rules_summary() → 規則確認
        ├─ [3] M3: save_memory(test)   → ChromaDB 確認
        ├─ [4] M2: create_agent() × N  → N 個 Agent 建立
        ├─ [5] M4: run_tick (就緒)
        ├─ [6] M6: get_current_season()
        └─ [7] M7: subprocess streamlit → http://localhost:8501
            │
            └─ 進入 tick 循環
                ├─ run_tick()
                ├─ advance_tick()
                └─ save_snapshot()（每 10 tick）
```

---

*最後更新：2026-05-25 | 對應 Architecture.md 版本：2026-05-25*
