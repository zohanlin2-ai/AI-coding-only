# Module M3：記憶系統（Memory System）

## 你的任務

使用 ChromaDB 為每個 Agent 提供向量語意記憶儲存與搜尋功能，讓 Agent 能「記得過去發生的事」，並能以語意相似度搜尋歷史事件；同時維護一個全局的世界事件向量資料庫供跨模組查詢。

---

## 負責範圍

- **負責：**
  - 啟動本地 ChromaDB，資料持久化於 `data/chroma/`
  - 為每個 Agent 建立並維護獨立的記憶 collection（`agent_{agent_id}_memory`）
  - 維護全局世界事件 collection（`world_history`）
  - 實作記憶儲存（含 `importance` 權重寫入 metadata）
  - 實作語意相似度搜尋（`recall_memory`、`search_history`）
  - 實作依時間倒序讀取最近記憶（`get_recent_memory`）

- **不負責：**
  - Agent 的行為決策或思考（由 M2 負責）
  - 世界狀態的 SQLite 儲存（由 M1 負責）
  - tick 推進與時間管理（由 M6 負責）
  - LLM 呼叫（M3 不使用 LLM）
  - 讀取 `config.json` 以外的系統設定

---

## 依賴關係

- **需要先完成：**
  - M0（產出 `config.json`，M3 從中讀取基本設定）

- **被以下模組使用：**
  - M2（Agent 行動後儲存記憶、思考時召回記憶）
  - M4（Multi-Agent 互動時查詢相關記憶）
  - M6（儲存世界事件到向量資料庫）
  - M8（整合測試）

---

## 工作目錄

```
c:\Users\zohanlin\Documents\zohan_ai_test\AI_World\modules\m3_memory\
```

所有程式碼寫在此目錄下的 `main.py`。  
ChromaDB 資料存在專案根目錄的 `data/chroma/`（由本模組負責建立）。

---

## 環境安裝

在專案根目錄執行：

```bash
pip install chromadb pydantic
```

> **注意**：`chromadb` 版本請使用 `>=0.4.0`。若遇到 `sqlite3` 版本衝突（Python 3.11 在某些環境有此問題），請改用：
> ```bash
> pip install chromadb>=0.5.0
> ```

---

## 需要建立的檔案

```
AI_World/
├── data/
│   └── chroma/                  ← ChromaDB 自動建立，不需手動建立
├── modules/
│   └── m3_memory/
│       └── main.py              ← 本模組唯一需要建立的檔案
└── shared/
    └── schemas.py               ← 已存在，直接 import，不可修改
```

---

## 共用 Schema（直接使用，不可修改）

從 `shared/schemas.py` import 以下 class。**不可在 `main.py` 中重新定義這些 class。**

```python
# shared/schemas.py（節錄 M3 相關部分）

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid


def gen_id() -> str:
    return str(uuid.uuid4())[:8]


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

以下五個函數是 M3 對其他模組的**公開合約**。函數名稱、參數名稱、參數型別、回傳型別**一律不得更改**。

```python
def save_memory(agent_id: str, event: str, importance: float) -> str:
    """
    儲存 Agent 的一條記憶。
    - agent_id: Agent 的唯一識別碼
    - event: 記憶內容的文字描述
    - importance: 記憶重要性，範圍 0.0（不重要）~ 1.0（極重要）
    - 返回：新建記憶的唯一 id（字串）
    """

def recall_memory(agent_id: str, query: str, top_k: int = 5) -> list[str]:
    """
    根據語意查詢，返回該 Agent 最相關的記憶列表。
    - agent_id: Agent 的唯一識別碼
    - query: 查詢文字（語意相似度搜尋）
    - top_k: 最多返回幾條記憶
    - 返回：記憶內容字串列表（最相關在前）
    """

def get_recent_memory(agent_id: str, n: int = 10) -> list[str]:
    """
    按時間倒序返回 Agent 最近的 n 條記憶。
    - agent_id: Agent 的唯一識別碼
    - n: 最多返回幾條
    - 返回：記憶內容字串列表（最新在前）
    """

