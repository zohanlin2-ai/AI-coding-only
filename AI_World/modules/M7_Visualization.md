# Module M7: Visualization Dashboard

## Your Task

Create a Streamlit visualization App that allows human observers to monitor the state of the AI World in real-time, including the world map, Agent status, event stream, and historical snapshot queries, with all data read from M1 and M6.

---

## Scope of Responsibility

- **Responsible for:**
  - Start and maintain a Streamlit Web App (`app.py`)
  - Auto-refresh the screen every 10 seconds, retrieving the latest world state from M1
  - Present the world map as a color grid (terrain + Agent position markers)
  - Display all Agent resources and personality metrics in a table
  - Display the latest 50 world events in a list
  - Provide tick range input to query historical events from M6
  - Display global information such as current tick, year, and season in the header

- **Not responsible for:**
  - Modifying or writing world state (read-only)
  - Operating the database directly (accessed via M1/M6 interfaces)
  - Agent decision-making, LLM calling, and rule execution
  - Any external APIs or functions (M7 has no external interface)

---

## Dependencies

- **Prerequisites:**
  - M0 (Generates `config.json`, M7 reads it to obtain settings like `tick_interval_sec`)
  - M1 (`get_world_state()` must be callable normally)
  - M6 (`get_history()`, `get_snapshot()`, `get_timeline()`, `get_current_season()` must be callable normally)

- **Used by the following modules:**
  - M8 (Verifies Streamlit App can start normally during integration testing)

---

## Working Directory

```
c:\Users\zohanlin\Documents\zohan_ai_test\AI_World\modules\m7_visualization\
```

All commands are run at the project root `c:\Users\zohanlin\Documents\zohan_ai_test\AI_World\`.

---

## Environment Setup

```bash
pip install streamlit pandas plotly pydantic
```

> **Note:** The `pydantic` version must be v2 (`pydantic>=2.0`). If an older version is already installed, please run `pip install --upgrade pydantic`.

---

## Files to Create

```
AI_World/
└── modules/
    └── m7_visualization/
        └── app.py          ← The only file to create
```

`shared/schemas.py` and other modules already exist, no need to recreate.

---

## Shared Schema (Use directly, do not modify)

The following Schema is defined in `shared/schemas.py`. M7 needs to import and use it directly; **do not define alternative classes yourself**.

```python
# shared/schemas.py (Excerpt of parts M7 will use)

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
    hunger: float = 0.3      # 0.0~1.0, higher means hungrier
    fear: float = 0.3        # 0.0~1.0, higher means more fearful
    ambition: float = 0.5    # 0.0~1.0, higher means more ambitious
    loyalty: float = 0.5     # 0.0~1.0, higher means more loyal
    aggression: float = 0.3  # 0.0~1.0, higher means more aggressive


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
    age: int = 0  # Unit: tick


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

### Terrain Color Map (M7 self-defined, not part of the Schema)

| terrain Value  | Recommended Display Color |
|-------------|-------------|
| `"plains"`  | Yellow-green `#a8d5a2` |
| `"mountain"` | Gray `#9e9e9e` |
| `"forest"`  | Dark green `#2d6a4f` |
| `"water"`   | Blue `#4fc3f7` |

### Season Symbol Correspondence (for header display)

| season Value   | Recommended Symbol |
|-------------|---------|
| `"spring"`  | 🌸 Spring |
| `"summer"`  | ☀️ Summer |
| `"autumn"`  | 🍂 Autumn |
| `"winter"`  | ❄️ Winter |

---

## Provided Functions (Signatures cannot be modified)

**M7 has no external functions.** M7 is an independent Streamlit App that does not provide any functions that can be imported by other modules.

Starting method:
```bash
streamlit run modules/m7_visualization/app.py
```

---

## External Functions You Can Call

### From M1 (`modules/m1_world_state/main.py`)

```python
from modules.m1_world_state.main import get_world_state

def get_world_state() -> WorldState:
    """Read the current complete world state, containing all locations, agents, organizations, events"""
```

