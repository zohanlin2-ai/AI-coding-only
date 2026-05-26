# verify_m4.py (在 AI_World/ 根目錄執行)
import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from shared.schemas import Config, AgentPersonality, Location, WorldEvent
from modules.m1_world_state.main import init_world, get_world_state, get_tick
from modules.m2_agent.main import create_agent, get_agent
from modules.m3_memory.main import recall_memory
from modules.m4_multi_agent.main import (
    run_tick,
    run_agent_interaction,
    negotiate,
    get_nearby_agents,
)

print("=== M4 Multi-Agent Interaction Engine 驗證 ===\n")

# 1. 載入 config 並初始化世界
config = Config(**json.load(open("config.json")))

# 建立 3 個不同座標的地點
# village at (0, 0)
# plains at (0, 1) - within Chebyshev distance 1 from village
# mountain at (5, 5) - far away
loc_village = Location(id="loc_village", name="village", x=0, y=0, terrain="plains")
loc_plains = Location(id="loc_plains", name="plains", x=0, y=1, terrain="plains")
loc_mountain = Location(id="loc_mountain", name="mountain", x=5, y=5, terrain="mountain")

init_world([loc_village, loc_plains, loc_mountain], config)

# 建立 3 個 Agent，分別放在不同地點
p_friendly = AgentPersonality(hunger=0.3, fear=0.2, ambition=0.5, loyalty=0.9, aggression=0.1)
p_aggressive = AgentPersonality(hunger=0.3, fear=0.2, ambition=0.8, loyalty=0.3, aggression=0.8)

agent_a = create_agent("Agent_A", "loc_village", p_friendly)
agent_b = create_agent("Agent_B", "loc_plains", p_friendly)
agent_c = create_agent("Agent_C", "loc_mountain", p_aggressive)

print("[1] 驗證環境導入...")
print("[OK] import OK")

# 2. 測試 get_nearby_agents()
print("\n[2] 測試 get_nearby_agents()...")
# 2.1 A(0,0) 與 B(0,1) Chebyshev 距離為 1，C(5,5) 距離為 5。
# 呼叫 get_nearby_agents(A, radius=1) 應該只返回 B，不返回 C。
nearby_a = get_nearby_agents(agent_a.id, radius=1)
nearby_ids = [ag.id for ag in nearby_a]
assert agent_b.id in nearby_ids, "B 應該在 A 的鄰近列表中"
assert agent_c.id not in nearby_ids, "C 不應該在 A 的鄰近列表中"
print("[OK] get_nearby_agents() 只返回半徑內的 Agent")

# 2.2 不返回自身
assert agent_a.id not in nearby_ids, "鄰近列表不應包含呼叫者自身"
print("[OK] get_nearby_agents() 不返回自身")

# 2.3 不返回死亡 Agent
# 先手動將 B 的 is_alive 設為 False 存回世界狀態
b_state = get_agent(agent_b.id)
b_state.is_alive = False
from modules.m1_world_state.main import update_agent
update_agent(b_state)

nearby_a_after_death = get_nearby_agents(agent_a.id, radius=1)
assert len(nearby_a_after_death) == 0, "B 死亡後，A 附近不應有其他存活 Agent"
print("[OK] get_nearby_agents() 不返回死亡 Agent")

# 將 B 設回存活
b_state.is_alive = True
update_agent(b_state)

# 3. 測試 run_agent_interaction()
print("\n[3] 測試 run_agent_interaction()...")
# 觸發 A 與 B 的互動
event = run_agent_interaction(agent_a.id, agent_b.id)
assert isinstance(event, WorldEvent), "應返回 WorldEvent 物件"
assert event.event_type in ("interaction", "conflict"), "事件型態應為 interaction 或 conflict"
assert agent_a.id in event.affected_agent_ids, "A 的 ID 應在受影響 ID 中"
assert agent_b.id in event.affected_agent_ids, "B 的 ID 應在受影響 ID 中"
print(f"[OK] run_agent_interaction() 成功，事件類型: {event.event_type}")

# 4. 測試 negotiate()
print("\n[4] 測試 negotiate()...")
# A 與 B 皆為 friendly (loyalty=0.9, aggression=0.1)，成功率應很高 (>0.5)
result = negotiate(agent_a.id, agent_b.id, "分配採集到的野果")
assert isinstance(result, dict), "談判結果應為 dict"
assert "success" in result, "結果應包含 success"
assert "outcome" in result, "結果應包含 outcome"
print(f"[OK] negotiate() 成功返回 dict，success={result['success']}")

# 驗證成功時關係是否有提升
a_after = get_agent(agent_a.id)
b_after = get_agent(agent_b.id)
rel_a_to_b = a_after.relationships.get(agent_b.id, 0.0)
rel_b_to_a = b_after.relationships.get(agent_a.id, 0.0)
assert rel_a_to_b > 0.0, "談判成功，A 對 B 的關係分數應有所提升"
assert rel_b_to_a > 0.0, "談判成功，B 對 A 的關係分數應有所提升"
print(f"[OK] 談判成功 relationship 有更新，A->B: {rel_a_to_b:.2f}, B->A: {rel_b_to_a:.2f}")

# 5. 測試 run_tick() 完整驅動與其餘驗證
print("\n[5] 測試 run_tick() 完整驅動與 integration...")
# 獲取當前世界事件數量
state_before = get_world_state()
events_count_before = len(state_before.events)

# 執行一個完整 tick
tick_events = run_tick()
assert len(tick_events) >= 1, "run_tick() 至少應返回 1 個事件"
print(f"[OK] run_tick() 執行成功，返回了 {len(tick_events)} 個事件")

# 驗證事件是否已寫入 M1
state_after = get_world_state()
events_count_after = len(state_after.events)
assert events_count_after > events_count_before, "事件應已成功寫入 M1"
print(f"[OK] 事件已寫入 M1，事件數從 {events_count_before} 增加到 {events_count_after}")

# 驗證記憶已寫入 M3
memories_a = recall_memory(agent_a.id, "行動", top_k=5)
assert len(memories_a) >= 1, "Agent A 應至少擁有一條最近行動記憶"
print(f"[OK] 記憶已寫入 M3，Agent A 召回記憶: {memories_a[0][:50]}...")

# 6. 驗證死亡 Agent 不再參與 tick
print("\n[6] 驗證死亡 Agent 不再參與 tick...")
# 讓 Agent C 死亡 (food = 0)
c_state = get_agent(agent_c.id)
c_state.resources.food = 0.0
update_agent(c_state)

# 執行下一次 tick
tick_events_2 = run_tick()
# 檢查 tick_events_2 中除了可能的死亡事件(death)之外，不應有 C 產生的行動事件
for ev in tick_events_2:
    if agent_c.id in ev.affected_agent_ids:
        # 如果是 death 事件，允許
        if ev.event_type == "death":
            continue
        # 其他事件，例如 interaction、resource 等，不應由 C 主動觸發
        # 由於 C 已經死了，他不應是受害者/行動主體 (除了被動列在其他人的 interaction/conflict 中，但其他人不能找死人互動)
        # 所以他的行動不應被執行
        assert False, f"死亡 Agent C 參與了非死亡事件: {ev.description}"

print("[OK] 死亡 Agent 不再參與 tick 行動")

print("\n[SUCCESS] M4 所有測試通過！")
