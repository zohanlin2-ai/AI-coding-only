# Module M7：視覺化儀表板（Visualization Dashboard）

## 你的任務

建立一個 Streamlit 視覺化 App，讓人類觀察者能即時觀察 AI 世界的狀態，包含世界地圖、Agent 狀態、事件流與歷史快照查詢，所有資料從 M1 與 M6 讀取。

---

## 負責範圍

- **負責：**
  - 啟動並維護一個 Streamlit Web App（`app.py`）
  - 每 10 秒自動刷新畫面，從 M1 取得最新世界狀態
  - 以彩色格子圖呈現世界地圖（地形 + Agent 位置標記）
  - 以表格顯示所有 Agent 的資源與個性數值
  - 以列表顯示最新 50 個世界事件
  - 提供 Tick 範圍輸入，從 M6 查詢歷史事件
  - 在頁首顯示當前 tick、年份、季節等全域資訊

- **不負責：**
  - 修改或寫入世界狀態（唯讀）
  - 直接操作資料庫（透過 M1/M6 介面存取）
  - Agent 決策、LLM 呼叫、規則執行
  - 任何對外 API 或函數（M7 無對外介面）

---

## 依賴關係

- **需要先完成：**
  - M0（產出 `config.json`，M7 需讀取以取得 tick_interval_sec 等設定）
  - M1（`get_world_state()` 必須可正常呼叫）
  - M6（`get_history()`、`get_snapshot()`、`get_timeline()`、`get_current_season()` 必須可正常呼叫）

- **被以下模組使用：**
  - M8（整合測試時驗證 Streamlit App 可正常啟動）

---

## 工作目錄

```
c:\Users\zohanlin\Documents\zohan_ai_test\AI_World\modules\m7_visualization\
```

> 所有指令皆在專案根目錄 `c:\Users\zohanlin\Documents\zohan_ai_test\AI_World\` 執行。

---

## 環境安裝

```bash
pip install streamlit pandas plotly pydantic
```

> **注意：** `pydantic` 版本須為 v2（`pydantic>=2.0`）。若已安裝舊版，請執行 `pip install --upgrade pydantic`。

---

## 需要建立的檔案

```
AI_World/
└── modules/
    └── m7_visualization/
        └── app.py          ← 唯一需要建立的檔案
```

> `shared/schemas.py` 與其他模組已存在，不需重建。

---

## 共用 Schema（直接使用，不可修改）

以下 Schema 定義在 `shared/schemas.py`，M7 需直接 import 使用，**不得自行定義替代 class**。

```python
# shared/schemas.py（節錄 M7 會用到的部分）

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
    relationships: dict[str, float] = Field(default_factory=dict)
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

### 地形顏色對照表（M7 自行定義，非 Schema 的一部分）

| terrain 值  | 建議顯示顏色 |
|-------------|-------------|
| `"plains"`  | 黃綠色 `#a8d5a2` |
| `"mountain"` | 灰色 `#9e9e9e` |
| `"forest"`  | 深綠色 `#2d6a4f` |
| `"water"`   | 藍色 `#4fc3f7` |

### 季節符號對照（供頁首顯示）

| season 值   | 建議符號 |
|-------------|---------|
| `"spring"`  | 🌸 春 |
| `"summer"`  | ☀️ 夏 |
| `"autumn"`  | 🍂 秋 |
| `"winter"`  | ❄️ 冬 |

---

## 你對外提供的函數（簽名不可修改）

**M7 無對外函數。** M7 是一個獨立的 Streamlit App，不提供任何可被其他模組 import 的函數。

啟動方式：
```bash
streamlit run modules/m7_visualization/app.py
```

---

## 你可以呼叫的外部函數

### 來自 M1（`modules/m1_world_state/main.py`）

```python
from modules.m1_world_state.main import get_world_state

def get_world_state() -> WorldState:
    """讀取當前完整世界狀態，包含所有 locations、agents、organizations、events"""
```

### 來自 M6（`modules/m6_time_history/main.py`）