def save_world_event(event: WorldEvent) -> None:
    """
    將一個 WorldEvent 存入全局向量資料庫（world_history collection）。
    - event: WorldEvent 物件
    - 無返回值
    """

def search_history(query: str, top_k: int = 10) -> list[WorldEvent]:
    """
    語意搜尋世界歷史事件。
    - query: 查詢文字
    - top_k: 最多返回幾條
    - 返回：WorldEvent 物件列表（最相關在前）
    """
```

---

## 你可以呼叫的外部函數

M3 **不需要呼叫其他模組的函數**。M3 是被動被呼叫的服務模組，只讀取 `config.json`，不主動依賴 M1 / M2 / M4 / M6 的函數。

讀取設定的方式如下：

```python
import json
from pathlib import Path
from shared.schemas import Config

def _load_config() -> Config:
    config_path = Path(__file__).parent.parent.parent / "config.json"
    with open(config_path, "r", encoding="utf-8") as f:
        return Config(**json.load(f))
```

> `config.json` 位於專案根目錄（`AI_World/config.json`），由 M0 產生。

---

## 實作步驟

### Step 1：設定目錄與 import

在 `modules/m3_memory/main.py` 的頂部，設定 `sys.path` 讓 Python 能正確 import `shared.schemas`，並初始化 ChromaDB client。

```python
# modules/m3_memory/main.py

import sys
import json
import uuid
from pathlib import Path
from datetime import datetime

# 確保可以 import shared/schemas.py
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import chromadb
from chromadb.config import Settings
from shared.schemas import WorldEvent, Config

# ── ChromaDB 初始化 ──────────────────────────────────────────────
CHROMA_DATA_PATH = PROJECT_ROOT / "data" / "chroma"
CHROMA_DATA_PATH.mkdir(parents=True, exist_ok=True)

# 使用 PersistentClient 讓資料持久化儲存到 data/chroma/
_client = chromadb.PersistentClient(path=str(CHROMA_DATA_PATH))
```

---

### Step 2：取得或建立 Agent 記憶 Collection

每個 Agent 有自己獨立的 collection，名稱為 `agent_{agent_id}_memory`。使用 `get_or_create_collection` 確保幂等性（重複呼叫不會出錯）。

```python
def _get_agent_collection(agent_id: str):
    """
    取得或建立指定 Agent 的記憶 collection。
    Collection 命名規則：agent_{agent_id}_memory
    """
    collection_name = f"agent_{agent_id}_memory"
    # TODO: 使用 _client.get_or_create_collection() 建立 collection
    # 提示：collection_name 只能包含英數字、底線、連字號，且長度 3~63
    #       agent_id 若含有特殊字元，需先做 sanitize（替換為底線）
    raise NotImplementedError
```

> **注意**：ChromaDB collection 名稱只允許英數字、底線、連字號，且長度須在 3～63 之間。如果 `agent_id` 可能包含特殊字元，需要先做 sanitize：
> ```python
> import re
> safe_id = re.sub(r'[^a-zA-Z0-9_-]', '_', agent_id)
> collection_name = f"agent_{safe_id}_memory"
> ```

---

### Step 3：取得或建立全局世界歷史 Collection

```python
def _get_world_collection():
    """
    取得或建立全局世界事件的 collection。
    Collection 名稱固定為：world_history
    """
    # TODO: 使用 _client.get_or_create_collection("world_history")
    raise NotImplementedError
```

---

### Step 4：實作 `save_memory`

將一條 Agent 記憶存入對應 collection。  
`importance`、`tick`、`agent_id`、`timestamp` 都存入 metadata 以便後續篩選。

```python
def save_memory(agent_id: str, event: str, importance: float) -> str:
    """
    儲存 Agent 的一條記憶，返回記憶 id。
    """
    collection = _get_agent_collection(agent_id)
    memory_id = str(uuid.uuid4())[:8]

    # TODO: 使用 collection.add() 儲存記憶
    # documents: [event]  ← 文字內容，ChromaDB 會自動向量化
    # ids: [memory_id]
    # metadatas: [{
    #     "tick": ...,        ← 當前 tick，若無法取得可用 0
    #     "agent_id": agent_id,
    #     "importance": importance,
    #     "timestamp": datetime.now().isoformat()
    # }]
    #
    # 提示：tick 可以嘗試從 M1 取得，但 M3 不依賴 M1，
    #       可以接受一個預設值（0 或呼叫方傳入）。
    #       此版本先用 timestamp 排序，tick 可留 0。

    raise NotImplementedError

    return memory_id