### From M6 (`modules/m6_time_history/main.py`)

```python
from modules.m6_time_history.main import get_history, get_snapshot, get_timeline, get_current_season

def get_history(start_tick: int, end_tick: int) -> list[WorldEvent]:
    """Get the list of historical events in the specified tick range"""

def get_snapshot(tick: int) -> Optional[WorldState]:
    """Get the world snapshot for the specified tick, returns None if no snapshot exists"""

def get_timeline() -> list[dict]:
    """Return the timeline list of all major events, format: [{tick, event_type, description}, ...]"""

def get_current_season() -> str:
    """Return the current season string: 'spring' | 'summer' | 'autumn' | 'winter'"""
```

> **Note:** When calling these functions, ensure that M1 and M6's database (`data/world.db`) already exists and is initialized. If the database does not exist, use `try/except` to catch exceptions and display a user-friendly error message on the UI. **Do not let the App crash.**

---

## Implementation Steps

### Step 0: Create Directory and Empty File

```bash
# Execute at the project root directory
mkdir modules\m7_visualization
type nul > modules\m7_visualization\app.py
```

---

### Step 1: Create `app.py` Basic Skeleton and Page Routes

The overall structure of `app.py` is as follows. Create the skeleton first, then fill in each tab's logic step-by-step.

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

# ── Path Settings (ensure shared and modules can be imported from project root) ──
# Add project root directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# ── External Module Imports ──
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


# ── Constant Settings ──
REFRESH_INTERVAL = 10      # Auto-refresh interval in seconds
TERRAIN_COLORS = {
    "plains":   "#a8d5a2",
    "mountain": "#9e9e9e",
    "forest":   "#2d6a4f",
    "water":    "#4fc3f7",
}
SEASON_EMOJI = {
    "spring": "🌸 Spring",
    "summer": "☀️ Summer",
    "autumn": "🍂 Autumn",
    "winter": "❄️ Winter",
}


# ── Helper Functions ──
def load_config() -> dict:
    """Read config.json, returns default values on failure"""
    # TODO: Open config.json, parse and return dict
    # If file does not exist, return {"tick_interval_sec": 30}
    pass


def safe_get_world_state() -> Optional[WorldState]:
    """Safely call M1, returns None and displays warning on failure"""
    # TODO: Call get_world_state(), catch all exceptions
    # On exception, show message with st.warning(), return None
    pass


# ── Page Rendering Functions (to be implemented in separate steps) ──
def render_header(world_state: Optional[WorldState]) -> None:
    """Render header: Title + current tick / year / season"""
    # TODO: To be implemented in Step 2
    pass


def render_world_map(world_state: Optional[WorldState]) -> None:
    """Render world map tab"""
    # TODO: To be implemented in Step 3
    pass


def render_agent_status(world_state: Optional[WorldState]) -> None:
    """Render Agent status tab"""
    # TODO: To be implemented in Step 4
    pass


def render_event_stream(world_state: Optional[WorldState]) -> None:
    """Render event stream tab"""
    # TODO: To be implemented in Step 5
    pass


def render_history_query() -> None:
    """Render history query tab"""
    # TODO: To be implemented in Step 6
    pass


# ── Main Program Entry ──
def main():
    st.set_page_config(
        page_title="AI World Dashboard",
        page_icon="🌍",
        layout="wide",
    )

    # Read world state (shared by all tabs)
    world_state = safe_get_world_state()

    # Render header
    render_header(world_state)

    # Tab navigation
    tab1, tab2, tab3, tab4 = st.tabs([
        "🗺️ World Map",
        "🧑 Agent Status",
        "📜 Event Stream",
        "🕰️ History Query",
    ])

    with tab1:
        render_world_map(world_state)

    with tab2:
        render_agent_status(world_state)

    with tab3:
        render_event_stream(world_state)

    with tab4:
        render_history_query()

    # ── Auto-Refresh Mechanism ──
    # TODO: To be implemented in Step 7


