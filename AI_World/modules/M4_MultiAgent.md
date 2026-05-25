# Module M4：多 Agent 互動引擎（Multi-Agent Interaction Engine）

## 你的任務

協調多個 Agent 在同一個 AI World 中的互動，並驅動完整的 tick 循環——每個 tick 讓所有存活 Agent 依序完成需求更新、生存檢查、鄰近互動、行動執行與記憶儲存，最終返回本 tick 所有發生的 `WorldEvent`。

---

## 負責範圍

- **負責：**
  - 實作 `run_tick()` 完整 tick 驅動流程
  - 判斷哪些 Agent 在同一地點（`get_nearby_agents()`）
  - 驅動兩個 Agent 之間的互動事件（`run_agent_interaction()`）
  - 驅動談判流程並更新 Agent relationship（`negotiate()`）
  - 協調呼叫 M1、M2、M3、M5 的外部函數
  - 確保死亡 Agent 不再參與後續 tick

- **不負責：**
  - LLM 呼叫本身（由 M2 的 `agent_think` / `agent_act` 負責）
  - 資源消耗規則計算（由 M5 的 `apply_resource_decay` 負責）
  - 行動合法性驗證邏輯（由 M5 的 `validate_action` 負責）
  - 記憶的向量儲存細節（由 M3 的 `save_memory` 負責）
  - 世界狀態的持久化（由 M1 的 `add_event` / `update_agent` 負責）
  - 時間推進（`advance_tick()` 由 M6 負責）

---

## 依賴關係

- **需要先完成：**
  - M0（提供 `config.json`）
  - M1（提供 `get_world_state`, `add_event`, `update_agent`）
  - M2（提供 `agent_think`, `agent_act`, `update_agent_needs`, `list_agents`）
  - M3（提供 `save_memory`, `recall_memory`）
  - M5（提供 `validate_action`, `apply_resource_decay`, `check_survival`）

- **被以下模組使用：**
  - M8（整合測試時呼叫 `run_tick()`）
  - M6（時間系統在每個 tick 後呼叫 M4 驅動世界運作）

---

## 工作目錄

```
c:\Users\zohanlin\Documents\zohan_ai_test\AI_World\modules\m4_multi_agent\
```

---

## 環境安裝

```bash
pip install pydantic
```

> [!NOTE]
> pydantic 用於 Schema 型別驗證。M4 本身不直接安裝 LLM 或資料庫套件，所有 LLM / DB 操作皆透過呼叫 M2、M3 的函數完成。

---

## 需要建立的檔案

```
AI_World/
└── modules/
    └── m4_multi_agent/
        └── main.py          ← 唯一需要實作的檔案
```

> [!IMPORTANT]
> **不需要**建立 `__init__.py`。整個模組只有一個 `main.py`。

---

## 共用 Schema（直接使用，不可修改）

以下 Schema 定義在 `shared/schemas.py`，M4 **必須** `from shared.schemas import *` 使用，禁止自行重新定義這些 class。

```python
# shared/schemas.py（節錄 M4 相關部分）

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


class Location(BaseModel):
    id: str = Field(default_factory=gen_id)
    name: str
    x: int
    y: int
    terrain: str  # "plains" | "mountain" | "forest" | "water"
    resources: Resource = Field(default_factory=Resource)


class Organization(BaseModel):
    id: str = Field(default_factory=gen_id)
    name: str
    type: str  # "tribe" | "company" | "nation"
    member_ids: list[str] = Field(default_factory=list)
    leader_id: Optional[str] = None
    resources: Resource = Field(default_factory=Resource)
    territory: list[str] = Field(default_factory=list)


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
```

---

## 你對外提供的函數（簽名不可修改）

以下四個函數是 M4 的**對外合約**。函數名稱、參數名稱、參數型別、回傳型別**一律不得修改**。

```python
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

## 你可以呼叫的外部函數

以下是 M4 被允許呼叫的其他模組函數。呼叫時使用完整 import 路徑，**不可**繞過這些介面直接操作資料庫。

```python
# M1 — World State Engine
from modules.m1_world_state.main import (
    get_world_state,      # () -> WorldState：讀取當前完整世界狀態
    add_event,            # (event: WorldEvent) -> None：新增世界事件
    update_agent,         # (agent: Agent) -> None：更新 Agent 狀態到資料庫
    get_tick,             # () -> int：取得當前 tick 數
)

