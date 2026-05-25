# Module M5：Rules Engine（規則引擎）

## 你的任務

實作世界底層規則引擎，負責驗證所有 Agent 行動是否合法、每 tick 套用資源消耗與再生規則、執行經濟邏輯，以及判斷 Agent 是否存活，確保世界不因 AI 行為失控而崩壞。

---

## 負責範圍

- **負責：**
  - 定義並管理所有底層遊戲規則（資源消耗、行動合法性、經濟限制）
  - 驗證 Agent 的行動字串是否符合規則，返回允許/拒絕及原因
  - 每 tick 套用每個 Agent 的資源自然消耗（food、water、energy 遞減）
  - 每 tick 套用地點資源自然再生（每地點 +2，上限 1000）
  - 套用交易手續費（10%）及確保 money 不為負數等經濟規則
  - 判斷 Agent 是否因資源耗盡而死亡（food <= 0 或 water <= 0）
  - 提供所有規則摘要（供 M7 視覺化或 M8 整合測試使用）

- **不負責：**
  - 儲存世界狀態到資料庫（由 M1 負責）
  - 驅動 Agent 思考或行動（由 M2 負責）
  - 管理 tick 推進（由 M6 負責）
  - 執行實際交易的資源轉移（由 M4 負責，M5 只做驗證）
  - 記憶系統（由 M3 負責）

---

## 依賴關係

- **需要先完成：**
  - M0（提供 `config.json`）
  - M1（提供 `get_world_state()`，M5 讀取世界狀態作為驗證依據）

- **被以下模組使用：**
  - M2（Agent 行動前呼叫 `validate_action()`）
  - M4（多 Agent 互動時呼叫 `validate_action()`、`apply_resource_decay()`、`apply_economic_rules()`）
  - M6（每 tick 呼叫 `apply_resource_decay()`、`check_survival()`）
  - M8（整合測試呼叫所有對外函數）

---

## 工作目錄

```
c:\Users\zohanlin\Documents\zohan_ai_test\AI_World\modules\m5_rules\
```

---

## 環境安裝

```bash
pip install pydantic
```

> **注意：** 本模組使用 **Pydantic v2**。請確認版本：
> ```bash
> python -c "import pydantic; print(pydantic.__version__)"
> ```
> 版本應為 `2.x.x`。

---

## 需要建立的檔案

```
AI_World/
└── modules/
    └── m5_rules/
        └── main.py          ← 唯一需要建立的檔案
```

> **注意：** 不需要建立 `__init__.py`，直接從 `modules/m5_rules/main.py` import 即可。

---

## 共用 Schema（直接使用，不可修改）

> 必須從 `shared/schemas.py` import，**不可在 m5_rules/main.py 內自行重新定義這些 class**。

```python
# shared/schemas.py 的完整內容（僅供參考，直接 import 使用）

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
    hunger: float = 0.3
    fear: float = 0.3
    ambition: float = 0.5
    loyalty: float = 0.5
    aggression: float = 0.3


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
    age: int = 0  # 單位：tick


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

> 這些函數是 M5 對其他模組的公開承諾。**函數名稱、參數型別、回傳型別一律不得更改。** 內部邏輯可自由實作。

```python
def validate_action(agent: Agent, action: str) -> tuple[bool, str]:
    """
    驗證 Agent 的行動字串是否合法。
    - 返回 (True, "") 表示行動合法，可以執行
    - 返回 (False, "原因說明") 表示行動非法，說明原因
    """

def apply_resource_decay(world_state: WorldState) -> WorldState:
    """
    每 tick 套用資源自然消耗規則到所有存活的 Agent，以及地點資源自然再生。
    返回更新後的 WorldState（不直接寫入資料庫，由呼叫方決定是否存檔）。
    """

def check_survival(agent: Agent) -> bool:
    """
    檢查 Agent 是否存活。
    - food <= 0 或 water <= 0 → 返回 False（死亡）
    - 否則返回 True（存活）
    """