if __name__ == "__main__":
    main()
```

---

### Step 2: Implement `render_header()`

Display the AI World title, current tick, year, and season in the header. If `world_state` is `None` (M1 is not ready yet), display "Waiting for world initialization...".

```python
def render_header(world_state: Optional[WorldState]) -> None:
    st.title("🌍 AI World Real-time Dashboard")
    st.divider()

    if world_state is None:
        st.warning("⚠️ Unable to connect to M1 World State Engine, waiting for world initialization...")
        return

    # Get current season (prioritize M6, fallback to WorldState on failure)
    season_str = world_state.season
    if M6_AVAILABLE:
        try:
            season_str = get_current_season()
        except Exception:
            pass  # Use world_state.season as fallback

    season_display = SEASON_EMOJI.get(season_str, season_str)

    # TODO: Use st.columns(3) to display side-by-side:
    #   col1 → "⏱️ Tick: {world_state.tick}"
    #   col2 → "📅 Year: Year {world_state.year}"
    #   col3 → "Season: {season_display}"
    # Display each using st.metric() for better visual presentation
    pass
```

---

### Step 3: Implement `render_world_map()`

Use Plotly's `go.Heatmap` or custom grid map to present terrain with colors, and mark grids containing Agents with the symbol "👤".

```python
def render_world_map(world_state: Optional[WorldState]) -> None:
    st.subheader("🗺️ World Map")

    if world_state is None or not world_state.locations:
        st.info("No map data available yet. Please confirm M1 has initialized and created Locations.")
        return

    locations = list(world_state.locations.values())

    # Calculate map boundaries
    max_x = max(loc.x for loc in locations)
    max_y = max(loc.y for loc in locations)

    # Create grid matrix: z value represents terrain (using integer index mapped to color)
    # Create Agent position lookup table: location_id → list of Agent names
    # TODO:
    #   1. Create a (max_y+1) x (max_x+1) 2D array, filling in terrain index (0~3)
    #   2. Create a (max_y+1) x (max_x+1) text array, filling in grid details (Location name + Agent name)
    #   3. Draw terrain base map using go.Figure(go.Heatmap(...))
    #      colorscale maps to the 4 colors of TERRAIN_COLORS
    #   4. Overlay go.Scatter scatter plot for grids with Agents, symbol "👤"
    #   5. st.plotly_chart(fig, use_container_width=True)

    # ── Legend Description ──
    st.markdown("**Terrain Legend:**")
    cols = st.columns(len(TERRAIN_COLORS))
    for i, (terrain, color) in enumerate(TERRAIN_COLORS.items()):
        # TODO: Use cols[i].markdown() to display color block and terrain name
        pass
```

> **Hint:** Plotly Heatmap's `colorscale` accepts `[[0, "#color1"], [0.33, "#color2"], ...]` format. The terrain index mapping is recommended as: `plains=0, forest=1, mountain=2, water=3`.

---

### Step 4: Implement `render_agent_status()`

Display a status table of all Agents with `st.dataframe()`, and provide detailed expansion blocks for individual Agents.

```python
def render_agent_status(world_state: Optional[WorldState]) -> None:
    st.subheader("🧑 Agent Status Overview")

    if world_state is None or not world_state.agents:
        st.info("No Agent data available yet. Please confirm M2 has created Agents.")
        return

    agents = list(world_state.agents.values())

    # ── Main Table ──
    # TODO: Convert agents to list of dicts, fields including:
    #   name, location_id (can be mapped to location name),
    #   food, water, energy, money, materials,
    #   is_alive (display ✅ / ❌), age
    # Create table using pd.DataFrame(), then display with st.dataframe()
    # Recommend using st.dataframe's column_config to configure progress bar styles for numerical columns

    # ── Individual Agent Details ──
    st.subheader("🔍 Detailed Agent Data")
    agent_names = [a.name for a in agents]
    selected_name = st.selectbox("Select Agent", agent_names)

    # TODO: Find Agent object corresponding to selected_name
    # Use st.expander() or st.columns() to display:
    #   - Personality traits (hunger/fear/ambition/loyalty/aggression) using progress bars or radar charts
    #   - Skills list (skills dict)
    #   - Relationships list (relationships dict, displaying target Agent name and relationship score)
    pass