```

---

### Step 5：實作 `recall_memory`

使用 ChromaDB 的語意搜尋，根據 `query` 文字找出最相關的記憶。

```python
def recall_memory(agent_id: str, query: str, top_k: int = 5) -> list[str]:
    """
    語意搜尋 Agent 的記憶，返回最相關的記憶文字列表。
    """
    collection = _get_agent_collection(agent_id)

    # TODO: 使用 collection.query() 進行語意搜尋
    # query_texts: [query]
    # n_results: top_k
    #
    # 注意：若 collection 中的記憶數量少於 top_k，
    #       ChromaDB 會報錯或返回較少結果，需要處理邊界情況：
    #       n_results = min(top_k, collection.count())
    #       若 count() == 0，直接返回 []
    #
    # 回傳值結構：results["documents"][0] 是字串列表

    raise NotImplementedError
```

---

### Step 6：實作 `get_recent_memory`

返回 Agent 最近 n 條記憶（依 `timestamp` metadata 倒序排列）。

```python
def get_recent_memory(agent_id: str, n: int = 10) -> list[str]:
    """
    返回 Agent 最近 n 條記憶（最新在前）。
    """
    collection = _get_agent_collection(agent_id)

    # TODO: 使用 collection.get() 取得所有記憶
    # include=["documents", "metadatas"]
    #
    # 取得後，依 metadatas 中的 "timestamp" 欄位做倒序排列：
    # sorted(..., key=lambda x: x["timestamp"], reverse=True)
    #
    # 只返回前 n 條的 document 文字
    #
    # 若 collection 為空，返回 []

    raise NotImplementedError
```

---

### Step 7：實作 `save_world_event`

將 `WorldEvent` 物件存入 `world_history` collection。  
存入時需將 `WorldEvent` 的主要欄位放入 metadata，以便 `search_history` 能還原成 `WorldEvent` 物件。

```python
def save_world_event(event: WorldEvent) -> None:
    """
    將世界事件存入全局向量資料庫。
    """
    collection = _get_world_collection()

    # TODO: 使用 collection.add() 儲存事件
    # documents: [event.description]  ← 用 description 做語意索引
    # ids: [event.id]
    # metadatas: [{
    #     "tick": event.tick,
    #     "event_type": event.event_type,
    #     "description": event.description,
    #     "affected_agent_ids": json.dumps(event.affected_agent_ids),
    #     "affected_location_ids": json.dumps(event.affected_location_ids),
    #     "timestamp": event.timestamp.isoformat()
    # }]
    #
    # 注意：ChromaDB metadata 值只能是 str / int / float / bool，
    #       list 必須先用 json.dumps() 轉成字串。

    raise NotImplementedError
```

---

### Step 8：實作 `search_history`

語意搜尋世界歷史，從 metadata 還原成 `WorldEvent` 物件列表。

```python
def search_history(query: str, top_k: int = 10) -> list[WorldEvent]:
    """
    語意搜尋世界歷史事件，返回 WorldEvent 列表。
    """
    collection = _get_world_collection()

    # TODO: 使用 collection.query() 進行語意搜尋
    # query_texts: [query]
    # n_results: min(top_k, collection.count())
    # include=["metadatas"]
    #
    # 從 results["metadatas"][0] 取得 metadata 列表
    # 將每個 metadata 還原成 WorldEvent 物件：
    # WorldEvent(
    #     id=meta["id"],            ← 需要從 ids 取得，或在 metadata 中另存
    #     tick=meta["tick"],
    #     event_type=meta["event_type"],
    #     description=meta["description"],
    #     affected_agent_ids=json.loads(meta["affected_agent_ids"]),
    #     affected_location_ids=json.loads(meta["affected_location_ids"]),
    #     timestamp=datetime.fromisoformat(meta["timestamp"])
    # )
    #
    # 若 collection 為空，返回 []
    #
    # 提示：若需要 id，可在 query() 加上 include=["metadatas", "documents"]
    #       並同時在 save_world_event 的 metadata 中儲存 "id": event.id

    raise NotImplementedError
