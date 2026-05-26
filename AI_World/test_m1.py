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
print(f"[OK] 初始化成功，地點數：{len(state.locations)}")
for loc in state.locations.values():
    print(f"   - {loc.name} ({loc.terrain}) @ ({loc.x}, {loc.y})")

# ── 測試 2：get_world_state ────────────────────────────────
print("\n=== 測試 get_world_state ===")
state2 = get_world_state()
assert state2.tick == 0
assert state2.year == 1
assert state2.season == "spring"
print(f"[OK] tick={state2.tick}, year={state2.year}, season={state2.season}")

# ── 測試 3：update_agent ───────────────────────────────────
print("\n=== 測試 update_agent ===")
loc_id = list(state.locations.keys())[0]
new_agent = Agent(name="TestHero", location_id=loc_id)
update_agent(new_agent)
state3 = get_world_state()
assert new_agent.id in state3.agents, "Agent 應已存入世界狀態"
print(f"[OK] Agent '{new_agent.name}' (id={new_agent.id}) 已成功寫入")

# ── 測試 4：update_location_resources ─────────────────────
print("\n=== 測試 update_location_resources ===")
new_res = Resource(food=999.0, water=888.0, energy=777.0, money=666.0, materials=555.0)
update_location_resources(loc_id, new_res)
state4 = get_world_state()
assert state4.locations[loc_id].resources.food == 999.0, "food 應已更新為 999.0"
print(f"[OK] 地點資源已更新：food={state4.locations[loc_id].resources.food}")

# ── 測試 5：add_event ─────────────────────────────────────
print("\n=== 測試 add_event ===")
ev = WorldEvent(tick=0, event_type="discovery", description="發現了神秘石頭")
add_event(ev)
state5 = get_world_state()
assert any(e.id == ev.id for e in state5.events), "事件應已存入世界狀態"
print(f"[OK] 事件 '{ev.description}' 已成功新增")

# ── 測試 6：get_tick ───────────────────────────────────────
print("\n=== 測試 get_tick ===")
tick = get_tick()
assert tick == 0
print(f"[OK] 當前 tick = {tick}")

# ── 測試 7：save_state + load_state ───────────────────────
print("\n=== 測試 save_state + load_state ===")
save_state()
from pathlib import Path
assert Path("data/world_snapshot.json").exists(), "world_snapshot.json 應已建立"
loaded = load_state()
assert len(loaded.locations) == len(state5.locations), "地點數量應一致"
assert new_agent.id in loaded.agents, "Agent 應在 load 後仍存在"
print(f"[OK] save/load 一致：{len(loaded.locations)} 個地點，{len(loaded.agents)} 個 Agent")

print("\n[SUCCESS] 所有測試通過！")
