# Module M1：World State Engine（世界狀態引擎）

## 你的任務

實作以 SQLite 持久化儲存整個世界狀態的引擎，作為所有其他模組存取與修改世界資料的唯一入口，並提供 `init_world`、`get_world_state`、`update_agent`、`update_location_resources`、`add_event`、`get_tick`、`save_state`、`load_state` 等對外函數。

---

## 負責範圍

- **負責：**
  - 讀取 `config.json` 取得全域設定
  - 建立並管理 SQLite 資料庫（`data/world.db`）
  - 建立資料表：`locations`、`agents`、`organizations`、`events`、`world_meta`
  - 實作所有對外函數（見下方介面合約）
  - 世界初始化：預設建立 5 個地點（village、plains、mountain、forest、river）
  - 序列化（`save_state`）與反序列化（`load_state`）世界狀態

- **不負責：**
  - Agent 的思考邏輯（由 M2 負責）
  - 記憶向量搜尋（由 M3 負責）
  - 時間推進與季節計算（由 M6 負責）
  - 規則驗證與資源衰減計算（由 M5 負責）
  - 視覺化顯示（由 M7 負責）

---

## 依賴關係

- **需要先完成：**
  - **M0**（Setup）：M0 必須已執行完畢，`config.json` 必須存在於專案根目錄 `AI_World/config.json`

- **被以下模組使用：**
  - M2（Agent System）：呼叫 `get_world_state`、`update_agent`
  - M4（Multi-Agent Interaction）：呼叫 `get_world_state`、`add_event`、`get_tick`
  - M5（Rules Engine）：呼叫 `get_world_state`、`update_location_resources`
  - M6（Time & History）：呼叫 `get_tick`、`save_state`、`load_state`
  - M7（Visualization）：呼叫 `get_world_state`
  - M8（Integration）：呼叫 `init_world`、`get_world_state`

---

## 工作目錄

```
c:\Users\zohanlin\Documents\zohan_ai_test\AI_World\modules\m1_world_state\
```

> [!IMPORTANT]
> 所有相對路徑（如 `data/world.db`、`config.json`）均以專案根目錄 `AI_World/` 為基準。
> 請在程式中動態計算根目錄路徑，**不可硬編碼絕對路徑**。

---

## 環境安裝

```bash
pip install pydantic
```

> SQLite 為 Python 標準函式庫（`sqlite3`），**不需要額外安裝**。

---

## 需要建立的檔案

```
AI_World/
├── config.json                   ← 由 M0 產生，M1 讀取（勿修改）
├── shared/
│   └── schemas.py                ← 由 M0 或統一建立，M1 直接 import
├── data/
│   └── world.db                  ← 由 M1 init_world() 自動建立
└── modules/
    └── m1_world_state/
        ├── main.py               ← 對外函數（本模組的主要入口）
        └── database.py           ← SQLite 底層操作封裝
```

> [!NOTE]
> `data/` 目錄若不存在，程式需自動建立（使用 `os.makedirs`）。
> `shared/schemas.py` 需由開發者手動建立（貼上下方 Schema 內容），或由 M0 統一產生。

---

## 共用 Schema（直接使用，不可修改）

> 以下內容必須存放於 `AI_World/shared/schemas.py`，M1 使用 `from shared.schemas import *` 引入。

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

## 你對外提供的函數（簽名不可修改）

> 以下函數定義在 `modules/m1_world_state/main.py`，所有外部模組 import 此檔案呼叫。

```python
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

## 你可以呼叫的外部函數

M1 是最底層的基礎模組，**不依賴其他模組的函數**。

M1 唯一的外部依賴是 **讀取 `config.json` 檔案**（純 JSON，不呼叫任何其他模組）。

---

## 實作步驟

### Step 0：確認目錄結構

在開始前，確認以下目錄存在，若不存在則建立：

```
AI_World/shared/        ← 放 schemas.py
AI_World/data/          ← 放 world.db（程式自動建立）
AI_World/modules/m1_world_state/
```

確認 `config.json` 已存在於 `AI_World/config.json`。

---

### Step 1：建立 `shared/schemas.py`

將上方「共用 Schema」章節的完整程式碼貼入 `AI_World/shared/schemas.py`。

同時在 `AI_World/shared/` 建立空的 `__init__.py`，讓 `shared` 成為 Python package：

```python
# shared/__init__.py
# 空檔案即可
```

---

### Step 2：實作 `database.py`（SQLite 底層操作）

`database.py` 負責所有 SQLite 的 CRUD 操作。使用 JSON 欄位（`TEXT` 型別）儲存巢狀資料（如 `resources`、`personality`、`skills` 等）。

**資料表設計：**

| 資料表 | 用途 |
|--------|------|
| `world_meta` | 儲存 tick、year、season 等全域狀態（單一 row） |
| `locations` | 儲存所有地點資料 |
| `agents` | 儲存所有 Agent 資料 |
| `organizations` | 儲存所有組織資料 |
| `events` | 儲存所有世界事件 |

**Code Skeleton：**

```python
# modules/m1_world_state/database.py
import sqlite3
import json
import os
from pathlib import Path

