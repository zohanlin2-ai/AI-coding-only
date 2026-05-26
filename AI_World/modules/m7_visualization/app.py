# modules/m7_visualization/app.py
"""
M7 — AI World Visualization Dashboard
Provides real-time world map, agent statuses, event streams, and history queries in English.
Start command: streamlit run modules/m7_visualization/app.py
"""

import sys
import os
import time
import datetime
from typing import Optional

# Ensure importing root modules
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# Defensive imports of M1 and M6
try:
    from modules.m1_world_state.main import get_world_state
    M1_AVAILABLE = True
except Exception:
    M1_AVAILABLE = False

try:
    from modules.m6_time_history.main import (
        get_history,
        get_snapshot,
        get_timeline,
        get_current_season,
    )
    M6_AVAILABLE = True
except Exception:
    M6_AVAILABLE = False

from shared.schemas import WorldState, WorldEvent, Agent, Location

# Constants
REFRESH_INTERVAL = 10  # Seconds

TERRAIN_COLORS = {
    "plains":   "#a8d5a2",
    "mountain": "#9e9e9e",
    "forest":   "#2d6a4f",
    "water":    "#4fc3f7",
}
TERRAIN_INDEX = {"plains": 0, "forest": 1, "mountain": 2, "water": 3}

SEASON_LABEL = {
    "spring": "🌸 Spring",
    "summer": "☀️ Summer",
    "autumn": "🍂 Autumn",
    "winter": "❄️ Winter",
}

EVENT_EMOJI = {
    "interaction": "🟦",
    "resource":    "🟩",
    "conflict":    "🟥",
    "discovery":   "🟨",
    "death":       "⬛",
    "season_change": "🔵",
}


def safe_get_world_state() -> Optional[WorldState]:
    """Safely fetch world state from M1, show warning if failed."""
    if not M1_AVAILABLE:
        st.error("M1 World State Engine module could not be loaded.")
        return None
    try:
        return get_world_state()
    except Exception as e:
        st.warning(f"⚠️ Unable to read world state: {e}")
        return None


def _loc_name(world_state: WorldState, loc_id: str) -> str:
    loc = world_state.locations.get(loc_id)
    return loc.name if loc else loc_id


# ── Render Functions ──

def render_header(world_state: Optional[WorldState]) -> None:
    st.title("🌍 AI World Real-Time Dashboard")
    st.divider()

    if world_state is None:
        st.warning("⚠️ Unable to connect to M1 World State Engine, waiting for initialization...")
        return

    season_str = world_state.season
    if M6_AVAILABLE:
        try:
            season_str = get_current_season()
        except Exception:
            pass

    season_display = SEASON_LABEL.get(season_str, season_str)
    alive_count = sum(1 for a in world_state.agents.values() if a.is_alive)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("⏱️ Tick", world_state.tick)
    col2.metric("📅 Year", f"Year {world_state.year}")
    col3.metric("Season", season_display)
    col4.metric("👥 Alive Agents", alive_count)


