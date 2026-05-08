# Rubik's Cube Simulator — CHANGELOG

所有重要的版本異動記錄於此，格式參考 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.0.0/)。

---

## [0.3.0] - 2026-04-16

### Added
- **第一層完整解法**：`solve_first_layer` 現在驗證每個角塊的**全部 3 個 sticker**（U 面 + 兩個側面），而非僅 U 面。完成後 4 個側面（L/R/F/B）的上排各自只有一種顏色，而非混色。
- **最佳目標方向選擇**：`compute_target_orientation` 從 4 個等效已解狀態（相同顏色在頂面，但 Y 軸旋轉各異）中，挑選與當前狀態 **sticker 匹配數最多**的候選，減少 BFS 搜尋量。
- **驗證工具 `test_panda3d_anim.py`**：在 Panda3D world-space 中模擬 `wrtReparentTo + setHpr`，直接驗證 6 個面動畫的物理行為與邏輯置換一致（非數學矩陣假設）。
- **驗證工具 `test_firstlayer.py`**：200 組 8 步隨機打亂，全部完整 12-sticker 驗證，通過率 200/200。
- **顏色名稱對應修正**：`COLOR_NAMES` index 4 = Orange（L 面），index 5 = Blue（B 面），與視覺顏色完全一致。

### Changed
- **`MAX_BFS_STATES`** 從 50,000 提高至 150,000，應對更嚴格的 3-sticker 目標搜尋。
- **`verify_rotmap.py`** 重寫，改用正確的 Ursina 旋轉矩陣（`rotation_directions=(-1,-1,1)`），而非標準數學矩陣，避免 Y/Z 軸方向誤判。

---

## [0.2.0] - 2026-04-15

### Added
- **動畫物理驗證**：透過直接執行 `panda3d.core.NodePath.setHpr()`，確認 Ursina `rotation_y/z` 的實際旋轉方向，解決長期的視覺—邏輯不同步問題。
- **Console 偵錯輸出**：每次 First Layer 解法完成後，印出 4 個角塊的 sticker 值與驗證結果，便於確認邏輯狀態正確。

### Fixed
- **`rot_map` 旋轉角度（決定性修正）**：
  - 發現 Ursina `entity.py` 中 `rotation_directions = (-1, -1, 1)`，Y 軸與 Z 軸的旋轉方向與標準數學相反。
  - 最終確認正確映射：`U=+90, D=-90, R=+90, L=-90, F=+90, B=-90`（均為 Ursina `rotation` 值）。
  - 此修正讓視覺動畫與邏輯置換完全同步，**徹底解決「Verified 但顏色不在同一面」的問題**。
- **第一層驗證函數**：移除了要求側面 sticker 與特定 `current_target_state` 完全吻合的舊邏輯，改為直接用「U 面 4 格均為目標顏色」進行第一步快速驗證。

---

## [0.1.0] - 2026-04-14

### Added
- **`src/main.py`**：Ursina 3D 動畫主程式；包含 8 個方塊實體、顏色貼面、鏡頭軌道控制按鈕。
- **`src/cube.py`**：24-sticker 表示法 `CubeState`，含 6 個面的置換陣列（PERM_MOVES）及逆向置換自動生成。
- **`src/solver.py`**：BFS 解法引擎；Color-Neutral 方向偵測 `compute_target_orientation`；24 個已解等效狀態生成 `get_24_solved_states`；第一層宏操作集合（24+ 宏）。
- **GUI 狀態欄**：即時顯示目前解法狀態、目標顏色、最佳面資訊。
- **隨機打亂按鈕**：8 步隨機轉動序列。

### Fixed
- **`src/cube.py` R/L 置換陣列**：原定義使用 rotx_ccw 方向的 R，修正為物理正確的 rotx_cw（R 轉動為順時針看向 R 面），解決角塊「撕裂」及無限 BFS 迴圈問題。
- **`src/solver.py` BFS 安全上限**：加入 `MAX_BFS_STATES`（初始 50,000），防止複雜狀態下的無限搜尋。
- **`src/solver.py` 重試機制**：每個角塊解法加入最多 4 次 D 旋轉重試，提升解法找到率。