def apply_economic_rules(world_state: WorldState) -> WorldState:
    """
    套用經濟規則，確保各地點資源不超過上限，money 不為負數等。
    返回更新後的 WorldState。
    """

def get_rules_summary() -> dict:
    """
    返回所有規則的摘要 dict，供視覺化或整合測試使用。
    格式範例：
    {
        "resource_decay": {...},
        "action_rules": {...},
        "economic_rules": {...},
        "survival_rules": {...}
    }
    """
```

---

## 你可以呼叫的外部函數

```python
# 從 M1 取得當前世界狀態（若需要地形資訊做行動驗證）
from modules.m1_world_state.main import get_world_state
```

> **使用注意：**
> - `get_world_state()` 返回 `WorldState` 物件
> - 取得地點地形資訊：`world_state.locations[location_id].terrain`
> - 取得地點是否存在：`location_id in world_state.locations`
> - **不要在 M5 內直接操作資料庫**，只透過 M1 介面取得資料

---

## 規則定義（完整規格）

### 一、資源消耗規則（每 tick，apply_resource_decay 套用）

| 資源 | 基本消耗 | 特殊條件 |
|------|---------|---------|
| food | -5 / tick | 若 Agent 所在地形為 `forest` → -3（森林有野生食物） |
| water | -4 / tick | 無特殊條件 |
| energy | -3 / tick | 若 Agent 處於「休息」狀態 → -1（休息消耗較少） |
| money | 不自然消耗 | 只在交易時變動 |
| materials | 不自然消耗 | 只在行動時變動 |

> **判斷「休息狀態」的方式：** 解析最近的 action 字串，若包含 `"休息"` 或 `"rest"` 則視為休息狀態。
> 若無法判斷，預設使用基本消耗值（-3）。

### 二、行動驗證規則（validate_action 檢查）

| 行動關鍵字 | 合法條件 | 非法時的錯誤說明 |
|-----------|---------|----------------|
| `採集食物` | Agent 所在地形必須是 `forest` 或 `plains` | `"採集食物只能在森林或平原地形執行"` |
| `移動` | action 字串中的目標地點 ID 必須存在於 WorldState | `"目標地點不存在於世界"` |
| `交易` | 必須指定對象；雙方 money 扣除後不得為負數 | `"交易對象未指定"` 或 `"資源不足無法交易"` |
| 任何行動 | 執行後 Agent 的 money 不得變為負數 | `"執行此行動將導致 money 為負數"` |

> **行動字串解析說明：**
> - 行動字串是 LLM 產生的自然語言描述，例如：`"我要移動到 loc_abc1"`、`"我要採集食物"`、`"我要和 Agent_xyz 交易 20 food"`
> - 使用 `in` 操作或 `str.find()` 做關鍵字匹配即可，不需要複雜解析
> - 無法識別的行動類型，預設返回 `(True, "")` 允許執行

### 三、經濟規則（apply_economic_rules 套用）

| 規則 | 說明 |
|------|------|
| 交易手續費 | 交易時收取交易金額的 10%，從 money 扣除 |
| 地點資源上限 | 每個地點 Location 的所有資源欄位上限為 1000.0 |
| 資源自然再生 | 每 tick 每個地點的 food/water/materials 各 +2（不超過上限） |
| money 下限 | 任何情況下 Agent 的 money 不得低於 0.0 |

---

## 實作步驟

### 步驟 1：建立檔案並設定 import

在 `c:\Users\zohanlin\Documents\zohan_ai_test\AI_World\modules\m5_rules\main.py` 建立以下骨架：

```python
# modules/m5_rules/main.py
"""
M5 — Rules Engine（規則引擎）
負責：行動驗證、資源消耗、存活判斷、經濟規則
"""

import sys
import os

# 讓 Python 找得到 shared/ 和 modules/
# 此模組從 AI_World/ 根目錄執行
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from shared.schemas import Agent, WorldState, Resource, Location, WorldEvent
from modules.m1_world_state.main import get_world_state

# ── 常數定義（規則參數集中管理）──────────────────────────────────────