```

> **Hint:** `st.progress(value)` can display a progress bar from 0.0~1.0, suitable for personality metrics. Plotly's `go.Scatterpolar` can draw a radar chart to present the 5D personality data.

---

### Step 5: Implement `render_event_stream()`

Display the latest 50 world events, distinguishing event types with different colors.

```python
def render_event_stream(world_state: Optional[WorldState]) -> None:
    st.subheader("📜 Latest Event Stream")

    if world_state is None:
        st.info("Unable to retrieve event data.")
        return

    events = world_state.events

    if not events:
        st.info("No world events recorded yet.")
        return

    # Only display latest 50 items, sorted in descending order by tick (newest first)
    recent_events = sorted(events, key=lambda e: e.tick, reverse=True)[:50]

    # Event types mapped to color badges
    EVENT_COLORS = {
        "interaction": "🟦",
        "resource":    "🟩",
        "conflict":    "🟥",
        "discovery":   "🟨",
        "death":       "⬛",
    }

    # TODO: Convert events to DataFrame, fields: tick, event_type, description, timestamp
    # Method 1 (Simple): Use st.dataframe() to display table
    # Method 2 (Aesthetic): Use a loop to call st.markdown() for each event on a line
    #   Format example: "{emoji} **[Tick {tick}]** `{event_type}` — {description}"
    pass
```

---

### Step 6: Implement `render_history_query()`

Provide tick range inputs, call M6 to query historical events, and display the world snapshot for the specified tick.

```python
def render_history_query() -> None:
    st.subheader("🕰️ History Query")

    if not M6_AVAILABLE:
        st.error("M6 Time & History module is not ready yet, unable to query history.")
        return

    # ── Event Range Query ──
    st.markdown("### 📋 Event Range Query")
    col1, col2 = st.columns(2)
    with col1:
        start_tick = st.number_input("Start Tick", min_value=0, value=0, step=1)
    with col2:
        end_tick = st.number_input("End Tick", min_value=0, value=10, step=1)

    if st.button("Query Historical Events"):
        try:
            # TODO: Call get_history(start_tick, end_tick)
            # Display query results (event list), same format as event stream
            # If no results, show st.info("No events in this range")
            pass
        except Exception as e:
            st.error(f"Query failed: {e}")

    st.divider()

    # ── Snapshot Query ──
    st.markdown("### 📸 Snapshot Query")
    snapshot_tick = st.number_input("Snapshot Tick", min_value=0, value=0, step=1)

    if st.button("Load Snapshot"):
        try:
            # TODO: Call get_snapshot(snapshot_tick)
            # If returns None, show st.warning("No snapshot record for this Tick")
            # If snapshot exists, use st.json() to display snapshot summary (tick / year / season / agent count)
            pass
        except Exception as e:
            st.error(f"Snapshot load failed: {e}")

    st.divider()

    # ── Timeline Overview ──
    st.markdown("### 🗓️ Major Event Timeline")
    if st.button("Load Timeline"):
        try:
            # TODO: Call get_timeline()
            # Display [{tick, event_type, description}] list with st.dataframe()
            pass
        except Exception as e:
            st.error(f"Timeline load failed: {e}")
```

---

### Step 7: Implement Auto-Refresh Mechanism

Add auto-refresh logic to the end of the `main()` function. Streamlit's auto-refresh needs to be implemented with `time.sleep()` and `st.rerun()`.

```python
# Add at the end of main() function (after rendering all tabs):