```python
from modules.m6_time_history.main import get_history, get_snapshot, get_timeline, get_current_season

def get_history(start_tick: int, end_tick: int) -> list[WorldEvent]:
    """取得指定 tick 範圍的歷史事件列表"""

def get_snapshot(tick: int) -> Optional[WorldState]:
    """取得指定 tick 的世界快照，若無快照則返回 None"""

def get_timeline() -> list[dict]:
    """返回所有重大事件的時間軸列表，格式：[{tick, event_type, description}, ...]"""

def get_current_season() -> str:
    """返回當前季節字串：'spring' | 'summer' | 'autumn' | 'winter'"""
```

> **注意：** 呼叫這些函數時，需確保 M1 與 M6 的資料庫（`data/world.db`）已存在且已初始化。若資料庫不存在，請使用 `try/except` 捕捉例外並在 UI 顯示友善錯誤訊息，**不要讓 App crash**。

---

## 實作步驟

### 步驟 0：建立目錄與空白檔案

```bash
# 在專案根目錄執行
mkdir modules\m7_visualization
type nul > modules\m7_visualization\app.py
```

---

### 步驟 1：建立 `app.py` 基本骨架與頁面路由

`app.py` 的整體結構如下。先建立骨架，再逐步填入各分頁邏輯。

```python
# modules/m7_visualization/app.py

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import time
import json
import sys
import os
from typing import Optional

# ── 路徑設定（確保從專案根目錄可以 import shared 與各 module）──
# 將專案根目錄加入 Python 路徑
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# ── 外部模組 import ──
try:
    from modules.m1_world_state.main import get_world_state
    M1_AVAILABLE = True
except ImportError:
    M1_AVAILABLE = False

try:
    from modules.m6_time_history.main import (
        get_history,
        get_snapshot,
        get_timeline,
        get_current_season,
    )
    M6_AVAILABLE = True
except ImportError:
    M6_AVAILABLE = False

from shared.schemas import WorldState, WorldEvent, Agent, Location


# ── 常數設定 ──
REFRESH_INTERVAL = 10      # 自動刷新秒數
TERRAIN_COLORS = {
    "plains":   "#a8d5a2",
    "mountain": "#9e9e9e",
    "forest":   "#2d6a4f",
    "water":    "#4fc3f7",
}
SEASON_EMOJI = {
    "spring": "🌸 春",
    "summer": "☀️ 夏",
    "autumn": "🍂 秋",
    "winter": "❄️ 冬",
}


# ── 輔助函數 ──
def load_config() -> dict:
    """讀取 config.json，失敗時返回預設值"""
    # TODO：開啟 config.json，解析並返回 dict
    # 若檔案不存在，返回 {"tick_interval_sec": 30}
    pass


def safe_get_world_state() -> Optional[WorldState]:
    """安全地呼叫 M1，失敗時返回 None 並顯示警告"""
    # TODO：呼叫 get_world_state()，捕捉所有例外
    # 例外時用 st.warning() 顯示訊息，返回 None
    pass


# ── 頁面渲染函數（各步驟分別實作）──
def render_header(world_state: Optional[WorldState]) -> None:
    """渲染頁首：標題 + 當前 tick / 年份 / 季節"""
    # TODO：在步驟 2 實作
    pass


def render_world_map(world_state: Optional[WorldState]) -> None:
    """渲染世界地圖分頁"""
    # TODO：在步驟 3 實作
    pass


def render_agent_status(world_state: Optional[WorldState]) -> None:
    """渲染 Agent 狀態分頁"""
    # TODO：在步驟 4 實作
    pass


def render_event_stream(world_state: Optional[WorldState]) -> None:
    """渲染事件流分頁"""
    # TODO：在步驟 5 實作
    pass


def render_history_query() -> None:
    """渲染歷史查詢分頁"""
    # TODO：在步驟 6 實作
    pass


# ── 主程式入口 ──
def main():
    st.set_page_config(
        page_title="AI World Dashboard",
        page_icon="🌍",
        layout="wide",
    )

    # 讀取世界狀態（所有分頁共用）
    world_state = safe_get_world_state()

    # 渲染頁首
    render_header(world_state)

    # 分頁導航
    tab1, tab2, tab3, tab4 = st.tabs([
        "🗺️ 世界地圖",
        "🧑 Agent 狀態",
        "📜 事件流",
        "🕰️ 歷史查詢",
    ])

    with tab1:
        render_world_map(world_state)

    with tab2:
        render_agent_status(world_state)

    with tab3:
        render_event_stream(world_state)

    with tab4:
        render_history_query()

    # ── 自動刷新機制 ──
    # TODO：在步驟 7 實作


if __name__ == "__main__":
    main()
```