# 資源消耗規則
FOOD_DECAY_DEFAULT = 5.0       # 一般地形每 tick 消耗
FOOD_DECAY_FOREST = 3.0        # 森林地形每 tick 消耗（有野生食物）
WATER_DECAY = 4.0              # 每 tick 消耗
ENERGY_DECAY_DEFAULT = 3.0     # 一般狀態每 tick 消耗
ENERGY_DECAY_RESTING = 1.0     # 休息狀態每 tick 消耗

# 經濟規則
TRADE_FEE_RATE = 0.10          # 交易手續費 10%
LOCATION_RESOURCE_MAX = 1000.0 # 地點資源上限
RESOURCE_REGEN_PER_TICK = 2.0  # 地點資源每 tick 自然再生量
MONEY_MIN = 0.0                # money 最低值
```

---

### 步驟 2：實作 `validate_action()`

```python
def validate_action(agent: Agent, action: str) -> tuple[bool, str]:
    """
    驗證 Agent 的行動字串是否合法。
    返回 (True, "") 表示允許；返回 (False, "原因") 表示拒絕。
    """
    # 1. 取得當前世界狀態（用於地形與地點驗證）
    world_state = get_world_state()

    # 2. 取得 Agent 當前地點的地形
    current_location = world_state.locations.get(agent.location_id)
    current_terrain = current_location.terrain if current_location else "unknown"

    # 3. 採集食物：只能在 forest 或 plains
    if "採集食物" in action:
        # TODO: 檢查 current_terrain 是否為 "forest" 或 "plains"
        # 若不是，返回 (False, "採集食物只能在森林或平原地形執行")
        pass

    # 4. 移動：目標地點必須存在
    if "移動" in action:
        # TODO: 從 action 字串解析出目標地點 ID
        # 提示：可用 action.split() 分割後尋找疑似 location_id 的 token
        # 若目標地點不在 world_state.locations 中，返回 (False, "目標地點不存在於世界")
        pass

    # 5. 交易：必須有對象且不能讓 money 變負
    if "交易" in action:
        # TODO: 檢查 action 是否提到交易對象（包含 Agent id 或名字）
        # TODO: 嘗試解析交易金額，確保 agent.resources.money - 金額 >= MONEY_MIN
        # 若金額不明，預設允許（返回 True）
        pass

    # 6. 通用規則：任何行動不得讓 money 變負
    # （此處為保守估計，若無法解析金額則跳過）

    # 7. 所有規則通過，允許行動
    return (True, "")
```

---

### 步驟 3：實作 `apply_resource_decay()`

```python
def apply_resource_decay(world_state: WorldState) -> WorldState:
    """
    每 tick 套用資源自然消耗（對 Agent）與自然再生（對地點）。
    直接修改傳入的 WorldState 並返回。
    """
    # ── 對每個存活的 Agent 套用資源消耗 ──
    for agent_id, agent in world_state.agents.items():
        if not agent.is_alive:
            continue  # 已死亡的 Agent 跳過

        # 1. 取得 Agent 所在地形
        location = world_state.locations.get(agent.location_id)
        terrain = location.terrain if location else "unknown"

        # 2. 計算 food 消耗
        # TODO: 若 terrain == "forest" 則使用 FOOD_DECAY_FOREST，否則 FOOD_DECAY_DEFAULT
        food_decay = ...

        # 3. 計算 energy 消耗
        # TODO: 解析 Agent 的最新 action（此資訊暫時無法從 WorldState 直接取得）
        # 暫定：若 Agent 沒有任何記憶，預設使用 ENERGY_DECAY_DEFAULT
        # 進階：可在 WorldState.events 中找最新與此 Agent 相關的事件，
        #        若最新事件 description 包含 "休息" 或 "rest" 則使用 ENERGY_DECAY_RESTING
        energy_decay = ...

        # 4. 套用消耗（資源值不得低於 0）
        # TODO: 更新 agent.resources.food、water、energy
        # agent.resources.food = max(0.0, agent.resources.food - food_decay)
        # agent.resources.water = max(0.0, agent.resources.water - WATER_DECAY)
        # agent.resources.energy = max(0.0, agent.resources.energy - energy_decay)

        # 5. 更新 WorldState 中的 Agent
        world_state.agents[agent_id] = agent

    # ── 對每個地點套用資源自然再生 ──
    for loc_id, location in world_state.locations.items():
        # TODO: 對 food、water、materials 各 +RESOURCE_REGEN_PER_TICK，
        #        但不超過 LOCATION_RESOURCE_MAX
        # location.resources.food = min(LOCATION_RESOURCE_MAX, location.resources.food + RESOURCE_REGEN_PER_TICK)
        # 同樣處理 water、materials
        world_state.locations[loc_id] = location

    return world_state
