# Module M6：Time & History（時間與歷史系統）

## 你的任務

實作世界的時間推進與歷史記錄機制，負責 tick → season → year 的轉換、定期儲存世界快照、以及提供其他模組查詢過去事件與時間軸的能力。

---

## 負責範圍

- **負責：**
  - 管理世界時間（tick、season、year）的推進邏輯
  - 季節切換規則（spring → summer → autumn → winter → spring）
  - 每 10 tick 自動儲存一次世界快照
  - 每個季節結束時強制儲存快照
  - 快照的寫入（`data/snapshots/snapshot_{tick}.json`）與讀取
  - 提供指定 tick 範圍的歷史事件查詢
  - 提供重大事件時間軸（`get_timeline()`）
  - 提供當前季節查詢（`get_current_season()`）

- **不負責：**
  - Agent 行為的執行（由 M2、M4 負責）
  - 資源消耗規則的套用（由 M5 負責；但 M6 推進 tick 時需提示 M5 執行）
  - 向量記憶體的管理（由 M3 負責）
  - 視覺化介面（由 M7 負責）
  - Agent 的建立與刪除（由 M2 負責）

---

## 依賴關係

- **需要先完成：**
  - M0（產出 `config.json`，M6 讀取 `tick_interval_sec` 等參數）
  - M1（提供 `get_world_state()`、`get_tick()`、`save_state()`）
  - M3（提供 `save_world_event()`、`search_history()`）

- **被以下模組使用：**
  - M7（Streamlit 視覺化介面直接呼叫 `get_timeline()`、`get_snapshot()`）
  - M8（整合測試會呼叫 M6 所有對外函數）

---

## 工作目錄

```
c:\Users\zohanlin\Documents\zohan_ai_test\AI_World\modules\m6_time_history\
```

所有程式碼寫在此目錄下。執行程式時，**工作目錄（cwd）必須設定在專案根目錄**：
```
c:\Users\zohanlin\Documents\zohan_ai_test\AI_World\
```
這樣 `from shared.schemas import *` 與 `from modules.m1_world_state.main import ...` 等 import 才能正確解析。

---

## 環境安裝

```bash
pip install pydantic
```

> **注意：** M1 和 M3 已有其他依賴（SQLite、ChromaDB 等），請確保它們的環境也已安裝完成，M6 才能正確呼叫它們的函數。

---

## 需要建立的檔案

```
AI_World/
├── modules/
│   └── m6_time_history/
│       └── main.py          ← 你需要實作的主檔案
└── data/
    └── snapshots/           ← 快照輸出目錄（程式執行時自動建立，不需手動建立）
        ├── snapshot_0.json
        ├── snapshot_10.json
        └── ...
```

> **不需要建立 `data/snapshots/` 目錄**，程式啟動時用 `os.makedirs(..., exist_ok=True)` 自動建立即可。

---

## 共用 Schema（直接使用，不可修改）

> 從 `shared/schemas.py` import，**不可自行定義替代 class**。

以下是 M6 會用到的 Schema：

```python
# shared/schemas.py（節錄）

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
    age: int = 0


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

> 以下函數名稱、參數型別、回傳型別**一律不可更改**。內部邏輯自由實作。

```python
# modules/m6_time_history/main.py

def advance_tick() -> int:
    """推進世界時間一個 tick，更新季節/年份，返回新 tick 數"""

def get_history(start_tick: int, end_tick: int) -> list[WorldEvent]:
    """取得指定 tick 範圍的歷史事件"""

def save_snapshot() -> None:
    """儲存當前世界狀態快照到 data/snapshots/snapshot_{tick}.json"""

def get_snapshot(tick: int) -> Optional[WorldState]:
    """取得指定 tick 的世界快照，若不存在返回 None"""

def get_timeline() -> list[dict]:
    """返回所有重大事件的時間軸列表 [{tick, event_type, description}]"""

def get_current_season() -> str:
    """返回當前季節 'spring' | 'summer' | 'autumn' | 'winter'"""
```

---

## 你可以呼叫的外部函數

```python
# 從 M1 取得世界狀態與時間
from modules.m1_world_state.main import get_world_state, get_tick, save_state