# M2 — Agent System
from modules.m2_agent.main import (
    agent_think,          # (agent_id: str, context: str) -> str：讓 Agent 思考，返回行動描述
    agent_act,            # (agent_id: str) -> WorldEvent：讓 Agent 執行行動，返回事件
    update_agent_needs,   # (agent_id: str) -> None：更新 Agent 的 hunger/energy 等需求
    list_agents,          # () -> list[Agent]：列出所有存活 Agent
)

# M3 — Memory System
from modules.m3_memory.main import (
    save_memory,          # (agent_id: str, event: str, importance: float) -> str：儲存記憶
    recall_memory,        # (agent_id: str, query: str, top_k: int = 5) -> list[str]：語意搜尋記憶
)

# M5 — Rules Engine
from modules.m5_rules.main import (
    validate_action,      # (agent: Agent, action: str) -> tuple[bool, str]：驗證行動是否合法
    apply_resource_decay, # (world_state: WorldState) -> WorldState：套用資源自然消耗
    check_survival,       # (agent: Agent) -> bool：檢查 Agent 是否存活
)
```

---

## 實作步驟

### 步驟 1：建立檔案並設定 import

建立 `modules/m4_multi_agent/main.py`，加入所有必要 import：

```python
# modules/m4_multi_agent/main.py

from shared.schemas import Agent, WorldEvent, WorldState

from modules.m1_world_state.main import (
    get_world_state,
    add_event,
    update_agent,
    get_tick,
)
from modules.m2_agent.main import (
    agent_think,
    agent_act,
    update_agent_needs,
    list_agents,
)
from modules.m3_memory.main import save_memory, recall_memory
from modules.m5_rules.main import validate_action, apply_resource_decay, check_survival
```

---

### 步驟 2：實作 `get_nearby_agents()`

邏輯說明：
- 從 `get_world_state()` 取得當前 `WorldState`
- 找到 `agent_id` 對應的 `Location`（取得 `x`, `y` 座標）
- 遍歷所有其他 **存活** Agent，計算 Chebyshev 距離（棋盤格距離）
- 距離 ≤ `radius` 且非自身 → 加入回傳列表

> [!TIP]
> Chebyshev 距離公式：`max(|x1-x2|, |y1-y2|)`。這讓「相鄰」包含對角線方向，符合直覺的棋盤格移動。

```python
def get_nearby_agents(agent_id: str, radius: int = 1) -> list[Agent]:
    """返回指定 Agent 附近 radius 格內的所有存活 Agent"""
    world: WorldState = get_world_state()

    # TODO: 取得目標 Agent 的位置
    target_agent = world.agents.get(agent_id)
    if target_agent is None or not target_agent.is_alive:
        return []

    target_location = world.locations.get(target_agent.location_id)
    if target_location is None:
        return []

    nearby: list[Agent] = []

    for other_id, other_agent in world.agents.items():
        # TODO: 跳過自身與死亡 Agent
        if other_id == agent_id or not other_agent.is_alive:
            continue

        # TODO: 計算兩個 Agent 所在 Location 的 Chebyshev 距離
        other_location = world.locations.get(other_agent.location_id)
        if other_location is None:
            continue

        distance = max(
            abs(target_location.x - other_location.x),
            abs(target_location.y - other_location.y),
        )

        # TODO: 若距離 <= radius，加入列表
        if distance <= radius:
            nearby.append(other_agent)

    return nearby
