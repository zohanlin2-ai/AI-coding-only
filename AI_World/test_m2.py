# test_m2.py（放在 AI_World/ 根目錄執行）
import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from shared.schemas import Config, AgentPersonality, Location
from modules.m1_world_state.main import init_world, get_world_state
from modules.m2_agent.main import create_agent, get_agent, agent_think, agent_act, update_agent_needs, list_agents

print("=== M2 Agent System 驗證 ===\n")

# 1. 載入 config 並初始化資料庫
config = Config(**json.load(open("config.json")))
# 建立測試地點 (village, forest, plains)
forest_loc = Location(id="loc_forest", name="forest", x=0, y=0, terrain="forest")
plains_loc = Location(id="loc_plains", name="plains", x=1, y=0, terrain="plains")
init_world([forest_loc, plains_loc], config)

# 2. 測試 create_agent
print("[1] 測試 create_agent...")
personality = AgentPersonality(hunger=0.3, fear=0.2, ambition=0.8, loyalty=0.5, aggression=0.4)
agent = create_agent("Xiaoming", "loc_forest", personality)
assert agent.name == "Xiaoming"
assert agent.location_id == "loc_forest"
assert agent.is_alive == True
print(f"[OK] 成功建立 Agent '{agent.name}' (id={agent.id})")

# 3. 測試 get_agent
print("\n[2] 測試 get_agent...")
fetched_agent = get_agent(agent.id)
assert fetched_agent.id == agent.id
assert fetched_agent.name == "Xiaoming"
print(f"[OK] 成功取得 Agent: {fetched_agent.name}")

# 測試無效 ID 拋出 KeyError
try:
    get_agent("invalid_id")
    assert False, "應拋出 KeyError"
except KeyError:
    print("[OK] 無效 ID 查詢成功攔截 KeyError")

# 4. 測試 agent_think (需呼叫 Ollama)
print("\n[3] 測試 agent_think (實際呼叫本地 LLM)...")
context = "四周非常安靜，森林裡有許多野果可以採集。"
action_text = agent_think(agent.id, context)
assert len(action_text) > 0
print(f"[OK] LLM 思考回應為: '{action_text}'")

# 5. 測試 agent_act
print("\n[4] 測試 agent_act...")
# 先手動設定為 "採集食物" 以測試動作解析
from modules.m2_agent.main import _last_action
_last_action[agent.id] = "我要在森林裡採集食物"

event = agent_act(agent.id)
assert event.event_type == "resource"
assert "採集" in event.description or "食物" in event.description

# 確認食物有增加 (Xiaoming 預設 100.0, 採集完 +10.0 = 110.0)
updated_agent = get_agent(agent.id)
assert updated_agent.resources.food == 110.0
print(f"[OK] 行動執行成功，食物增加後為: {updated_agent.resources.food:.1f}")

# 6. 測試 update_agent_needs
print("\n[5] 測試 update_agent_needs...")
# 記錄更新前數值
old_hunger = updated_agent.personality.hunger
old_energy = updated_agent.resources.energy
old_water = updated_agent.resources.water

update_agent_needs(agent.id)

decayed_agent = get_agent(agent.id)
assert decayed_agent.personality.hunger > old_hunger
assert decayed_agent.resources.energy < old_energy
assert decayed_agent.resources.water < old_water
print(f"[OK] 需求遞變成功: hunger={decayed_agent.personality.hunger:.2f}, energy={decayed_agent.resources.energy:.1f}, water={decayed_agent.resources.water:.1f}")

# 7. 測試 list_agents
print("\n[6] 測試 list_agents...")
alive_agents = list_agents()
assert len(alive_agents) == 1
assert alive_agents[0].id == agent.id
print(f"[OK] 存活 Agent 列表核對成功，數量: {len(alive_agents)}")

print("\n[SUCCESS] M2 所有測試通過！")