```

> **重要提示**：ChromaDB 的 `query()` 預設不回傳 `ids`，若需要 `id` 還原 `WorldEvent`，有兩個做法：
> 1. 在 `save_world_event` 的 metadata 中額外儲存 `"id": event.id`（**推薦**）
> 2. 在 `query()` 加上 `include=["ids", "metadatas"]`

---

### Step 9：模組自我測試腳本（非必要，但強烈建議）

在 `main.py` 最底部加上 `if __name__ == "__main__":` 區塊，方便獨立執行驗證：

```python
if __name__ == "__main__":
    import time

    print("=== M3 Memory System 自我測試 ===\n")

    # 測試 1：save_memory + recall_memory
    print("[1] 測試 save_memory...")
    mid = save_memory("agent_001", "我在森林中發現了一個神秘的洞穴", importance=0.9)
    print(f"    已儲存記憶 id: {mid}")

    save_memory("agent_001", "我與 agent_002 進行了食物交換", importance=0.6)
    save_memory("agent_001", "今天天氣很好，我在平原上休息", importance=0.2)

    print("\n[2] 測試 recall_memory（語意查詢：洞穴探索）...")
    results = recall_memory("agent_001", "探索地下空間", top_k=3)
    for i, r in enumerate(results):
        print(f"    [{i+1}] {r}")

    # 測試 2：Agent 隔離性
    print("\n[3] 測試 Agent 記憶隔離...")
    save_memory("agent_002", "我是 agent_002，我住在山上", importance=0.5)
    results_002 = recall_memory("agent_002", "洞穴", top_k=5)
    print(f"    agent_002 查詢「洞穴」的結果（應為空或只含 agent_002 的記憶）：")
    for r in results_002:
        print(f"    - {r}")

    # 測試 3：get_recent_memory
    print("\n[4] 測試 get_recent_memory...")
    recent = get_recent_memory("agent_001", n=2)
    print(f"    最近 2 條記憶：{recent}")

    # 測試 4：save_world_event + search_history
    print("\n[5] 測試 save_world_event + search_history...")
    event = WorldEvent(
        tick=42,
        event_type="conflict",
        description="兩個部落在北方平原爆發了衝突，爭奪水源控制權",
        affected_agent_ids=["agent_001", "agent_002"],
        affected_location_ids=["loc_001"]
    )
    save_world_event(event)

    search_results = search_history("水資源爭奪戰", top_k=5)
    print(f"    搜尋結果（{len(search_results)} 條）：")
    for e in search_results:
        print(f"    - [tick {e.tick}] {e.event_type}: {e.description}")

    print("\n✅ 所有測試通過！")