# 計算專案根目錄（AI_World/）
ROOT_DIR = Path(__file__).resolve().parents[2]
DB_PATH = ROOT_DIR / "data" / "world.db"


def get_connection() -> sqlite3.Connection:
    """建立並回傳資料庫連線（啟用 WAL 模式以提升並發性能）"""
    os.makedirs(DB_PATH.parent, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row  # 讓結果可以用欄位名稱存取
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def create_tables() -> None:
    """建立所有資料表（若已存在則略過）"""
    conn = get_connection()
    with conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS world_meta (
                id      INTEGER PRIMARY KEY CHECK (id = 1),  -- 永遠只有一筆
                tick    INTEGER NOT NULL DEFAULT 0,
                year    INTEGER NOT NULL DEFAULT 1,
                season  TEXT    NOT NULL DEFAULT 'spring'
            );

            CREATE TABLE IF NOT EXISTS locations (
                id        TEXT PRIMARY KEY,
                name      TEXT NOT NULL,
                x         INTEGER NOT NULL,
                y         INTEGER NOT NULL,
                terrain   TEXT NOT NULL,
                resources TEXT NOT NULL  -- JSON
            );

            CREATE TABLE IF NOT EXISTS agents (
                id              TEXT PRIMARY KEY,
                name            TEXT NOT NULL,
                location_id     TEXT NOT NULL,
                personality     TEXT NOT NULL,  -- JSON
                resources       TEXT NOT NULL,  -- JSON
                skills          TEXT NOT NULL,  -- JSON
                relationships   TEXT NOT NULL,  -- JSON
                memory_ids      TEXT NOT NULL,  -- JSON array
                organization_id TEXT,
                is_alive        INTEGER NOT NULL DEFAULT 1,
                age             INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS organizations (
                id          TEXT PRIMARY KEY,
                name        TEXT NOT NULL,
                type        TEXT NOT NULL,
                member_ids  TEXT NOT NULL,  -- JSON array
                leader_id   TEXT,
                resources   TEXT NOT NULL,  -- JSON
                territory   TEXT NOT NULL   -- JSON array
            );

            CREATE TABLE IF NOT EXISTS events (
                id                   TEXT PRIMARY KEY,
                tick                 INTEGER NOT NULL,
                event_type           TEXT NOT NULL,
                description          TEXT NOT NULL,
                affected_agent_ids   TEXT NOT NULL,  -- JSON array
                affected_location_ids TEXT NOT NULL, -- JSON array
                timestamp            TEXT NOT NULL
            );
        """)
    conn.close()


def upsert_world_meta(tick: int, year: int, season: str) -> None:
    """插入或更新 world_meta（永遠只有一筆，id=1）"""
    conn = get_connection()
    with conn:
        conn.execute("""
            INSERT INTO world_meta (id, tick, year, season)
            VALUES (1, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET tick=excluded.tick, year=excluded.year, season=excluded.season
        """, (tick, year, season))
    conn.close()


def get_world_meta() -> dict:
    """讀取 world_meta，若不存在則回傳預設值"""
    conn = get_connection()
    row = conn.execute("SELECT * FROM world_meta WHERE id = 1").fetchone()
    conn.close()
    if row:
        return {"tick": row["tick"], "year": row["year"], "season": row["season"]}
    return {"tick": 0, "year": 1, "season": "spring"}


def upsert_location(location_dict: dict) -> None:
    """插入或更新一個地點（用 location.model_dump() 傳入）"""
    conn = get_connection()
    with conn:
        conn.execute("""
            INSERT INTO locations (id, name, x, y, terrain, resources)
            VALUES (:id, :name, :x, :y, :terrain, :resources)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name, x=excluded.x, y=excluded.y,
                terrain=excluded.terrain, resources=excluded.resources
        """, {
            **location_dict,
            "resources": json.dumps(location_dict["resources"])
        })
    conn.close()


def get_all_locations() -> list[dict]:
    """讀取所有地點，回傳 dict list（resources 已解析為 dict）"""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM locations").fetchall()
    conn.close()
    result = []
    for row in rows:
        d = dict(row)
        d["resources"] = json.loads(d["resources"])
        result.append(d)
    return result


def upsert_agent(agent_dict: dict) -> None:
    """插入或更新一個 Agent"""
    # TODO: 將 agent_dict 中的 personality、resources、skills、
    #       relationships、memory_ids 序列化為 JSON 字串後寫入
    pass


def get_all_agents() -> list[dict]:
    """讀取所有 Agent，回傳 dict list（巢狀欄位已解析）"""
    # TODO: 讀取後將 JSON 欄位反序列化
    pass


def upsert_organization(org_dict: dict) -> None:
    """插入或更新一個組織"""
    # TODO: 將 member_ids、resources、territory 序列化後寫入
    pass


def get_all_organizations() -> list[dict]:
    """讀取所有組織，回傳 dict list"""
    # TODO: 讀取後反序列化 JSON 欄位
    pass


def insert_event(event_dict: dict) -> None:
    """新增一個事件（不更新，事件只新增不修改）"""
    # TODO: 將 affected_agent_ids、affected_location_ids 序列化後寫入
    #       timestamp 轉為 ISO 字串儲存
    pass


def get_all_events() -> list[dict]:
    """讀取所有事件，回傳 dict list"""
    # TODO: 讀取後反序列化 JSON 欄位，timestamp 轉回 datetime
    pass
```

> [!TIP]
> **JSON 欄位的序列化模式：**
> - 寫入時：`json.dumps(some_dict_or_list)`
> - 讀取時：`json.loads(json_string)`
> - `datetime` 與 `timestamp` 使用 `.isoformat()` 轉字串，讀取時用 `datetime.fromisoformat()`

---

### Step 3：實作 `main.py`（對外函數）

`main.py` 是 M1 的公開介面。所有函數必須按照簽名實作，不可更改。

**初始化的 5 個預設地點（`init_world` 呼叫時若 `locations` 為空，則使用此預設值）：**

| name | x | y | terrain |
|------|---|---|---------|
| village | 2 | 2 | plains |
| plains | 0 | 2 | plains |
| mountain | 4 | 4 | mountain |
| forest | 1 | 3 | forest |
| river | 3 | 1 | water |

**Code Skeleton：**

```python
# modules/m1_world_state/main.py
import json
import sys
from pathlib import Path

# 讓 Python 找到 shared 套件
ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR))

from shared.schemas import (
    Agent, Config, Location, Organization, Resource, WorldEvent, WorldState
)
from . import database as db  # 相對 import，若以腳本執行可改為 import database as db


# ── 模組內部快取（避免每次都重新讀取資料庫）──────────────────────────
_world_state: WorldState | None = None
_config: Config | None = None


def _load_config() -> Config:
    """讀取並解析 config.json"""
    config_path = ROOT_DIR / "config.json"
    with open(config_path, "r", encoding="utf-8") as f:
        return Config(**json.load(f))


def _get_default_locations() -> list[Location]:
    """回傳 5 個預設地點"""
    return [
        Location(name="village",  x=2, y=2, terrain="plains"),
        Location(name="plains",   x=0, y=2, terrain="plains"),
        Location(name="mountain", x=4, y=4, terrain="mountain"),
        Location(name="forest",   x=1, y=3, terrain="forest"),
        Location(name="river",    x=3, y=1, terrain="water"),
    ]


# ── 對外函數 ───────────────────────────────────────────────────────────

def init_world(locations: list[Location], config: Config) -> WorldState:
    """初始化世界，建立資料庫結構，返回初始 WorldState。
    
    若 locations 為空 list，自動使用 5 個預設地點。
    """
    global _world_state, _config

    # 1. 儲存 config
    _config = config

    # 2. 建立資料庫與資料表
    db.create_tables()

    # 3. 決定要寫入的地點
    if not locations:
        locations = _get_default_locations()

    # 4. 將地點寫入資料庫
    for loc in locations:
        db.upsert_location(loc.model_dump())

    # 5. 初始化 world_meta（tick=0, year=1, season='spring'）
    db.upsert_world_meta(tick=0, year=1, season="spring")

    # 6. 讀取並快取 WorldState
    _world_state = get_world_state()
    return _world_state


def get_world_state() -> WorldState:
    """讀取當前完整世界狀態（從資料庫重新讀取，確保資料最新）"""
    # TODO:
    # 1. 呼叫 db.get_world_meta() 取得 tick/year/season
    # 2. 呼叫 db.get_all_locations()，轉換為 dict[str, Location]
    # 3. 呼叫 db.get_all_agents()，轉換為 dict[str, Agent]
    # 4. 呼叫 db.get_all_organizations()，轉換為 dict[str, Organization]
    # 5. 呼叫 db.get_all_events()，轉換為 list[WorldEvent]
    # 6. 組合成 WorldState 並回傳
    pass


def update_agent(agent: Agent) -> None:
    """更新單一 Agent 的狀態到資料庫"""
    # TODO:
    # 1. 呼叫 db.upsert_agent(agent.model_dump())
    # 2. 若 _world_state 有快取，更新快取中的 agents[agent.id]
    pass


def update_location_resources(location_id: str, resources: Resource) -> None:
    """更新指定地點的資源"""
    # TODO:
    # 1. 從 db 讀取現有地點資料
    # 2. 更新 resources 欄位
    # 3. 呼叫 db.upsert_location() 寫回
    pass


def add_event(event: WorldEvent) -> None:
    """新增一個世界事件"""
    # TODO:
    # 1. 呼叫 db.insert_event(event.model_dump())
    # 2. 若 _world_state 有快取，append 到 events
    pass


def get_tick() -> int:
    """取得當前 tick 數"""
    # TODO: 呼叫 db.get_world_meta()["tick"] 回傳
    pass


def save_state() -> None:
    """將當前世界狀態序列化並儲存到 data/world_snapshot.json"""
    # TODO:
    # 1. 呼叫 get_world_state() 取得最新狀態
    # 2. 使用 world_state.model_dump(mode='json') 序列化
    # 3. 寫入 ROOT_DIR / "data" / "world_snapshot.json"
    pass


def load_state() -> WorldState:
    """從 data/world_snapshot.json 讀取世界狀態，並同步回 SQLite"""
    # TODO:
    # 1. 讀取 ROOT_DIR / "data" / "world_snapshot.json"
    # 2. 用 WorldState.model_validate(data) 解析
    # 3. 將所有資料重新寫入 SQLite（locations、agents、organizations、events、meta）
    # 4. 更新 _world_state 快取
    # 5. 回傳 WorldState
    pass
```

> [!WARNING]
> `save_state()` 使用 `model_dump(mode='json')` 而非 `model_dump()`，可確保 `datetime` 被正確序列化為字串，避免 JSON 序列化錯誤。

---

### Step 4：確認 `__init__.py`

在 `modules/m1_world_state/` 建立空的 `__init__.py`，讓此目錄成為 Python package（供其他模組以 `from modules.m1_world_state.main import ...` 引入）：

```python
# modules/m1_world_state/__init__.py
# 空檔案
```

---

### Step 5：手動測試

建立一個暫時的測試腳本 `AI_World/test_m1.py`（**驗證後可刪除**）：

```python
# test_m1.py（放在 AI_World/ 根目錄執行）
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from modules.m1_world_state.main import (
    init_world, get_world_state, update_agent,
    update_location_resources, add_event, get_tick,
    save_state, load_state
)
from shared.schemas import Config, Location, Agent, Resource, WorldEvent

# 讀取 config（需要 config.json 存在）
import json
config = Config(**json.load(open("config.json")))

# ── 測試 1：init_world ─────────────────────────────────────
print("=== 測試 init_world ===")
state = init_world([], config)  # 空 list → 使用 5 個預設地點
assert len(state.locations) == 5, f"應有 5 個地點，實際有 {len(state.locations)}"
print(f"✅ 初始化成功，地點數：{len(state.locations)}")
for loc in state.locations.values():
    print(f"   - {loc.name} ({loc.terrain}) @ ({loc.x}, {loc.y})")

# ── 測試 2：get_world_state ────────────────────────────────
print("\n=== 測試 get_world_state ===")
state2 = get_world_state()
assert state2.tick == 0
assert state2.year == 1
assert state2.season == "spring"
print(f"✅ tick={state2.tick}, year={state2.year}, season={state2.season}")

# ── 測試 3：update_agent ───────────────────────────────────
print("\n=== 測試 update_agent ===")
loc_id = list(state.locations.keys())[0]
new_agent = Agent(name="TestHero", location_id=loc_id)
update_agent(new_agent)
state3 = get_world_state()
assert new_agent.id in state3.agents, "Agent 應已存入世界狀態"
print(f"✅ Agent '{new_agent.name}' (id={new_agent.id}) 已成功寫入")

# ── 測試 4：update_location_resources ─────────────────────
print("\n=== 測試 update_location_resources ===")
new_res = Resource(food=999.0, water=888.0, energy=777.0, money=666.0, materials=555.0)
update_location_resources(loc_id, new_res)
state4 = get_world_state()
assert state4.locations[loc_id].resources.food == 999.0, "food 應已更新為 999.0"
print(f"✅ 地點資源已更新：food={state4.locations[loc_id].resources.food}")

# ── 測試 5：add_event ─────────────────────────────────────
print("\n=== 測試 add_event ===")
ev = WorldEvent(tick=0, event_type="discovery", description="發現了神秘石頭")
add_event(ev)
state5 = get_world_state()
assert any(e.id == ev.id for e in state5.events), "事件應已存入世界狀態"
print(f"✅ 事件 '{ev.description}' 已成功新增")

# ── 測試 6：get_tick ───────────────────────────────────────
print("\n=== 測試 get_tick ===")
tick = get_tick()
assert tick == 0
print(f"✅ 當前 tick = {tick}")

# ── 測試 7：save_state + load_state ───────────────────────
print("\n=== 測試 save_state + load_state ===")
save_state()
from pathlib import Path
assert Path("data/world_snapshot.json").exists(), "world_snapshot.json 應已建立"
loaded = load_state()
assert len(loaded.locations) == len(state5.locations), "地點數量應一致"
assert new_agent.id in loaded.agents, "Agent 應在 load 後仍存在"
print(f"✅ save/load 一致：{len(loaded.locations)} 個地點，{len(loaded.agents)} 個 Agent")

print("\n🎉 所有測試通過！")
```

執行方式（在 `AI_World/` 根目錄下執行）：

```bash
cd c:\Users\zohanlin\Documents\zohan_ai_test\AI_World
python test_m1.py
```

---

## 驗證標準（全部通過才算完成）

- [ ] `data/world.db` 在執行 `init_world()` 後存在
- [ ] `init_world([], config)` 自動建立 5 個預設地點（village、plains、mountain、forest、river）
- [ ] `get_world_state()` 回傳完整 `WorldState`，包含 `locations`、`agents`、`organizations`、`events`
- [ ] `update_agent(agent)` 後重新呼叫 `get_world_state()`，能在 `state.agents` 中看到更新後的 Agent
- [ ] `update_location_resources(location_id, resources)` 後，`get_world_state().locations[location_id].resources` 反映新值
- [ ] `add_event(event)` 後，`get_world_state().events` 包含該事件
- [ ] `get_tick()` 回傳整數，初始為 `0`
- [ ] `save_state()` 執行後，`data/world_snapshot.json` 檔案存在且為合法 JSON
- [ ] `load_state()` 執行後，回傳的 `WorldState` 與 `save_state()` 前的狀態一致（地點數、Agent 數相符）
- [ ] `main.py` 與 `database.py` 所有函數皆有型別標注（含參數與回傳型別）
- [ ] 測試腳本 `test_m1.py` 全部輸出 ✅，最終顯示 `🎉 所有測試通過！`

---

## 常見錯誤與排查

| 錯誤訊息 | 原因 | 解法 |
|----------|------|------|
| `ModuleNotFoundError: No module named 'shared'` | Python path 未設定 | 確認 `sys.path.insert(0, str(ROOT_DIR))` 在 `main.py` 頂部執行 |
| `FileNotFoundError: config.json` | M0 尚未執行 | 先執行 M0，或手動建立 `config.json`（參考下方範例） |
| `sqlite3.OperationalError: no such table` | `create_tables()` 未被呼叫 | 確認 `init_world()` 有呼叫 `db.create_tables()` |
| `json.JSONDecodeError` | 資料庫中有損壞的 JSON 欄位 | 檢查 `upsert_*` 函數是否正確序列化所有 dict/list 欄位 |
| `pydantic.ValidationError` | Schema 欄位不符 | 確認 `shared/schemas.py` 使用的版本與本文件一致 |

**臨時 `config.json` 範例**（若 M0 尚未完成，可手動建立）：

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