# 從 M3 存取世界事件向量記憶
from modules.m3_memory.main import save_world_event, search_history
```

### 外部函數說明

| 函數 | 說明 |
|------|------|
| `get_world_state() -> WorldState` | 讀取當前完整世界狀態（含所有 agents、events 等） |
| `get_tick() -> int` | 取得當前 tick 數 |
| `save_state() -> None` | 將當前世界狀態序列化並儲存到 M1 的資料庫 |
| `save_world_event(event: WorldEvent) -> None` | 將世界事件存入 ChromaDB，供語意搜尋 |
| `search_history(query: str, top_k: int = 10) -> list[WorldEvent]` | 語意搜尋歷史事件 |

---

## 時間規則（核心邏輯）

```
1 tick = 1 天

每 30 tick = 1 個季節，順序為：
  spring（tick 0~29）→ summer（tick 30~59）→ autumn（tick 60~89）→ winter（tick 90~119）

每 120 tick = 1 年（4 個季節走完後，year +1，重新從 spring 開始）

季節對資源消耗的影響（告知 M5 或在 advance_tick 中記錄）：
  - winter：food 消耗 +20%
  - summer：water 消耗 +20%
  （M6 本身不直接修改 Agent 資源，應在 advance_tick 中建立 WorldEvent 告知 M5）
```

### 季節判斷公式

```python
SEASONS = ["spring", "summer", "autumn", "winter"]
TICKS_PER_SEASON = 30
TICKS_PER_YEAR = 120

def _calculate_season(tick: int) -> str:
    season_index = (tick % TICKS_PER_YEAR) // TICKS_PER_SEASON
    return SEASONS[season_index]