def render_world_map(world_state: Optional[WorldState]) -> None:
    st.subheader("🗺️ World Map")

    if world_state is None or not world_state.locations:
        st.info("No map data available. Please verify M1 is initialized.")
        return

    locations = list(world_state.locations.values())
    max_x = max(loc.x for loc in locations)
    max_y = max(loc.y for loc in locations)
    grid_w = max_x + 1
    grid_h = max_y + 1

    z = [[0] * grid_w for _ in range(grid_h)]
    text = [[""] * grid_w for _ in range(grid_h)]
    loc_id_grid = [[None] * grid_w for _ in range(grid_h)]

    for loc in locations:
        row = loc.y
        col = loc.x
        z[row][col] = TERRAIN_INDEX.get(loc.terrain, 0)
        text[row][col] = f"{loc.name}<br>Terrain: {loc.terrain}"
        loc_id_grid[row][col] = loc.id

    agent_at: dict[str, list[str]] = {}
    for agent in world_state.agents.values():
        if agent.is_alive:
            agent_at.setdefault(agent.location_id, []).append(agent.name)

    for loc in locations:
        names = agent_at.get(loc.id, [])
        if names:
            text[loc.y][loc.x] += "<br>👤 " + ", ".join(names)

    colorscale = [
        [0.00, TERRAIN_COLORS["plains"]],
        [0.25, TERRAIN_COLORS["plains"]],
        [0.25, TERRAIN_COLORS["forest"]],
        [0.50, TERRAIN_COLORS["forest"]],
        [0.50, TERRAIN_COLORS["mountain"]],
        [0.75, TERRAIN_COLORS["mountain"]],
        [0.75, TERRAIN_COLORS["water"]],
        [1.00, TERRAIN_COLORS["water"]],
    ]

    fig = go.Figure(go.Heatmap(
        z=z,
        text=text,
        hoverinfo="text",
        colorscale=colorscale,
        showscale=False,
        zmin=0,
        zmax=3,
    ))

    agent_x, agent_y, agent_labels = [], [], []
    for loc in locations:
        names = agent_at.get(loc.id, [])
        if names:
            agent_x.append(loc.x)
            agent_y.append(loc.y)
            agent_labels.append(", ".join(names))

    if agent_x:
        fig.add_trace(go.Scatter(
            x=agent_x,
            y=agent_y,
            mode="markers+text",
            marker=dict(size=22, color="rgba(0,0,0,0)", line=dict(width=0)),
            text=["👤"] * len(agent_x),
            textfont=dict(size=18),
            hovertext=agent_labels,
            hoverinfo="text",
            name="Agents",
        ))

    fig.update_layout(
        xaxis=dict(title="X", dtick=1, tickmode="linear"),
        yaxis=dict(title="Y", dtick=1, tickmode="linear", autorange="reversed"),
        height=400,
        margin=dict(l=40, r=20, t=20, b=40),
        font=dict(family="Arial, sans-serif"),
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("**Terrain Legend:**")
    leg_cols = st.columns(len(TERRAIN_COLORS))
    labels = {
        "plains": "Magic Village (Plains)",
        "forest": "Magic Forest (Forest)",
        "mountain": "Ancient Ruins (Mountain)",
        "water": "Mana Spring (Water)",
    }
    for i, (terrain, color) in enumerate(TERRAIN_COLORS.items()):
        leg_cols[i].markdown(
            f'<span style="background:{color};padding:4px 12px;border-radius:4px;'
            f'color:#fff;font-size:13px;">■ {labels.get(terrain, terrain)}</span>',
            unsafe_allow_html=True,
        )


def render_agent_status(world_state: Optional[WorldState]) -> None:
    st.subheader("🧑 Agent Status Overview")

    if world_state is None or not world_state.agents:
        st.info("No Agent data available. Please verify M2 has registered agents.")
        return

    agents = list(world_state.agents.values())

    rows = []
    for a in agents:
        loc_name = _loc_name(world_state, a.location_id)
        gender_icon = "♂️" if getattr(a, "gender", "male") == "male" else "♀️"
        rows.append({
            "Name": f"{gender_icon} {a.name}",
            "Location": loc_name,
            "Food": round(a.resources.food, 1),
            "Water": round(a.resources.water, 1),
            "Energy": round(a.resources.energy, 1),
            "Mana": round(a.resources.mana, 1),
            "Money": round(a.resources.money, 1),
            "Materials": round(a.resources.materials, 1),
            "Alive": "✅" if a.is_alive else "❌",
            "Age (ticks)": a.age,
        })

    df = pd.DataFrame(rows)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Food":  st.column_config.ProgressColumn("Food", min_value=0, max_value=100),
            "Water":  st.column_config.ProgressColumn("Water", min_value=0, max_value=100),
            "Energy":  st.column_config.ProgressColumn("Energy", min_value=0, max_value=100),
            "Mana":  st.column_config.ProgressColumn("Mana 🔮", min_value=0, max_value=100),
            "Money":  st.column_config.NumberColumn("Money 💰"),
        },
    )

    st.subheader("🔍 Agent Detailed Info")
    agent_names = [a.name for a in agents]
    if not agent_names:
        return
    selected_name = st.selectbox("Select Agent", agent_names, key="agent_select")
    selected = next((a for a in agents if a.name == selected_name), None)
    if selected is None:
        return

    col_l, col_r = st.columns(2)

    with col_l:
        gender_display = "♂️ Male" if getattr(selected, "gender", "male") == "male" else "♀️ Female"
        st.markdown(f"**Gender**: {gender_display}")

        st.markdown("**Personality Traits**")
        personality_fields = [
            ("Hunger", selected.personality.hunger),
            ("Fear", selected.personality.fear),
            ("Ambition",   selected.personality.ambition),
            ("Loyalty", selected.personality.loyalty),
            ("Aggression", selected.personality.aggression),
        ]
        for label, val in personality_fields:
            st.write(f"{label}: {val:.2f}")
            st.progress(val)

        if selected.skills:
            st.markdown("**Skills**")
            for skill, level in selected.skills.items():
                st.write(f"- {skill}: {level:.2f}")
        else:
            st.markdown("**Skills**: (None)")

    with col_r:
        st.markdown("**Relationships with other Agents**")
        if selected.relationships:
            for other_id, rel in selected.relationships.items():
                other = world_state.agents.get(other_id)
                other_name = other.name if other else other_id
                bar_val = (rel + 1.0) / 2.0
                st.write(f"{other_name}: {rel:+.2f}")
                st.progress(bar_val)
        else:
            st.write("(No relationships established yet)")

        p = selected.personality
        radar_fig = go.Figure(go.Scatterpolar(
            r=[p.hunger, p.fear, p.ambition, p.loyalty, p.aggression],
            theta=["Hunger", "Fear", "Ambition", "Loyalty", "Aggression"],
            fill="toself",
            name=selected.name,
            line_color="#4e7df5",
        ))
        radar_fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
            showlegend=False,
            height=280,
            margin=dict(l=20, r=20, t=20, b=20),
            font=dict(family="Arial, sans-serif"),
        )
        st.plotly_chart(radar_fig, use_container_width=True)


