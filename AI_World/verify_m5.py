# verify_m5.py（在 AI_World/ 根目錄執行）
import sys
from pathlib import Path
import json
sys.path.insert(0, str(Path(__file__).parent))

from shared.schemas import Agent, AgentPersonality, Resource, Location, WorldState, Config
from modules.m1_world_state.main import init_world, update_agent
from modules.m5_rules.main import (
    validate_action,
    apply_resource_decay,
    check_survival,
    apply_economic_rules,
    get_rules_summary
)

print("=== M5 Rules Engine 驗證 ===\n")

# ── 載入 config 並初始化資料庫，以供 M1.get_world_state 讀取 ──────────
config = Config(**json.load(open("config.json")))

forest_location = Location(id="loc_forest", name="Deep Forest", x=0, y=0, terrain="forest")
plains_location = Location(id="loc_plains", name="Open Plains", x=1, y=0, terrain="plains")
mountain_location = Location(id="loc_mountain", name="High Mountain", x=2, y=0, terrain="mountain")

test_agent = Agent(
    id="agent_001",
    name="TestAgent",
    location_id="loc_plains",
    resources=Resource(food=50.0, water=50.0, energy=50.0, money=100.0, materials=20.0)
)

# 透過 M1 初始化 SQLite 資料庫，將測試資料寫入
init_world([forest_location, plains_location, mountain_location], config)
update_agent(test_agent)

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
assert ok == False, "[FAIL] 測試 1a 失敗：山地採集食物應被拒絕"
assert reason != "", "[FAIL] 測試 1a 失敗：拒絕原因不得為空字串"
print(f"[OK] 測試 1a 通過：山地採集食物被拒絕，原因：{reason}")

# 測試 1b：移動到不存在的地點（非法）
ok, reason = validate_action(test_agent, "我要移動到 loc_nonexistent")
assert ok == False, "[FAIL] 測試 1b 失敗：移動到不存在地點應被拒絕"
print(f"[OK] 測試 1b 通過：移動到不存在地點被拒絕，原因：{reason}")

# ── 驗證 2：validate_action() 對合法行動返回 (True, "") ──────────────

# 測試 2a：在森林採集食物（合法）
agent_in_forest = test_agent.model_copy(update={"location_id": "loc_forest"})
ok, reason = validate_action(agent_in_forest, "我要採集食物")
assert ok == True, f"[FAIL] 測試 2a 失敗：森林採集食物應被允許，但被拒絕：{reason}"
assert reason == "", f"[FAIL] 測試 2a 失敗：合法行動原因應為空字串，但為：{reason}"
print(f"[OK] 測試 2a 通過：森林採集食物被允許")

# 測試 2b：在平原採集食物（合法）
ok, reason = validate_action(test_agent, "我要採集食物")  # test_agent 在 plains
assert ok == True, f"[FAIL] 測試 2b 失敗：平原採集食物應被允許"
print(f"[OK] 測試 2b 通過：平原採集食物被允許")

# 測試 2c：移動到存在的地點（合法）
ok, reason = validate_action(test_agent, "我要移動到 loc_forest")
assert ok == True, f"[FAIL] 測試 2c 失敗：移動到存在地點應被允許，但被拒絕：{reason}"
print(f"[OK] 測試 2c 通過：移動到存在地點被允許")

# ── 驗證 3：apply_resource_decay() 後資源正確減少 ──────────────────

import copy
world_copy = copy.deepcopy(world)  # test_agent 在 plains
world_after = apply_resource_decay(world_copy)
agent_after = world_after.agents["agent_001"]

# 平原地形 food 應減少 5（50 - 5 = 45）
assert agent_after.resources.food == 45.0, \
    f"[FAIL] 測試 3a 失敗：平原地形 food 應為 45.0，實際：{agent_after.resources.food}"
print(f"[OK] 測試 3a 通過：平原地形 food 消耗 5，結果 {agent_after.resources.food}")

# water 應減少 4（50 - 4 = 46）
assert agent_after.resources.water == 46.0, \
    f"[FAIL] 測試 3b 失敗：water 應為 46.0，實際：{agent_after.resources.water}"
print(f"[OK] 測試 3b 通過：water 消耗 4，結果 {agent_after.resources.water}")

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
    f"[FAIL] 測試 3c 失敗：森林地形 food 應為 47.0，實際：{forest_agent_after.resources.food}"
print(f"[OK] 測試 3c 通過：森林地形 food 只消耗 3，結果 {forest_agent_after.resources.food}")

# ── 驗證 4：check_survival() 在 food <= 0 時返回 False ──────────────

dead_by_food = test_agent.model_copy(
    update={"resources": Resource(food=0.0, water=50.0, energy=50.0, money=100.0)}
)
assert check_survival(dead_by_food) == False, "[FAIL] 測試 4a 失敗：food=0 應返回 False"
print(f"[OK] 測試 4a 通過：food=0 返回 False（死亡）")

dead_by_water = test_agent.model_copy(
    update={"resources": Resource(food=50.0, water=0.0, energy=50.0, money=100.0)}
)
assert check_survival(dead_by_water) == False, "[FAIL] 測試 4b 失敗：water=0 應返回 False"
print(f"[OK] 測試 4b 通過：water=0 返回 False（死亡）")

healthy_agent = test_agent.model_copy(
    update={"resources": Resource(food=10.0, water=10.0, energy=50.0, money=100.0)}
)
assert check_survival(healthy_agent) == True, "[FAIL] 測試 4c 失敗：food=10 water=10 應返回 True"
print(f"[OK] 測試 4c 通過：food=10 water=10 返回 True（存活）")

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
    f"[FAIL] 測試 5 失敗：apply_economic_rules 後 money 應 >= 0，實際：{world_eco_after.agents['agent_eco'].resources.money}"
print(f"[OK] 測試 5 通過：apply_economic_rules 確保 money >= 0")

# ── 驗證 6：get_rules_summary() 返回 dict 且包含必要 key ──────────────

summary = get_rules_summary()
assert isinstance(summary, dict), "[FAIL] 測試 6 失敗：get_rules_summary() 應返回 dict"
required_keys = ["resource_decay", "action_rules", "economic_rules", "survival_rules"]
for key in required_keys:
    assert key in summary, f"[FAIL] 測試 6 失敗：summary 缺少 key '{key}'"
print(f"[OK] 測試 6 通過：get_rules_summary() 返回包含所有必要 key 的 dict")

print("\n[SUCCESS] M5 所有驗證通過！")