def _calculate_year(tick: int) -> int:
    return (tick // TICKS_PER_YEAR) + 1
```

---

## 快照儲存格式

- **儲存位置：** `data/snapshots/snapshot_{tick}.json`
- **格式：** Pydantic `WorldState` 序列化後的 JSON（使用 `.model_dump_json()`）
- **自動儲存條件：**
  1. 每 10 tick 儲存一次（`tick % 10 == 0`）
  2. 每個季節結束時強制儲存（tick 為 29、59、89、119、149…，即 `(tick + 1) % 30 == 0`）

---

## 實作步驟

### Step 1：建立檔案與基本結構

建立 `modules/m6_time_history/main.py`，先寫好所有 import 與常數定義：

```python
# modules/m6_time_history/main.py

import os
import json
from typing import Optional
from datetime import datetime

from shared.schemas import WorldState, WorldEvent, gen_id
from modules.m1_world_state.main import get_world_state, get_tick, save_state
from modules.m3_memory.main import save_world_event, search_history

# ── 常數 ─────────────────────────────────────────────────
SEASONS = ["spring", "summer", "autumn", "winter"]
TICKS_PER_SEASON = 30
TICKS_PER_YEAR = 120
SNAPSHOT_INTERVAL = 10
SNAPSHOT_DIR = "data/snapshots"

# ── 初始化快照目錄 ─────────────────────────────────────────
os.makedirs(SNAPSHOT_DIR, exist_ok=True)
```

---

### Step 2：實作輔助函數（private）

這些函數只在模組內部使用，命名以底線開頭：

```python
def _calculate_season(tick: int) -> str:
    """根據 tick 計算當前季節"""
    # TODO: 使用 SEASONS 列表與 TICKS_PER_SEASON 計算
    season_index = ...  # 提示：(tick % TICKS_PER_YEAR) // TICKS_PER_SEASON
    return SEASONS[season_index]


def _calculate_year(tick: int) -> int:
    """根據 tick 計算當前年份（從第 1 年開始）"""
    # TODO: 計算年份
    return ...  # 提示：(tick // TICKS_PER_YEAR) + 1


def _is_season_end(tick: int) -> bool:
    """判斷當前 tick 是否為某季節的最後一天"""
    # TODO: 季節最後一天的條件
    return ...  # 提示：(tick + 1) % TICKS_PER_SEASON == 0


def _get_snapshot_path(tick: int) -> str:
    """返回指定 tick 的快照檔案路徑"""
    return os.path.join(SNAPSHOT_DIR, f"snapshot_{tick}.json")
```

---

### Step 3：實作 `advance_tick()`

這是 M6 最核心的函數，需要：
1. 從 M1 取得當前 tick
2. 計算新 tick、新季節、新年份
3. 如果季節切換，建立一個 `WorldEvent` 記錄
4. 將事件存入 M3 的向量記憶
5. 在適當時機觸發 `save_snapshot()`
6. 呼叫 M1 的 `save_state()` 更新資料庫

```python
def advance_tick() -> int:
    """
    推進世界時間一個 tick，更新季節/年份，返回新 tick 數。

    流程：
      1. 取得目前 tick（從 M1）
      2. new_tick = current_tick + 1
      3. 計算 new_season 與 new_year
      4. 若季節改變 → 建立 WorldEvent("season_change", ...)，存入 M3
      5. 若 new_tick % 10 == 0 → 呼叫 save_snapshot()
      6. 若 _is_season_end(new_tick - 1) → 呼叫 save_snapshot()（季節末強制儲存）
      7. 呼叫 M1 的 save_state()
      8. 返回 new_tick
    """
    current_tick = get_tick()
    new_tick = current_tick + 1

    old_season = _calculate_season(current_tick)
    new_season = _calculate_season(new_tick)
    new_year = _calculate_year(new_tick)

    # TODO: 季節切換時，建立 WorldEvent 並存入 M3
    if new_season != old_season:
        event = WorldEvent(
            tick=new_tick,
            event_type=...,        # 填入合適的 event_type
            description=...,       # 例如：f"Season changed to {new_season} in year {new_year}"
        )
        save_world_event(event)

    # TODO: 判斷是否需要儲存快照
    # 條件1：每 10 tick
    # 條件2：季節結束時（使用 _is_season_end）

    # TODO: 呼叫 M1 的 save_state()

    return new_tick
```

> **提示：** M1 的 `WorldState` 有 `tick`、`season`、`year` 欄位，但 M6 不直接修改 WorldState 物件——它通過 `save_state()` 讓 M1 持久化。若 M1 的 `save_state()` 不會自動更新 tick/season/year，需確認 M1 的實作方式，必要時在此先更新 WorldState 物件再呼叫 `save_state()`。

---

### Step 4：實作 `save_snapshot()` 與 `get_snapshot()`

```python
def save_snapshot() -> None:
    """
    將當前世界狀態儲存為 JSON 快照。

    流程：
      1. 呼叫 M1 的 get_world_state() 取得完整狀態
      2. 使用 WorldState.model_dump_json() 序列化
      3. 寫入 data/snapshots/snapshot_{tick}.json
    """
    world_state = get_world_state()
    tick = world_state.tick
    path = _get_snapshot_path(tick)

    # TODO: 序列化並寫入檔案
    json_str = world_state.model_dump_json(indent=2)
    with open(path, "w", encoding="utf-8") as f:
        ...


def get_snapshot(tick: int) -> Optional[WorldState]:
    """
    讀取指定 tick 的快照，不存在則返回 None。

    流程：
      1. 計算檔案路徑 _get_snapshot_path(tick)
      2. 若檔案不存在 → 返回 None
      3. 讀取 JSON → 使用 WorldState.model_validate_json() 解析
      4. 返回 WorldState 物件
    """
    path = _get_snapshot_path(tick)

    if not os.path.exists(path):
        return None

    # TODO: 讀取並解析 JSON
    with open(path, "r", encoding="utf-8") as f:
        ...

    return ...  # WorldState 物件
```

---

### Step 5：實作 `get_history()`

```python
def get_history(start_tick: int, end_tick: int) -> list[WorldEvent]:
    """
    取得 start_tick 到 end_tick（含）範圍內的所有世界事件。

    策略：
      1. 呼叫 M1 的 get_world_state()，從 world_state.events 取得所有事件
      2. 篩選出 tick 在 [start_tick, end_tick] 範圍內的事件
      3. 按 tick 排序後返回

    注意：若 M1 不儲存完整事件列表，可考慮掃描快照檔案合併事件。
    """
    world_state = get_world_state()

    # TODO: 篩選並排序事件
    filtered = [
        event for event in world_state.events
        if start_tick <= event.tick <= end_tick
    ]

    return sorted(filtered, key=lambda e: e.tick)
```

---

### Step 6：實作 `get_timeline()`

```python
def get_timeline() -> list[dict]:
    """
    返回所有重大事件的時間軸列表。

    每個項目格式：
      {
        "tick": int,
        "event_type": str,
        "description": str
      }

    重大事件定義（選擇以下任一策略）：
      - 策略A：返回所有 event_type 為 "season_change"、"conflict"、"death"、"discovery" 的事件
      - 策略B：返回 world_state.events 中所有事件（依 tick 排序）
      - 策略C：從掃描快照檔案中彙整

    建議使用策略A，讓時間軸只顯示「有意義」的事件。
    """
    world_state = get_world_state()

    MAJOR_EVENT_TYPES = {"season_change", "conflict", "death", "discovery"}

    # TODO: 篩選重大事件並格式化輸出
    timeline = []
    for event in sorted(world_state.events, key=lambda e: e.tick):
        if event.event_type in MAJOR_EVENT_TYPES:
            timeline.append({
                "tick": event.tick,
                "event_type": event.event_type,
                "description": event.description,
            })

    return timeline
```

---

### Step 7：實作 `get_current_season()`

```python
def get_current_season() -> str:
    """
    返回當前季節字串。

    流程：
      1. 呼叫 M1 的 get_tick() 取得 tick
      2. 使用 _calculate_season(tick) 計算季節
      3. 返回季節字串
    """
    tick = get_tick()
    return _calculate_season(tick)
```

---

### Step 8：模組層級初始化（可選）

如果需要在模組 import 時執行任何初始化（例如確保快照目錄存在），可在檔案最頂部或最底部加入：

```python
# 確保快照目錄存在（已在常數定義區執行，此處為備用）
def _ensure_snapshot_dir():
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)