```

---

### 步驟 4：實作 `check_survival()`

```python
def check_survival(agent: Agent) -> bool:
    """
    檢查 Agent 是否存活。
    - food <= 0 或 water <= 0 → 死亡，返回 False
    - 其他情況 → 存活，返回 True
    """
    # TODO: 檢查 agent.resources.food 和 agent.resources.water
    # 若任一 <= 0，返回 False
    # 否則返回 True
    pass
```

---

### 步驟 5：實作 `apply_economic_rules()`

```python
def apply_economic_rules(world_state: WorldState) -> WorldState:
    """
    套用經濟規則：
    1. 確保所有 Agent 的 money 不低於 MONEY_MIN（0.0）
    2. 確保所有地點的資源不超過 LOCATION_RESOURCE_MAX（1000.0）
    3. 交易手續費在交易發生時由 validate_action / M4 處理，
       此函數做事後清理（夾在 0 到上限之間）
    """
    # ── 對每個 Agent ──
    for agent_id, agent in world_state.agents.items():
        if not agent.is_alive:
            continue

        # TODO: 確保 money 不為負數
        # agent.resources.money = max(MONEY_MIN, agent.resources.money)

        world_state.agents[agent_id] = agent

    # ── 對每個地點 ──
    for loc_id, location in world_state.locations.items():
        # TODO: 確保所有資源欄位在 [0, LOCATION_RESOURCE_MAX] 之間
        # location.resources.food = min(LOCATION_RESOURCE_MAX, max(0.0, location.resources.food))
        # 同樣處理 water、energy、money、materials
        world_state.locations[loc_id] = location

    return world_state
```

---

### 步驟 6：實作 `get_rules_summary()`

```python
def get_rules_summary() -> dict:
    """
    返回所有規則的 dict 摘要，供視覺化（M7）或整合測試（M8）使用。
    """
    return {
        "resource_decay": {
            "food_decay_default": FOOD_DECAY_DEFAULT,
            "food_decay_forest": FOOD_DECAY_FOREST,
            "water_decay": WATER_DECAY,
            "energy_decay_default": ENERGY_DECAY_DEFAULT,
            "energy_decay_resting": ENERGY_DECAY_RESTING,
            "description": "每 tick 對存活 Agent 套用資源消耗；森林地形食物消耗較少；休息狀態體力消耗較少"
        },
        "action_rules": {
            # TODO: 補充行動驗證規則的說明
            "採集食物": "只能在 forest 或 plains 地形執行",
            "移動": "目標地點必須存在於世界",
            "交易": "必須指定對象，且雙方資源充足",
            "通用": "任何行動不得使 money 低於 0"
        },
        "economic_rules": {
            "trade_fee_rate": TRADE_FEE_RATE,
            "location_resource_max": LOCATION_RESOURCE_MAX,
            "resource_regen_per_tick": RESOURCE_REGEN_PER_TICK,
            "money_min": MONEY_MIN,
            "description": "交易收取 10% 手續費；地點資源上限 1000；每 tick 地點資源自然再生 +2"
        },
        "survival_rules": {
            "death_conditions": ["food <= 0", "water <= 0"],
            "description": "food 或 water 耗盡時 Agent 死亡"
        }
    }