---

### 步驟 2：實作 `render_header()`

在頁首顯示 AI World 標題，以及當前的 tick、年份、季節。若 `world_state` 為 `None`（M1 尚未就緒），顯示「等待世界初始化...」。

```python
def render_header(world_state: Optional[WorldState]) -> None:
    st.title("🌍 AI World 即時儀表板")
    st.divider()

    if world_state is None:
        st.warning("⚠️ 無法連接 M1 World State Engine，等待世界初始化...")
        return

    # 取得當前季節（優先從 M6 取，失敗則從 WorldState 取）
    season_str = world_state.season
    if M6_AVAILABLE:
        try:
            season_str = get_current_season()
        except Exception:
            pass  # 使用 world_state.season 做 fallback

    season_display = SEASON_EMOJI.get(season_str, season_str)

    # TODO：用 st.columns(3) 並排顯示：
    #   col1 → "⏱️ Tick：{world_state.tick}"
    #   col2 → "📅 年份：第 {world_state.year} 年"
    #   col3 → "季節：{season_display}"
    # 每欄使用 st.metric() 顯示，視覺效果較佳
    pass
```

---

### 步驟 3：實作 `render_world_map()`

使用 Plotly 的 `go.Heatmap` 或自訂格子圖，以顏色呈現地形，並以符號「👤」標記有 Agent 的格子。

```python
def render_world_map(world_state: Optional[WorldState]) -> None:
    st.subheader("🗺️ 世界地圖")

    if world_state is None or not world_state.locations:
        st.info("暫無地圖資料。請確認 M1 已初始化並建立 Location。")
        return

    locations = list(world_state.locations.values())

    # 計算地圖邊界
    max_x = max(loc.x for loc in locations)
    max_y = max(loc.y for loc in locations)

    # 建立格子矩陣：z 值代表地形（用整數 index 對應顏色）
    # 建立 Agent 位置查找表：location_id → agent 名稱列表
    # TODO：
    #   1. 建立 (max_y+1) × (max_x+1) 的 2D 陣列，填入地形 index（0~3）
    #   2. 建立 (max_y+1) × (max_x+1) 的 text 陣列，填入格子資訊（地名 + Agent 名）
    #   3. 使用 go.Figure(go.Heatmap(...)) 繪製地形底圖
    #      colorscale 對應 TERRAIN_COLORS 的四種顏色
    #   4. 對有 Agent 的格子，疊加 go.Scatter 散點圖，符號為 "👤"
    #   5. st.plotly_chart(fig, use_container_width=True)

    # ── 圖例說明 ──
    st.markdown("**地形圖例：**")
    cols = st.columns(len(TERRAIN_COLORS))
    for i, (terrain, color) in enumerate(TERRAIN_COLORS.items()):
        # TODO：用 cols[i].markdown() 顯示色塊與地形名稱
        pass
```

> **提示：** Plotly Heatmap 的 `colorscale` 接受 `[[0, "#color1"], [0.33, "#color2"], ...]` 格式。地形 index 對應關係建議為：`plains=0, forest=1, mountain=2, water=3`。

---

### 步驟 4：實作 `render_agent_status()`

以 `st.dataframe()` 顯示所有 Agent 的狀態表格，並提供個別 Agent 的詳細展開區塊。

```python
def render_agent_status(world_state: Optional[WorldState]) -> None:
    st.subheader("🧑 Agent 狀態總覽")

    if world_state is None or not world_state.agents:
        st.info("暫無 Agent 資料。請確認 M2 已建立 Agent。")
        return

    agents = list(world_state.agents.values())

    # ── 主要表格 ──
    # TODO：將 agents 轉換成 list of dict，欄位包含：
    #   name、location_id（可進一步轉換成地名）、
    #   food、water、energy、money、materials、
    #   is_alive（顯示 ✅ / ❌）、age
    # 使用 pd.DataFrame() 建立表格，再用 st.dataframe() 顯示
    # 建議對數值欄位使用 st.dataframe 的 column_config 設定進度條樣式

    # ── 個別 Agent 詳細資訊 ──
    st.subheader("🔍 Agent 詳細資料")
    agent_names = [a.name for a in agents]
    selected_name = st.selectbox("選擇 Agent", agent_names)

    # TODO：找到 selected_name 對應的 Agent 物件
    # 使用 st.expander() 或 st.columns() 顯示：
    #   - 個性特質（hunger/fear/ambition/loyalty/aggression）用進度條或雷達圖
    #   - 技能列表（skills dict）
    #   - 關係列表（relationships dict，顯示對象 Agent 名稱與好感度）
    pass
```

