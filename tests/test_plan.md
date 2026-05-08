# Rubik's Cube 測試計畫

本文件定義針對 2x2x2 魔術方塊模擬器的自動化測試與驗證流程。

## 1. 自動化測試腳本 (Python)

專案目前包含以下核心測試腳本，用於確保演算法的正確性與效能：

| 腳本名稱 | 測試對象 | 驗證內容 |
| :--- | :--- | :--- |
| `test_firstlayer.py` | 第一層解法 (Phase 0) | 進行 200 組隨機 8 步打亂，驗證頂面 4 個角塊的 **12 個 sticker** 是否完美契合目標狀態。 |
| `test_fullsolve.py` | 完整解法 (Phase 0-2) | 進行 200 組打亂，依序執行 First Layer → OLL → PLL，最後驗證 `is_solved()` 是否為 True。 |
| `test_timing.py` | 效能測試 | 測量 BFS 搜尋 OLL 與 PLL 的平均耗時（目前基準 < 1ms）。 |
| `test_panda3d_anim.py` | 動畫物理行為 | 在 Panda3D 空間中驗證 `wrtReparentTo` 置換邏輯是否與視覺旋轉一致。 |

## 2. 核心邏輯驗證方向

### 單元測試 (Unit Tests)
- **方塊置換正確性 (`cube.py`)**: 驗證 U/D/R/L/F/B 與其逆向轉動後的陣列 state 正確對應。
- **BFS 安全上限 (`solver.py`)**: 確保 `MAX_BFS_STATES` 能正常攔截無效路徑，防止 CPU 無限循環。

### 整合測試 (Integration Tests)
- **Color-Neutral 偵測**: 給定不同頂色的打亂狀態，驗證 `compute_target_orientation` 能否挑選出最省步數的目標面。
- **動畫與邏輯同步**: 驗證按鈕觸發的 `action_queue` 在動畫結束後，邏輯狀態與視覺完全對齊。

## 3. 執行測試

本專案建議使用 `pytest` 框架執行所有測試：

```bash
# 安裝 pytest
pip install pytest

# 執行所有測試
pytest

# 執行特定類型的測試 (例如效能測試)
python test_timing.py
```

## 4. 人工視覺檢核
- 啟動 `main.py` 後觀察：
    - 按下 `Random` 是否確實產生 8 步隨機動畫。
    - 點擊 `First Layer` 後，觀察角塊插入過程中是否發生「撕裂」或顏色異常。
    - 拖行視野確認相機平穩。