def main():
    # ... (previous code) ...

    # ── Auto-Refresh Mechanism ──
    st.divider()
    col_refresh, col_countdown = st.columns([3, 1])

    with col_refresh:
        auto_refresh = st.checkbox("Enable Auto-Refresh (every 10 seconds)", value=True)

    with col_countdown:
        # TODO: Display "Last updated time", format: HH:MM:SS
        import datetime
        st.caption(f"Last Updated: {datetime.datetime.now().strftime('%H:%M:%S')}")

    if auto_refresh:
        time.sleep(REFRESH_INTERVAL)
        st.rerun()
```

> **Note:** `st.rerun()` is a new API in Streamlit 1.27+. Older versions use `st.experimental_rerun()`. If `AttributeError` occurs during execution, please switch to `st.experimental_rerun()`, or check Streamlit version: `streamlit --version`.
>
> **Performance Tip:** `time.sleep(10)` pauses the entire App for 10 seconds, which is normal behavior under Streamlit's single-thread model. For more precise control, use `st.empty()` with a countdown timer.

---

### Step 8: Test Startup

Start the App by running the following command from the project root directory:

```bash
# Switch to project root directory
cd c:\Users\zohanlin\Documents\zohan_ai_test\AI_World

# Start Streamlit
streamlit run modules/m7_visualization/app.py
```

Once the App is started, the browser should open `http://localhost:8501` automatically.

---

## Important Implementation Notes

### 1. sys.path Settings

Since `app.py` is located in `modules/m7_visualization/` and `shared/schemas.py` is in the project root, path settings **must** be added at the beginning of `app.py`:

```python
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
```

This ensures correct imports of `from shared.schemas import ...` and `from modules.m1_world_state.main import ...`.

### 2. Defensive Imports

M1 and M6 implementations might not be completed. Protect each import with `try/except ImportError` along with flags (`M1_AVAILABLE`, `M6_AVAILABLE`), allowing the App to start and display friendly messages even when dependent modules are not ready.

### 3. Do Not Let App Crash

All places calling M1/M6 functions must be wrapped in `try/except Exception`. Situations like database non-existence, connection failure, or data format errors should be displayed using `st.warning()` or `st.error()`. **Never display Python tracebacks to users.**

### 4. Plotly Grid Map y-Axis Direction

Plotly Heatmap defaults to y=0 at the bottom (mathematical coordinate system), but maps usually have y=0 at the top. It is recommended to configure `yaxis_autorange="reversed"` in `fig.update_layout()`, or flip the y-axis when creating the z matrix.

### 5. Chinese Font Support

The default font of Plotly might not support Chinese. If map hover text shows garbled characters, add to `fig.update_layout()`:

```python
fig.update_layout(font=dict(family="Microsoft JhengHei, Arial, sans-serif"))
```

---

## Verification Standards (Must pass all to be considered complete)

- [ ] After running `streamlit run modules/m7_visualization/app.py`, the browser opens automatically with no Python traceback
- [ ] Header displays "🌍 AI World Real-time Dashboard" title, along with current tick, year, and season (using `st.metric()`)
- [ ] All four tabs (World Map, Agent Status, Event Stream, History Query) switch normally with no errors in any tab
- [ ] World Map tab displays a terrain color grid map for all Locations (at least one grid cell has color)
- [ ] Grids with Agents have clear Agent markers ("👤" or scatter dots)
- [ ] Agent Status tab table contains at least: `name`, `location_id`, `food`, `money`, `is_alive` fields
- [ ] Event Stream tab displays latest events; each line includes: `tick`, `event_type`, `description`
- [ ] History Query tab: after entering a tick range and clicking the button, corresponding events are displayed (or a "no events" message is shown)
- [ ] After checking "Enable Auto-Refresh", the App automatically reloads data every 10 seconds (can be observed after M1 updates data)
- [ ] When M1 or M6 is not ready, the App **does not crash** but displays friendly warning messages
- [ ] "Last updated time" displays correct current time format (HH:MM:SS)