```

---

### 步驟 3：實作 `run_agent_interaction()`

邏輯說明：
- 分別呼叫 `agent_think()` 讓兩個 Agent 思考「遇到對方」的情境
- 根據雙方 `personality.aggression` 決定互動類型：
  - 若任一方 `aggression > 0.7` → `event_type = "conflict"`
  - 否則 → `event_type = "interaction"`
- 建立一個 `WorldEvent` 描述這次互動
- 呼叫 `save_memory()` 讓兩個 Agent 都記住這次事件
- 呼叫 `add_event()` 把事件加入世界歷史

```python
def run_agent_interaction(agent_id_1: str, agent_id_2: str) -> WorldEvent:
    """驅動兩個 Agent 產生互動，返回互動事件"""
    world: WorldState = get_world_state()
    current_tick: int = get_tick()

    agent1 = world.agents.get(agent_id_1)
    agent2 = world.agents.get(agent_id_2)

    if agent1 is None or agent2 is None:
        raise ValueError(f"Agent 不存在：{agent_id_1} 或 {agent_id_2}")

    # TODO: 讓兩個 Agent 各自思考遇到對方的情境
    context_1 = f"你遇到了 {agent2.name}，思考你該如何回應。"
    context_2 = f"你遇到了 {agent1.name}，思考你該如何回應。"

    thought_1 = agent_think(agent_id_1, context_1)
    thought_2 = agent_think(agent_id_2, context_2)

    # TODO: 根據 aggression 決定互動類型
    is_conflict = (
        agent1.personality.aggression > 0.7
        or agent2.personality.aggression > 0.7
    )
    event_type = "conflict" if is_conflict else "interaction"

    # TODO: 建立 WorldEvent
    description = (
        f"{agent1.name} 與 {agent2.name} 發生{'衝突' if is_conflict else '互動'}。"
        f"（{agent1.name}：{thought_1[:50]}…）"
        f"（{agent2.name}：{thought_2[:50]}…）"
    )
    event = WorldEvent(
        tick=current_tick,
        event_type=event_type,
        description=description,
        affected_agent_ids=[agent_id_1, agent_id_2],
    )

    # TODO: 兩個 Agent 各自記住這次互動
    importance = 0.8 if is_conflict else 0.5
    save_memory(agent_id_1, description, importance)
    save_memory(agent_id_2, description, importance)

    # TODO: 新增事件到世界歷史
    add_event(event)

    return event
```

---

### 步驟 4：實作 `negotiate()`

邏輯說明：
- 讓兩個 Agent 各自 `agent_think()`，將 `topic` 作為思考 context
- 根據雙方個性計算談判成功率：
  - `loyalty` 高 → 傾向合作（提高成功率）
  - `aggression` 高 → 傾向對抗（降低成功率）
  - 建議公式：`success_prob = (a1.loyalty + a2.loyalty) / 2 - (a1.aggression + a2.aggression) / 4`
- 若成功（`success_prob > 0.5`）：
  - 更新兩個 Agent 的 `relationships` 分數（互相增加 `+0.1`，上限 `1.0`）
  - 呼叫 `update_agent()` 儲存更新後的 Agent
- 建立談判記憶並呼叫 `save_memory()`
- 返回 `{"success": bool, "outcome": str}`

> [!IMPORTANT]
> 回傳格式必須嚴格符合 `{"success": bool, "outcome": str}`。`outcome` 是描述談判結果的文字說明。

```python
def negotiate(agent_id_1: str, agent_id_2: str, topic: str) -> dict:
    """驅動兩 Agent 就某 topic 談判，返回結果 {success: bool, outcome: str}"""
    world: WorldState = get_world_state()

    agent1 = world.agents.get(agent_id_1)
    agent2 = world.agents.get(agent_id_2)

    if agent1 is None or agent2 is None:
        raise ValueError(f"Agent 不存在：{agent_id_1} 或 {agent_id_2}")

    # TODO: 兩個 Agent 各自針對 topic 思考
    context = f"你正在與對方談判，主題是：{topic}。表達你的立場。"
    thought_1 = agent_think(agent_id_1, context)
    thought_2 = agent_think(agent_id_2, context)

    # TODO: 根據 personality 計算成功率
    success_prob = (
        (agent1.personality.loyalty + agent2.personality.loyalty) / 2
        - (agent1.personality.aggression + agent2.personality.aggression) / 4
    )
    success = success_prob > 0.5

    # TODO: 若談判成功，更新雙方 relationship 分數
    if success:
        current_rel_1_to_2 = agent1.relationships.get(agent_id_2, 0.0)
        current_rel_2_to_1 = agent2.relationships.get(agent_id_1, 0.0)

        agent1.relationships[agent_id_2] = min(1.0, current_rel_1_to_2 + 0.1)
        agent2.relationships[agent_id_1] = min(1.0, current_rel_2_to_1 + 0.1)

        update_agent(agent1)
        update_agent(agent2)

    # TODO: 建立 outcome 描述與記憶
    outcome = (
        f"談判{'成功' if success else '失敗'}（成功率：{success_prob:.2f}）。"
        f"主題：{topic}。"
        f"{agent1.name} 的立場：{thought_1[:50]}…"
        f"{agent2.name} 的立場：{thought_2[:50]}…"
    )

    importance = 0.7 if success else 0.4
    save_memory(agent_id_1, outcome, importance)
    save_memory(agent_id_2, outcome, importance)

    return {"success": success, "outcome": outcome}