_ensure_snapshot_dir()
```

---

## 驗證標準（全部通過才算完成）

> 在專案根目錄（`AI_World/`）下執行以下測試：

- [ ] **`advance_tick()` 回傳值正確**
  - 連續呼叫 3 次 `advance_tick()`，每次回傳值應比上次多 1
  - `advance_tick()` 應返回 `int` 型別

- [ ] **季節切換正確**
  - 從 tick 0 推進到 tick 30 時，`get_current_season()` 應從 `"spring"` 變為 `"summer"`
  - 從 tick 90 推進到 tick 120 時，應從 `"winter"` 變為 `"spring"` 並 year +1

- [ ] **`get_history(0, 10)` 正常運作**
  - 呼叫 `get_history(0, 10)` 應返回 `list[WorldEvent]`（可為空列表，但不能報錯）
  - 返回的事件 tick 均在 `[0, 10]` 範圍內

- [ ] **`save_snapshot()` 產生 JSON 檔案**
  - 呼叫 `save_snapshot()` 後，`data/snapshots/snapshot_{tick}.json` 應存在
  - 檔案內容為合法的 JSON，且可用 `WorldState.model_validate_json()` 解析

- [ ] **`get_snapshot(tick)` 能讀回快照**
  - 先呼叫 `save_snapshot()`，再呼叫 `get_snapshot(current_tick)` 應返回 `WorldState` 物件
  - 呼叫 `get_snapshot(99999)` 應返回 `None`（不存在的 tick）

- [ ] **`get_timeline()` 格式正確**
  - 呼叫 `get_timeline()` 應返回 `list[dict]`
  - 每個 dict 必須包含 `"tick"`、`"event_type"`、`"description"` 三個 key
  - tick 值為 `int`，event_type 與 description 為 `str`

- [ ] **`get_current_season()` 回傳正確字串**
  - 回傳值必須是 `"spring"`、`"summer"`、`"autumn"`、`"winter"` 其中之一
  - 不可回傳其他字串或 `None`

- [ ] **快照自動儲存觸發**
  - 推進到第 10 tick 時，`data/snapshots/snapshot_10.json` 應自動存在
  - 推進到第 29 tick 時（spring 結束），應有對應快照

- [ ] **不影響現有模組**
  - import `modules.m6_time_history.main` 不會觸發任何副作用（不會修改資料庫）
  - 如有 module-level 初始化，只允許建立目錄，不允許修改世界狀態

---

## 常見問題（FAQ）

**Q：`advance_tick()` 需要修改 M1 資料庫中的 tick 值嗎？**

A：需要確認 M1 的 `save_state()` 是否會將 tick/season/year 一起儲存。若 M1 的 WorldState 物件中這些欄位只在記憶體中，M6 需要先更新 WorldState 物件（修改 `.tick`、`.season`、`.year`），再呼叫 `save_state()`。

**Q：`get_history()` 如果 M1 的 events 列表太長怎麼辦？**

A：目前 MVP 階段直接從記憶體篩選即可。若未來效能有問題，可改為掃描快照檔案。

**Q：每 10 tick 儲存一次，如果 tick 10 同時也是季節末，要存幾次？**

A：只存一次，兩個條件都滿足時呼叫一次 `save_snapshot()` 即可（函數本身是冪等的）。

**Q：快照 JSON 格式的 datetime 欄位會有問題嗎？**

A：Pydantic v2 的 `model_dump_json()` 會自動處理 `datetime` 序列化。讀取時使用 `model_validate_json()` 即可正確解析，無需手動處理。

---

*文件版本：1.0 | 最後更新：2026-05-25*