> **提示：** `st.progress(value)` 可顯示 0.0~1.0 的進度條，適合顯示個性數值。`plotly` 的 `go.Scatterpolar` 可繪製雷達圖呈現個性五維數據。

---

### 步驟 5：實作 `render_event_stream()`

顯示最新 50 個世界事件，並以不同顏色區分事件類型。

```python
def render_event_stream(world_state: Optional[WorldState]) -> None:
    st.subheader("📜 最新事件流")

    if world_state is None:
        st.info("無法取得事件資料。")
        return

    events = world_state.events

    if not events:
        st.info("目前尚無任何世界事件。")
        return

    # 只顯示最新 50 筆，按 tick 降序排列（最新的在最上面）
    recent_events = sorted(events, key=lambda e: e.tick, reverse=True)[:50]

    # 事件類型對應顏色 badge
    EVENT_COLORS = {
        "interaction": "🟦",
        "resource":    "🟩",
        "conflict":    "🟥",
        "discovery":   "🟨",
        "death":       "⬛",
    }

    # TODO：將事件轉換成 DataFrame，欄位：tick、event_type、description、timestamp
    # 方法一（簡單）：使用 st.dataframe() 顯示表格
    # 方法二（美觀）：用迴圈對每個事件呼叫 st.markdown() 顯示一行
    #   格式範例："{emoji} **[Tick {tick}]** `{event_type}` — {description}"
    pass
```

---

### 步驟 6：實作 `render_history_query()`

提供 tick 範圍輸入，呼叫 M6 查詢歷史事件，並顯示指定 tick 的世界快照。

```python
def render_history_query() -> None:
    st.subheader("🕰️ 歷史查詢")

    if not M6_AVAILABLE:
        st.error("M6 Time & History 模組尚未就緒，無法查詢歷史。")
        return

    # ── 事件範圍查詢 ──
    st.markdown("### 📋 事件範圍查詢")
    col1, col2 = st.columns(2)
    with col1:
        start_tick = st.number_input("起始 Tick", min_value=0, value=0, step=1)
    with col2:
        end_tick = st.number_input("結束 Tick", min_value=0, value=10, step=1)

    if st.button("查詢歷史事件"):
        try:
            # TODO：呼叫 get_history(start_tick, end_tick)
            # 顯示查詢結果（事件列表），格式同事件流
            # 若無結果，顯示 st.info("此範圍內無事件")
            pass
        except Exception as e:
            st.error(f"查詢失敗：{e}")

    st.divider()

    # ── 快照查詢 ──
    st.markdown("### 📸 世界快照查詢")
    snapshot_tick = st.number_input("快照 Tick", min_value=0, value=0, step=1)

    if st.button("載入快照"):
        try:
            # TODO：呼叫 get_snapshot(snapshot_tick)
            # 若返回 None，顯示 st.warning("此 Tick 無快照紀錄")
            # 若有快照，用 st.json() 顯示快照的摘要資訊（tick / year / season / agent 數量）
            pass
        except Exception as e:
            st.error(f"快照載入失敗：{e}")

    st.divider()

    # ── 時間軸總覽 ──
    st.markdown("### 🗓️ 重大事件時間軸")
    if st.button("載入時間軸"):
        try:
            # TODO：呼叫 get_timeline()
            # 以 st.dataframe() 顯示 [{tick, event_type, description}] 列表
            pass
        except Exception as e:
            st.error(f"時間軸載入失敗：{e}")
```

---

### 步驟 7：實作自動刷新機制

在 `main()` 函數末尾加入自動刷新邏輯。Streamlit 的自動刷新需搭配 `time.sleep()` 與 `st.rerun()`。