```

---

### 步驟 7：加入輔助函數（可選，提升可讀性）

以下是建議的 private 輔助函數，放在對外函數之前：

```python
def _get_agent_terrain(agent: Agent, world_state: WorldState) -> str:
    """取得 Agent 所在地點的地形，若地點不存在則返回 'unknown'"""
    location = world_state.locations.get(agent.location_id)
    return location.terrain if location else "unknown"


def _is_agent_resting(agent: Agent, world_state: WorldState) -> bool:
    """
    判斷 Agent 是否處於休息狀態。
    策略：在 WorldState.events 中找最近一筆與此 Agent 相關的事件，
    若 description 包含 '休息' 或 'rest' 則返回 True。
    """
    # 從最新的事件往回找
    for event in reversed(world_state.events):
        if agent.id in event.affected_agent_ids:
            desc = event.description.lower()
            if "休息" in desc or "rest" in desc:
                return True
            else:
                return False  # 找到最近事件但不是休息
    return False  # 沒有歷史事件，預設非休息


def _parse_trade_amount(action: str) -> float:
    """
    從行動字串解析交易金額。
    例如："我要和 Agent_xyz 交易 20 food" → 返回 20.0
    若解析失敗返回 0.0
    """
    # TODO: 用 re 或 split 解析數字
    import re
    numbers = re.findall(r'\d+\.?\d*', action)
    if numbers:
        return float(numbers[0])
    return 0.0
```

---

### 步驟 8：確認 import 路徑正確

在執行任何測試之前，先確認 Python 能找到 `shared.schemas` 和 `modules.m1_world_state.main`：

```python
# 在 AI_World/ 根目錄執行
python -c "from modules.m5_rules.main import get_rules_summary; print(get_rules_summary())"
```

若出現 `ModuleNotFoundError`，確認：
1. 你是在 `c:\Users\zohanlin\Documents\zohan_ai_test\AI_World\` 執行 Python
2. `shared/schemas.py` 已存在
3. `m5_rules/main.py` 中的 `sys.path.insert(0, ROOT_DIR)` 正確設定

---

## 驗證標準（全部通過才算完成）

請逐一執行以下測試，確認結果符合預期。**全部通過才算完成。**

```python
# 驗證腳本：在 AI_World/ 根目錄執行
# python verify_m5.py

from shared.schemas import Agent, AgentPersonality, Resource, Location, WorldState
from modules.m5_rules.main import (
    validate_action,
    apply_resource_decay,
    check_survival,
    apply_economic_rules,
    get_rules_summary
)

print("=== M5 Rules Engine 驗證 ===\n")

# ── 建立測試用資料 ──────────────────────────────────────────────────

forest_location = Location(id="loc_forest", name="Deep Forest", x=0, y=0, terrain="forest")
plains_location = Location(id="loc_plains", name="Open Plains", x=1, y=0, terrain="plains")
mountain_location = Location(id="loc_mountain", name="High Mountain", x=2, y=0, terrain="mountain")

test_agent = Agent(
    id="agent_001",
    name="TestAgent",
    location_id="loc_plains",
    resources=Resource(food=50.0, water=50.0, energy=50.0, money=100.0, materials=20.0)
)

world = WorldState(
    tick=1,
    locations={
        "loc_forest": forest_location,
        "loc_plains": plains_location,
        "loc_mountain": mountain_location,
    },
    agents={"agent_001": test_agent}
)

# ── 驗證 1：validate_action() 對非法行動返回 (False, 原因說明) ──────

# 測試 1a：在山地採集食物（非法）
agent_in_mountain = test_agent.model_copy(update={"location_id": "loc_mountain"})
ok, reason = validate_action(agent_in_mountain, "我要採集食物")
assert ok == False, "❌ 測試 1a 失敗：山地採集食物應被拒絕"
assert reason != "", "❌ 測試 1a 失敗：拒絕原因不得為空字串"
print(f"✅ 測試 1a 通過：山地採集食物被拒絕，原因：{reason}")

# 測試 1b：移動到不存在的地點（非法）
ok, reason = validate_action(test_agent, "我要移動到 loc_nonexistent")
assert ok == False, "❌ 測試 1b 失敗：移動到不存在地點應被拒絕"
print(f"✅ 測試 1b 通過：移動到不存在地點被拒絕，原因：{reason}")