```

---

### 步驟 5：實作 `run_tick()`（核心主流程）

`run_tick()` 是 M4 的主函數，負責驅動一個完整 tick。請嚴格按照以下流程實作：

```
1. get_world_state() 取得當前狀態
2. apply_resource_decay() 套用資源消耗
3. 對每個存活 Agent：
   a. update_agent_needs()
   b. check_survival() → 若死亡則標記並建立 death 事件
   c. get_nearby_agents() 找附近 Agent
   d. 若有鄰近 Agent → run_agent_interaction()
   e. agent_act() → 取得行動事件
   f. validate_action() → 不合法則跳過，記錄原因
   g. save_memory() 存入記憶
4. 收集所有 WorldEvent，呼叫 add_event()
5. 返回本 tick 所有事件
```

```python
def run_tick() -> list[WorldEvent]:
    """執行一個完整 tick（所有 Agent 依序行動），返回本 tick 所有事件"""
    tick_events: list[WorldEvent] = []
    current_tick: int = get_tick()

    # --- 步驟 1：取得當前世界狀態 ---
    world: WorldState = get_world_state()

    # --- 步驟 2：套用資源自然消耗 ---
    # TODO: 呼叫 apply_resource_decay()，傳入當前 WorldState
    world = apply_resource_decay(world)

    # --- 步驟 3：對每個存活 Agent 執行行動循環 ---
    agents: list[Agent] = list_agents()  # 只返回存活 Agent

    for agent in agents:
        # --- 3a：更新 Agent 需求（hunger, energy 等）---
        # TODO: 呼叫 update_agent_needs()
        update_agent_needs(agent.id)

        # --- 重新取得最新 Agent 狀態（needs 已更新）---
        refreshed_world = get_world_state()
        agent = refreshed_world.agents.get(agent.id)
        if agent is None:
            continue

        # --- 3b：生存檢查 ---
        # TODO: 呼叫 check_survival()，若死亡則標記 is_alive=False 並建立 death 事件
        is_alive = check_survival(agent)
        if not is_alive:
            agent.is_alive = False
            update_agent(agent)

            death_event = WorldEvent(
                tick=current_tick,
                event_type="death",
                description=f"{agent.name} 因資源耗盡而死亡。",
                affected_agent_ids=[agent.id],
                affected_location_ids=[agent.location_id],
            )
            add_event(death_event)
            tick_events.append(death_event)
            # 死亡後跳過本 Agent 的後續步驟
            continue

        # --- 3c：尋找附近 Agent ---
        # TODO: 呼叫 get_nearby_agents()，radius=1
        nearby: list[Agent] = get_nearby_agents(agent.id, radius=1)

        # --- 3d：若有鄰近 Agent，執行互動 ---
        # TODO: 對第一個鄰近 Agent 呼叫 run_agent_interaction()
        #       （進階：可對所有鄰近 Agent 都互動，但要避免重複互動）
        if nearby:
            interaction_target = nearby[0]
            try:
                interaction_event = run_agent_interaction(agent.id, interaction_target.id)
                tick_events.append(interaction_event)
            except Exception as e:
                print(f"[M4] 互動失敗：{agent.name} <-> {interaction_target.name}：{e}")

        # --- 3e：讓 Agent 執行行動 ---
        # TODO: 呼叫 agent_act()，取得行動 WorldEvent
        try:
            action_event: WorldEvent = agent_act(agent.id)
        except Exception as e:
            print(f"[M4] agent_act 失敗（{agent.name}）：{e}")
            continue

        # --- 3f：驗證行動合法性 ---
        # TODO: 呼叫 validate_action()；若不合法，跳過此事件（不加入列表）
        is_valid, reason = validate_action(agent, action_event.event_type)
        if not is_valid:
            print(f"[M4] 行動不合法（{agent.name}）：{reason}，跳過。")
            continue

        # 合法行動：加入 tick 事件列表並寫入世界
        add_event(action_event)
        tick_events.append(action_event)

        # --- 3g：儲存記憶 ---
        # TODO: 呼叫 save_memory()，讓 Agent 記住這次行動
        memory_text = f"Tick {current_tick}：{action_event.description}"
        save_memory(agent.id, memory_text, importance=0.5)

    return tick_events