```python
# 在 main() 函數末尾（所有 tab 渲染完畢之後）加入：

def main():
    # ... （前面的程式碼）...

    # ── 自動刷新機制 ──
    st.divider()
    col_refresh, col_countdown = st.columns([3, 1])

    with col_refresh:
        auto_refresh = st.checkbox("啟用自動刷新（每 10 秒）", value=True)

    with col_countdown:
        # TODO：顯示「上次更新時間」，格式：HH:MM:SS
        import datetime
        st.caption(f"上次更新：{datetime.datetime.now().strftime('%H:%M:%S')}")

    if auto_refresh:
        time.sleep(REFRESH_INTERVAL)
        st.rerun()
```

> **注意：** `st.rerun()` 是 Streamlit 1.27+ 的新 API，舊版使用 `st.experimental_rerun()`。若執行時出現 `AttributeError`，請改用 `st.experimental_rerun()`，或確認 Streamlit 版本：`streamlit --version`。
>
> **效能提示：** `time.sleep(10)` 會讓整個 App 暫停 10 秒，這在 Streamlit 的單執行緒模型下是正常行為。若要更精細的控制，可使用 `st.empty()` 配合倒數計時器。

---

### 步驟 8：測試啟動

在專案根目錄執行以下指令啟動 App：

```bash
# 切換到專案根目錄
cd c:\Users\zohanlin\Documents\zohan_ai_test\AI_World

# 啟動 Streamlit
streamlit run modules/m7_visualization/app.py
```

App 啟動後，瀏覽器應自動開啟 `http://localhost:8501`。

---

## 重要實作注意事項

### 1. sys.path 設定

由於 `app.py` 位於 `modules/m7_visualization/`，而 `shared/schemas.py` 位於專案根目錄，**必須**在 `app.py` 開頭加入路徑設定：

```python
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
```

這樣才能正確 `from shared.schemas import ...` 與 `from modules.m1_world_state.main import ...`。

### 2. 防禦性 import

M1 與 M6 可能尚未完成實作。使用 `try/except ImportError` 加上旗標（`M1_AVAILABLE`、`M6_AVAILABLE`）保護每個 import，讓 App 在依賴模組未就緒時仍能啟動並顯示友善訊息。

### 3. 不要讓 App crash

所有呼叫 M1/M6 函數的地方都必須包在 `try/except Exception` 中。資料庫不存在、連線失敗、資料格式錯誤等情況，應以 `st.warning()` 或 `st.error()` 顯示，**絕不允許顯示 Python traceback 給使用者**。

### 4. Plotly 格子地圖的 y 軸方向

Plotly Heatmap 預設 y=0 在底部（數學座標系），但地圖通常 y=0 在頂部。建議在 `fig.update_layout()` 中設定 `yaxis_autorange="reversed"`，或在建立 z 矩陣時翻轉 y 軸。

### 5. 中文字型支援

Plotly 預設字型可能不支援中文。若地圖 hover text 出現亂碼，在 `fig.update_layout()` 中加入：

```python
fig.update_layout(font=dict(family="Microsoft JhengHei, Arial, sans-serif"))
```

---

## 驗證標準（全部通過才算完成）

- [ ] 執行 `streamlit run modules/m7_visualization/app.py` 後，瀏覽器自動開啟且無 Python traceback
- [ ] 頁首顯示「🌍 AI World 即時儀表板」標題，以及當前 tick、年份、季節（使用 `st.metric()`）
- [ ] 四個分頁（世界地圖、Agent 狀態、事件流、歷史查詢）皆可正常切換，無任何分頁報錯
- [ ] 世界地圖分頁顯示所有 Location 的地形顏色格子圖（至少一個格子有顏色）
- [ ] 有 Agent 的格子上有明顯的 Agent 標記符號（「👤」或散點）
- [ ] Agent 狀態分頁的表格至少包含：`name`、`location_id`、`food`、`money`、`is_alive` 欄位
- [ ] 事件流分頁顯示最新事件，每行包含：`tick`、`event_type`、`description`
- [ ] 歷史查詢分頁：輸入 tick 範圍後點擊按鈕，能顯示對應事件（或顯示「無事件」訊息）
- [ ] 勾選「啟用自動刷新」後，App 每 10 秒自動重新讀取資料（可在 M1 更新資料後觀察）
- [ ] M1 或 M6 未就緒時，App **不 crash**，而是顯示友善的警告訊息
- [ ] 「上次更新時間」顯示正確的當前時間格式（HH:MM:SS）
