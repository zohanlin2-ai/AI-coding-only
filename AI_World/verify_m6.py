# verify_m6.py (在 AI_World/ 根目錄執行)
import sys
import json
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from shared.schemas import Config, Location, WorldState, WorldEvent
from modules.m1_world_state.main import init_world, get_world_state, get_tick
from modules.m1_world_state import database as db
from modules.m6_time_history.main import (
    advance_tick,
    get_history,
    save_snapshot,
    get_snapshot,
    get_timeline,
    get_current_season,
)

print("=== M6 Time & History System 驗證 ===\n")

# 1. 載入 config 並初始化世界
config = Config(**json.load(open("config.json")))
loc = Location(id="loc_village", name="village", x=0, y=0, terrain="plains")
init_world([loc], config)

print("[1] 驗證環境導入與基本屬性...")
season = get_current_season()
assert season in ("spring", "summer", "autumn", "winter"), f"未知季節: {season}"
print(f"[OK] get_current_season() 回傳正確字串: {season}")

# 2. 測試 advance_tick() 遞增
print("\n[2] 測試 advance_tick() 回傳值與遞增...")
t0 = get_tick()
t1 = advance_tick()
assert isinstance(t1, int), "advance_tick 應返回 int"
assert t1 == t0 + 1, f"advance_tick 應返回 {t0+1}，但得到 {t1}"
t2 = advance_tick()
assert t2 == t1 + 1, f"advance_tick 應返回 {t1+1}，但得到 {t2}"
print(f"[OK] advance_tick() 回傳與遞增正確 (t0={t0}, t1={t1}, t2={t2})")

# 3. 測試季節切換 (從 spring 進入 summer)
print("\n[3] 測試季節切換 (Spring -> Summer)...")
# 將 tick 設為 29 (spring 最後一天)
db.upsert_world_meta(29, 1, "spring")
assert get_tick() == 29
assert get_current_season() == "spring"

# 推進到 30
t_30 = advance_tick()
assert t_30 == 30
assert get_current_season() == "summer", f"tick 30 應為 summer，但得到 {get_current_season()}"

# 檢查是否寫入了 season_change 事件
state = get_world_state()
events = state.events
season_change_events = [e for e in events if e.event_type == "season_change"]
assert len(season_change_events) >= 1, "季節改變應新增 season_change 事件"
print(f"[OK] 成功切換到 summer，事件說明: '{season_change_events[-1].description}'")

# 4. 測試跨年切換 (Winter -> Spring, year + 1)
print("\n[4] 測試年份遞增與季節循環 (Winter -> Spring, Year+1)...")
# 將 tick 設為 119 (winter 最後一天)
db.upsert_world_meta(119, 1, "winter")
assert get_tick() == 119
assert get_current_season() == "winter"

# 推進到 120
t_120 = advance_tick()
assert t_120 == 120
state = get_world_state()
meta = db.get_world_meta()
assert meta["season"] == "spring", f"tick 120 應為 spring，但得到 {meta['season']}"
assert meta["year"] == 2, f"tick 120 應為第 2 年，但得到 {meta['year']}"
print(f"[OK] 成功切換到第二年春季: year={meta['year']}, season={meta['season']}")

# 5. 測試 save_snapshot() 與 get_snapshot()
print("\n[5] 測試快照存取 (save_snapshot / get_snapshot)...")
# 呼叫 save_snapshot
save_snapshot()
current_tick = get_tick()
snapshot_path = Path("data/snapshots") / f"snapshot_{current_tick}.json"
assert snapshot_path.exists(), f"快照檔案 {snapshot_path} 應存在"

# 測試 get_snapshot
snap_state = get_snapshot(current_tick)
assert isinstance(snap_state, WorldState), "get_snapshot 應返回 WorldState 物件"
assert snap_state.tick == current_tick, f"快照 tick 應為 {current_tick}，但得到 {snap_state.tick}"

# 測試讀取不存在的快照
invalid_snap = get_snapshot(99999)
assert invalid_snap is None, "讀取不存在的快照應返回 None"
print("[OK] 快照檔案建立與讀取成功")

# 6. 測試自動快照儲存 (每 10 tick 與季節結束)
print("\n[6] 測試自動快照儲存條件...")
# 6.1 測試每 10 tick 自動儲存：設定為 9，前進到 10
db.upsert_world_meta(9, 1, "spring")
snap_10_path = Path("data/snapshots") / "snapshot_10.json"
if snap_10_path.exists():
    os.remove(snap_10_path)

advance_tick()
assert snap_10_path.exists(), "推進到 10 tick 應自動產生 snapshot_10.json"

# 6.2 測試季節結束自動儲存：設定為 28，前進到 29 (spring 最後一天)
db.upsert_world_meta(28, 1, "spring")
snap_29_path = Path("data/snapshots") / "snapshot_29.json"
if snap_29_path.exists():
    os.remove(snap_29_path)

advance_tick()
assert snap_29_path.exists(), "推進到 29 tick (季節末) 應自動產生 snapshot_29.json"
print("[OK] 自動快照觸發成功")

# 7. 測試 get_history(start, end)
print("\n[7] 測試 get_history()...")
# 建立一個測試事件
test_event = WorldEvent(tick=15, event_type="discovery", description="在森林發現神秘遺跡")
from modules.m1_world_state.main import add_event
add_event(test_event)

history = get_history(10, 20)
assert len(history) >= 1, "應取得 tick 15 的事件"
ticks_in_history = [e.tick for e in history]
for t in ticks_in_history:
    assert 10 <= t <= 20, f"事件 tick {t} 超出查詢範圍 [10, 20]"
print(f"[OK] get_history() 查詢結果正常: 包含 tick {ticks_in_history}")

# 8. 測試 get_timeline()
print("\n[8] 測試 get_timeline()...")
timeline = get_timeline()
assert isinstance(timeline, list), "timeline 應為 list"
for item in timeline:
    assert isinstance(item, dict), "timeline 元素應為 dict"
    assert "tick" in item, "應包含 tick"
    assert "event_type" in item, "應包含 event_type"
    assert "description" in item, "應包含 description"
    assert isinstance(item["tick"], int), "tick 應為 int"
    assert isinstance(item["event_type"], str), "event_type 應為 str"
    assert isinstance(item["description"], str), "description 應為 str"
print("[OK] get_timeline() 格式驗證通過")

print("\n[SUCCESS] M6 所有測試通過！")