```

---

## 驗證標準（全部通過才算完成）

請依序執行以下驗證，**所有項目必須通過**才算完成 M4 的開發：

- [ ] **環境確認**：`python -c "from modules.m4_multi_agent.main import run_tick, run_agent_interaction, negotiate, get_nearby_agents; print('import OK')"` 輸出 `import OK` 不報錯

- [ ] **`run_tick()` 完整驅動**：在測試環境中準備 3 個存活 Agent（位於不同 Location），呼叫 `run_tick()` 不拋出 Exception，且成功返回 `list[WorldEvent]`

- [ ] **`run_tick()` 至少返回 1 個事件**：`len(run_tick()) >= 1`

- [ ] **`get_nearby_agents()` 只返回同地點 Agent**：將 Agent A 放在 `(0,0)`，Agent B 放在 `(0,1)`，Agent C 放在 `(5,5)`；呼叫 `get_nearby_agents(A.id, radius=1)` 應只返回 B，不返回 C

- [ ] **`get_nearby_agents()` 不返回自身**：返回列表中不包含呼叫者自己的 Agent

- [ ] **`get_nearby_agents()` 不返回死亡 Agent**：將某個鄰近 Agent 標記 `is_alive=False`，確認不出現在結果中

- [ ] **`run_agent_interaction()` 返回合法 WorldEvent**：返回值型別為 `WorldEvent`，且 `event_type` 為 `"interaction"` 或 `"conflict"`，`affected_agent_ids` 包含兩個 Agent 的 id

- [ ] **`negotiate()` 返回合法格式**：`result = negotiate(a1.id, a2.id, "資源分配")`，確認 `result` 是 `dict`，且包含 `"success"` (`bool`) 與 `"outcome"` (`str`) 兩個 key

- [ ] **談判成功時 relationship 有更新**：在 `loyalty` 高、`aggression` 低的兩個 Agent 之間執行 `negotiate()`，確認雙方 `relationships` 分數有提升

- [ ] **死亡 Agent 不再參與 tick**：將一個 Agent 的資源耗盡使其死亡後，下一次 `run_tick()` 的返回事件中，不應出現該 Agent 作為行動主體的事件（death 事件除外）

- [ ] **事件已寫入 M1**：呼叫 `run_tick()` 後，`get_world_state().events` 的長度應有增加，確認事件確實透過 `add_event()` 被寫入

- [ ] **記憶已寫入 M3**：呼叫 `run_tick()` 後，對參與行動的 Agent 呼叫 `recall_memory(agent_id, "行動", top_k=1)`，應能取回至少一條記憶

---

## 附錄：互動類型判斷邏輯摘要

| 情境 | 判斷條件 | event_type | 記憶重要性 |
|------|----------|------------|------------|
| 一般相遇 | 雙方 aggression ≤ 0.7 | `"interaction"` | 0.5 |
| 衝突相遇 | 任一方 aggression > 0.7 | `"conflict"` | 0.8 |
| Agent 死亡 | `check_survival()` 返回 False | `"death"` | — |

| 談判結果 | 條件 | relationship 變化 |
|----------|------|------------------|
| 成功 | `success_prob > 0.5` | 雙方 +0.1（上限 1.0）|
| 失敗 | `success_prob <= 0.5` | 不變 |

> [!NOTE]
> `success_prob` 計算公式：`(loyalty1 + loyalty2) / 2 - (aggression1 + aggression2) / 4`
> 數值範圍大約在 -0.15 ~ 0.75 之間，0.5 是合理的分界線。

---

*文件版本：1.0 | 對應 Architecture.md 最後更新：2026-05-25*