def render_event_stream(world_state: Optional[WorldState]) -> None:
    st.subheader("📜 Latest Event Stream")

    if world_state is None:
        st.info("Unable to get event data.")
        return

    events = world_state.events
    if not events:
        st.info("No world events currently.")
        return

    recent_events = sorted(events, key=lambda e: e.tick, reverse=True)[:50]

    with st.container(height=500):
        for ev in recent_events:
            emoji = EVENT_EMOJI.get(ev.event_type, "⚪")
            st.markdown(
                f"**[Tick {ev.tick}]** {emoji} **{ev.event_type.upper()}**  \n"
                f"{ev.description}"
            )
            st.divider()


def render_history_query() -> None:
    st.subheader("🕰️ History Query")

    if not M6_AVAILABLE:
        st.error("M6 Time & History module not ready, cannot query history.")
        return

    st.markdown("### 📋 Event Range Query")
    col1, col2 = st.columns(2)
    with col1:
        start_tick = st.number_input("Start Tick", min_value=0, value=0, step=1, key="hist_start")
    with col2:
        end_tick = st.number_input("End Tick", min_value=0, value=20, step=1, key="hist_end")

    if st.button("Query History Events", key="btn_hist"):
        try:
            hist = get_history(int(start_tick), int(end_tick))
            if hist:
                with st.container(height=400):
                    for ev in hist:
                        emoji = EVENT_EMOJI.get(ev.event_type, "⚪")
                        st.markdown(
                            f"**[Tick {ev.tick}]** {emoji} **{ev.event_type.upper()}**  \n"
                            f"{ev.description}"
                        )
                        st.divider()
            else:
                st.info("No events in this range.")
        except Exception as e:
            st.error(f"Query failed: {e}")

    st.divider()

    st.markdown("### 📸 World Snapshot Query")
    snapshot_tick = st.number_input("Snapshot Tick", min_value=0, value=0, step=1, key="snap_tick")

    if st.button("Load Snapshot", key="btn_snap"):
        try:
            snap = get_snapshot(int(snapshot_tick))
            if snap is None:
                st.warning(f"No snapshot record at Tick {int(snapshot_tick)}.")
            else:
                st.success(f"Successfully loaded snapshot at Tick {snap.tick}")
                st.json({
                    "tick": snap.tick,
                    "year": snap.year,
                    "season": snap.season,
                    "location_count": len(snap.locations),
                    "agent_count": len(snap.agents),
                    "event_count": len(snap.events),
                })
        except Exception as e:
            st.error(f"Snapshot load failed: {e}")

    st.divider()

    st.markdown("### 🗓️ Major Event Timeline")
    if st.button("Load Timeline", key="btn_timeline"):
        try:
            timeline = get_timeline()
            if timeline:
                with st.container(height=400):
                    for ev in timeline:
                        emoji = EVENT_EMOJI.get(ev["event_type"], "⚪")
                        st.markdown(
                            f"**[Tick {ev['tick']}]** {emoji} **{ev['event_type'].upper()}**  \n"
                            f"{ev['description']}"
                        )
                        st.divider()
            else:
                st.info("No major events currently (conflicts, deaths, discoveries, season changes).")
        except Exception as e:
            st.error(f"Timeline load failed: {e}")


# ── Entrypoint ──

def main():
    st.set_page_config(
        page_title="AI World Dashboard",
        page_icon="🌍",
        layout="wide",
    )

    world_state = safe_get_world_state()
    render_header(world_state)

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

    st.divider()
    col_refresh, col_time = st.columns([3, 1])

    with col_refresh:
        auto_refresh = st.checkbox("Enable Auto Refresh (every 10 seconds)", value=False, key="auto_refresh")

    with col_time:
        st.caption(f"Last updated: {datetime.datetime.now().strftime('%H:%M:%S')}")

    if auto_refresh:
        time.sleep(REFRESH_INTERVAL)
        st.rerun()


if __name__ == "__main__":
    main()