```

---

## ChromaDB 資料架構說明

### Agent 記憶 Collection

| 欄位 | 說明 |
|------|------|
| `id` | 記憶唯一 id（8 碼 UUID 片段） |
| `documents` | 記憶文字內容（供語意搜尋） |
| `metadatas.tick` | 儲存時的 tick 數（int） |
| `metadatas.agent_id` | 所屬 Agent id（str） |
| `metadatas.importance` | 重要性權重 0.0~1.0（float） |
| `metadatas.timestamp` | ISO 格式時間字串（str） |

### 世界歷史 Collection（`world_history`）

| 欄位 | 說明 |
|------|------|
| `id` | WorldEvent.id |
| `documents` | WorldEvent.description（供語意搜尋） |
| `metadatas.id` | WorldEvent.id（方便還原） |
| `metadatas.tick` | 事件發生 tick（int） |
| `metadatas.event_type` | 事件類型（str） |
| `metadatas.description` | 事件描述（str） |
| `metadatas.affected_agent_ids` | JSON 字串，如 `'["a1","a2"]'` |
| `metadatas.affected_location_ids` | JSON 字串，如 `'["loc1"]'` |
| `metadatas.timestamp` | ISO 格式時間字串（str） |

---

## 常見問題與注意事項

> [!WARNING]
> **ChromaDB collection 名稱限制**  
> Collection 名稱只能包含英數字、底線（`_`）、連字號（`-`），且長度須在 3～63 字元之間。`agent_id` 若含特殊字元，必須先 sanitize。

> [!WARNING]
> **`n_results` 不能超過實際資料筆數**  
> 呼叫 `collection.query()` 時，`n_results` 不可大於 collection 中的資料數量，否則會拋出例外。務必先用 `collection.count()` 確認數量：
> ```python
> count = collection.count()
> if count == 0:
>     return []
> n_results = min(top_k, count)
> ```

> [!NOTE]
> **ChromaDB 預設 Embedding Model**  
> `chromadb` 預設使用 `all-MiniLM-L6-v2`（需要網路下載）。若環境無法連網，可改用：
> ```python
> from chromadb.utils import embedding_functions
> ef = embedding_functions.DefaultEmbeddingFunction()
> collection = _client.get_or_create_collection("...", embedding_function=ef)
> ```
> 或者完全離線時，改用 `OllamaEmbeddingFunction`（需要 Ollama 已在本地運行）：
> ```python
> ef = embedding_functions.OllamaEmbeddingFunction(
>     url="http://localhost:11434/api/embeddings",
>     model_name="nomic-embed-text"
> )
> ```

> [!NOTE]
> **PersistentClient vs HttpClient**  
> M3 使用 `chromadb.PersistentClient`（本地檔案儲存），**不需要**另外啟動 ChromaDB server process。資料直接寫入 `data/chroma/` 目錄。這是 Local First 設計原則的體現。

> [!TIP]
> **`importance` 在搜尋中的應用（進階）**  
> ChromaDB 的 `query()` 返回結果時附帶 `distances`（距離分數），若想加入 `importance` 做加權重排，可在取得結果後自行計算：
> ```python
> # 加權分數 = (1 - distance) * importance
> # distance 越小 = 越相似
> ```
> 基本實作可先忽略 importance 對搜尋排序的影響，只在 metadata 中記錄即可。

---

## 驗證標準（全部通過才算完成）

- [ ] `pip install chromadb pydantic` 安裝無錯誤
- [ ] 執行 `python modules/m3_memory/main.py` 自我測試腳本全部通過，無 Exception
- [ ] `data/chroma/` 目錄自動建立，且 ChromaDB 資料寫入其中（目錄非空）
- [ ] `save_memory("agent_001", "我在森林中發現了洞穴", 0.9)` 返回一個非空字串 id
- [ ] `recall_memory("agent_001", "地下空間探索", top_k=3)` 能語意搜尋到「洞穴」相關記憶（不需完全一致，語意相近即可）
- [ ] 不同 Agent 的記憶互相隔離：Agent A 的記憶**不會**出現在 Agent B 的 `recall_memory` 結果中
- [ ] `get_recent_memory("agent_001", n=2)` 返回列表長度 ≤ 2，且最新的記憶排在前面
- [ ] `save_world_event(event)` 不拋出例外，`data/chroma/` 中有對應資料
- [ ] `search_history("水資源爭奪", top_k=5)` 返回 `list[WorldEvent]`，且每個元素可正常存取 `.tick`、`.event_type`、`.description`、`.affected_agent_ids` 欄位
- [ ] 重複啟動（多次執行 `main.py`）不會因 collection 已存在而報錯（`get_or_create_collection` 幂等）
- [ ] 各函數型別簽名與「你對外提供的函數」章節完全一致（用 `inspect.signature()` 確認）

---

*文件版本：1.0 | 對應 Architecture.md 最後更新：2026-05-25*