# ── 驗證 2：validate_action() 對合法行動返回 (True, "") ──────────────

# 測試 2a：在森林採集食物（合法）
agent_in_forest = test_agent.model_copy(update={"location_id": "loc_forest"})
ok, reason = validate_action(agent_in_forest, "我要採集食物")
assert ok == True, f"❌ 測試 2a 失敗：森林採集食物應被允許，但被拒絕：{reason}"
assert reason == "", f"❌ 測試 2a 失敗：合法行動原因應為空字串，但為：{reason}"
print(f"✅ 測試 2a 通過：森林採集食物被允許")

# 測試 2b：在平原採集食物（合法）
ok, reason = validate_action(test_agent, "我要採集食物")  # test_agent 在 plains
assert ok == True, f"❌ 測試 2b 失敗：平原採集食物應被允許"
print(f"✅ 測試 2b 通過：平原採集食物被允許")

# 測試 2c：移動到存在的地點（合法）
ok, reason = validate_action(test_agent, "我要移動到 loc_forest")
assert ok == True, f"❌ 測試 2c 失敗：移動到存在地點應被允許，但被拒絕：{reason}"
print(f"✅ 測試 2c 通過：移動到存在地點被允許")

# ── 驗證 3：apply_resource_decay() 後資源正確減少 ──────────────────

import copy
world_copy = copy.deepcopy(world)  # test_agent 在 plains
world_after = apply_resource_decay(world_copy)
agent_after = world_after.agents["agent_001"]

# 平原地形 food 應減少 5（50 - 5 = 45）
assert agent_after.resources.food == 45.0, \
    f"❌ 測試 3a 失敗：平原地形 food 應為 45.0，實際：{agent_after.resources.food}"
print(f"✅ 測試 3a 通過：平原地形 food 消耗 5，結果 {agent_after.resources.food}")

# water 應減少 4（50 - 4 = 46）
assert agent_after.resources.water == 46.0, \
    f"❌ 測試 3b 失敗：water 應為 46.0，實際：{agent_after.resources.water}"
print(f"✅ 測試 3b 通過：water 消耗 4，結果 {agent_after.resources.water}")

# 森林地形 food 應只減少 3
world_forest = WorldState(
    tick=1,
    locations={"loc_forest": forest_location},
    agents={"agent_002": Agent(
        id="agent_002", name="ForestAgent", location_id="loc_forest",
        resources=Resource(food=50.0, water=50.0, energy=50.0, money=100.0)
    )}
)
world_forest_after = apply_resource_decay(world_forest)
forest_agent_after = world_forest_after.agents["agent_002"]
assert forest_agent_after.resources.food == 47.0, \
    f"❌ 測試 3c 失敗：森林地形 food 應為 47.0，實際：{forest_agent_after.resources.food}"
print(f"✅ 測試 3c 通過：森林地形 food 只消耗 3，結果 {forest_agent_after.resources.food}")

# ── 驗證 4：check_survival() 在 food <= 0 時返回 False ──────────────

dead_by_food = test_agent.model_copy(
    update={"resources": Resource(food=0.0, water=50.0, energy=50.0, money=100.0)}
)
assert check_survival(dead_by_food) == False, "❌ 測試 4a 失敗：food=0 應返回 False"
print(f"✅ 測試 4a 通過：food=0 返回 False（死亡）")

dead_by_water = test_agent.model_copy(
    update={"resources": Resource(food=50.0, water=0.0, energy=50.0, money=100.0)}
)
assert check_survival(dead_by_water) == False, "❌ 測試 4b 失敗：water=0 應返回 False"
print(f"✅ 測試 4b 通過：water=0 返回 False（死亡）")

healthy_agent = test_agent.model_copy(
    update={"resources": Resource(food=10.0, water=10.0, energy=50.0, money=100.0)}
)
assert check_survival(healthy_agent) == True, "❌ 測試 4c 失敗：food=10 water=10 應返回 True"
print(f"✅ 測試 4c 通過：food=10 water=10 返回 True（存活）")

# ── 驗證 5：apply_economic_rules() 確保 money 不為負數 ──────────────

negative_money_agent = test_agent.model_copy(
    update={"resources": Resource(food=50.0, water=50.0, energy=50.0, money=-10.0)}
)
world_eco = WorldState(
    tick=1,
    locations={"loc_plains": plains_location},
    agents={"agent_eco": negative_money_agent.model_copy(update={"id": "agent_eco", "location_id": "loc_plains"})}
)
world_eco_after = apply_economic_rules(world_eco)
assert world_eco_after.agents["agent_eco"].resources.money >= 0.0, \
    f"❌ 測試 5 失敗：apply_economic_rules 後 money 應 >= 0，實際：{world_eco_after.agents['agent_eco'].resources.money}"
print(f"✅ 測試 5 通過：apply_economic_rules 確保 money >= 0")

# ── 驗證 6：get_rules_summary() 返回 dict 且包含必要 key ──────────────

summary = get_rules_summary()
assert isinstance(summary, dict), "❌ 測試 6 失敗：get_rules_summary() 應返回 dict"
required_keys = ["resource_decay", "action_rules", "economic_rules", "survival_rules"]
for key in required_keys:
    assert key in summary, f"❌ 測試 6 失敗：summary 缺少 key '{key}'"
print(f"✅ 測試 6 通過：get_rules_summary() 返回包含所有必要 key 的 dict")

print("\n🎉 M5 所有驗證通過！")
```

### 執行驗證

```bash
# 在 AI_World/ 根目錄執行
cd c:\Users\zohanlin\Documents\zohan_ai_test\AI_World
python verify_m5.py
```

預期輸出（全部 ✅）：

```
=== M5 Rules Engine 驗證 ===

✅ 測試 1a 通過：山地採集食物被拒絕，原因：採集食物只能在森林或平原地形執行
✅ 測試 1b 通過：移動到不存在地點被拒絕，原因：目標地點不存在於世界
✅ 測試 2a 通過：森林採集食物被允許
✅ 測試 2b 通過：平原採集食物被允許
✅ 測試 2c 通過：移動到存在地點被允許
✅ 測試 3a 通過：平原地形 food 消耗 5，結果 45.0
✅ 測試 3b 通過：water 消耗 4，結果 46.0
✅ 測試 3c 通過：森林地形 food 只消耗 3，結果 47.0
✅ 測試 4a 通過：food=0 返回 False（死亡）
✅ 測試 4b 通過：water=0 返回 False（死亡）
✅ 測試 4c 通過：food=10 water=10 返回 True（存活）
✅ 測試 5 通過：apply_economic_rules 確保 money >= 0
✅ 測試 6 通過：get_rules_summary() 返回包含所有必要 key 的 dict

🎉 M5 所有驗證通過！
```

---

## 注意事項與常見錯誤

> [!IMPORTANT]
> **不可在 M5 內直接讀寫資料庫。** 所有資料存取必須透過 M1 的 `get_world_state()`。M5 的函數修改完 WorldState 物件後，交由呼叫方（M4/M6）決定是否呼叫 M1 的 `update_agent()` 或 `save_state()` 存檔。

> [!WARNING]
> **apply_resource_decay() 和 apply_economic_rules() 修改的是傳入的 WorldState 物件。** 若呼叫方需要保留原始狀態做比對，應在呼叫前自行 `copy.deepcopy(world_state)`。

> [!TIP]
> 行動字串解析建議優先用 `in` 關鍵字判斷，不要用複雜正則表達式，以免 LLM 輸出格式稍有變化就全部失效。例如：`if "採集食物" in action` 比 `re.match(r'採集食物', action)` 更穩健。

> [!NOTE]
> `validate_action()` 每次呼叫都會呼叫 `get_world_state()` 讀取最新世界狀態，若 M1 尚未完成則此函數無法使用。請確保 M1 已完成並可正常運作。

---

*文件版本：1.0 | 對應 Architecture.md 版本：2026-05-25*
