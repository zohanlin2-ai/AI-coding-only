# 2×2 魔術方塊模擬器

## 專案簡介

本專案以 Python + Ursina 引擎實作一個可互動的 **2×2×2 魔術方塊（Pocket Cube）模擬器**，具備：

- 3D 視覺化旋轉動畫（視覺與邏輯完全同步）
- 隨機打亂功能
- **Color-Neutral 第一層自動解法**（BFS 演算法，支援任意面為目標）
- 即時狀態欄位顯示

> [!NOTE]
> **目前狀態**：第一層 (First Layer) 與第二層 (OLL + PLL) 解法均已完整實作，通過 200/200 隨機測試，視覺動畫與邏輯狀態完全同步。

---

## 安裝與執行

### 環境需求

- Python 3.8+
- [Ursina Engine](https://www.ursinaengine.org/)（底層使用 Panda3D）

```bash
pip install ursina
```

### 執行

```bash
python src/main.py
```

---

## 測試與驗證

本專案經過嚴格的自動化驗證，確保解法 100% 正確：

```bash
# 安裝測試套件
pip install pytest

# 執行所有邏輯測試
pytest

# 執行效能分析
python test_timing.py
```

詳細測試計畫請參閱：[tests/test_plan.md](tests/test_plan.md)

---

## 專案結構

```text
Rubik_s_cude/
├── README.md                    # 本文件
├── CHANGELOG.md                 # 版本更新紀錄
├── cube_solution/
│   ├── BFS_Solve_Method.md      # 完整解法說明（本模擬器使用的演算法）
│   └── Ortega_Method.md         # Ortega 手解參考
├── scratch.py                   # 開發草稿（置換陣列推導用）
├── verify_rotmap.py             # 動畫旋轉角度驗證工具（Panda3D world-space）
├── test_panda3d_anim.py         # 動畫物理行為驗證（wrtReparentTo 模擬）
├── test_firstlayer.py           # 第一層解法邏輯測試（200 組隨機打亂）
├── test_fullsolve.py            # 完整三階段解法測試（200 組）
├── test_timing.py               # OLL / PLL 效能計時測試
└── src/
    ├── main.py                  # Ursina 主程式、動畫引擎、UI
    ├── cube.py                  # 2×2 方塊邏輯狀態與置換陣列
    └── solver.py                # BFS 解法引擎、Color-Neutral 方向偵測
```

---

## 解法文件

| 文件 | 說明 |
|------|------|
| [BFS_Solve_Method.md](cube_solution/BFS_Solve_Method.md) | **本模擬器使用的解法**：Color-Neutral BFS 三階段分層法，含所有算法、流程圖、效能數據 |
| [Ortega_Method.md](cube_solution/Ortega_Method.md) | 標準 Ortega 手解速解法參考（OLL + PBL） |

---

## 操作說明

| 按鈕 | 功能 |
|------|------|
| **Random** | 隨機打亂（8 步隨機轉動） |
| **First Layer** | 自動解第一層（Color-Neutral BFS，選最佳面） |
| **Second Layer** | 自動解第二層（OLL + PLL，完全還原方塊） |
| **← → ↑ ↓** | 旋轉鏡頭視角（各 90° 步進） |

> **建議操作順序**：`Random → First Layer → Second Layer`
> 詳細解法說明見 [cube_solution/BFS_Solve_Method.md](cube_solution/BFS_Solve_Method.md)

---

## 核心架構

### 1. 邏輯狀態（`src/cube.py`）

#### 24-Sticker 表示法

2×2 方塊有 8 個角塊，每個角塊 3 個貼紙，共 **24 個貼紙**。
以 index 0–23 表示，按面分組：

| Index | 面 | 視覺顏色 |
|-------|----|----------|
| 0–3   | U（上） | 白色 |
| 4–7   | R（右） | 紅色 |
| 8–11  | F（前） | 綠色 |
| 12–15 | D（下） | 黃色 |
| 16–19 | L（左） | 橘色 |
| 20–23 | B（後） | 藍色 |

初始已解狀態：`(0,0,0,0, 1,1,1,1, 2,2,2,2, 3,3,3,3, 4,4,4,4, 5,5,5,5)`

#### 角塊 Sticker 對應

每個角塊在 3 個面各有一個 sticker，索引如下：

| 角塊 | U sticker | 側面 1 | 側面 2 |
|------|-----------|--------|--------|
| ULB  | s[0]      | s[16] (L面) | s[21] (B面) |
| URB  | s[1]      | s[5]  (R面) | s[20] (B面) |
| ULF  | s[2]      | s[17] (L面) | s[8]  (F面) |
| URF  | s[3]      | s[4]  (R面) | s[9]  (F面) |
| DFL  | s[12]     | s[19] (L面) | s[10] (F面) |
| DFR  | s[13]     | s[6]  (R面) | s[11] (F面) |
| DBL  | s[14]     | s[18] (L面) | s[23] (B面) |
| DBR  | s[15]     | s[7]  (R面) | s[22] (B面) |

#### 置換陣列（PERM_MOVES）

每個轉動由一個長度 24 的置換陣列定義，代表「新 state[i] = 舊 state[perm[i]]」：

```python
PERM_MOVES = {
    'U': [2,0,3,1, 20,21,6,7, 4,5,10,11, 12,13,14,15, 8,9,18,19, 16,17,22,23],
    'D': [0,1,2,3, 4,5,10,11, 8,9,18,19, 14,12,15,13, 16,17,22,23, 20,21,6,7],
    'R': [0,9,2,11, 6,4,7,5, 8,13,10,15, 12,22,14,20, 16,17,18,19, 3,21,1,23],
    'L': [23,1,21,3, 4,5,6,7, 0,9,2,11, 8,13,10,15, 18,16,19,17, 20,14,22,12],
    'F': [0,1,19,17, 2,5,3,7, 10,8,11,9, 6,4,14,15, 16,12,18,13, 20,21,22,23],
    'B': [5,7,2,3, 4,15,6,14, 8,9,10,11, 12,13,16,18, 1,17,0,19, 22,20,23,21],
}
```

逆向（prime）轉動由程式自動計算反向置換。

---

### 2. 動畫引擎（`src/main.py`）

#### 旋轉映射表（`rot_map`）

將邏輯轉動名稱對應到 Ursina 的動畫軸與角度。

> [!IMPORTANT]
> **技術細節**：Ursina 底層為 Panda3D（Z-up 座標系），其 `entity.rotation` 使用 `rotation_directions = (-1, -1, 1)` 做轉換，導致 Y 軸與 X 軸方向與標準數學相反。本專案已透過物理模擬校準完成。

最終驗證結果（透過 Panda3D `wrtReparentTo` + `setHpr` 實際測試）：

| 轉動 | 軸 | 面選取 | 角度 | Ursina 實際效果 |
|------|-----|--------|------|----------------|
| U    | y   | y > 0  | +90  | roty_cw = (z,y,−x)  |
| D    | y   | y < 0  | −90  | roty_ccw = (−z,y,x) |
| R    | x   | x > 0  | +90  | rotx_cw = (x,−z,y)  |
| L    | x   | x < 0  | −90  | rotx_ccw = (x,z,−y) |
| F    | z   | z < 0  | +90  | rotz_ccw = (y,−x,z) |
| B    | z   | z > 0  | −90  | rotz_cw = (−y,x,z)  |

#### 動畫流程

```
perform_move_animation(move):
  1. 選取位於目標面的所有 piece（依 world_position 軸值）
  2. piece.wrtReparentTo(pivot)   ← 掛到旋轉軸心
  3. pivot.animate("rotation_?", deg, duration=speed)
  4. invoke(end_anim, delay=speed+0.05)
     → piece.wrtReparentTo(scene)  ← 歸還場景
     → pivot.rotation = 0          ← 重置軸心
     → 觸發下一個 action_queue 動作
```

---

### 3. BFS 解法引擎（`src/solver.py`）

#### Color-Neutral 目標方向判斷

```
compute_target_orientation(current_state):
  1. 掃描所有 6 個面，找出在某個面上出現最多次的顏色 → best_color
  2. 從 24 個旋轉等效的已解狀態中，篩選出 best_color 在 U 面的候選（最多 4 個）
  3. 選擇與當前狀態 sticker 匹配數最多的候選 → current_target_state
     （最多匹配 = 最少需要移動 = BFS 效率最高）
```

#### 宏操作集合（Macros）

BFS 不搜尋單步轉動，而是以**宏操作（macro）**為單位，每個宏是一組預定義的移動序列。

**Standalone 宏**（D 層旋轉）：
- `[D]`, `[D']`, `[D, D]`

**角塊插入宏**（從 D 層插入到 U 層，每個角塊位置各有對應的宏）：

| 目標角塊 | 可用宏系列 |
|----------|-----------|
| ULB, URB, ULF, URF | `R'D'R`, `R'DR`, `FDF'`, `FD'F'` … |
| ULB, URB, ULF | + `L'DL`, `L'D'L`, `BDB'`, `BD'B'` … |
| ULB, URB | + `LDL'`, `LD'L'`, `B'DB`, `B'D'B` … |
| ULB | + `RDR'`, `RD'R'`, `F'DF`, `F'D'F` … |

**非破壞性過濾**：每一步只允許不會破壞已解角塊的宏，
透過逐步縮小可用宏集合（`macros_1` → `macros_2` → `macros_3` → `macros_4`）實現。

#### 第一層解法流程（`solve_first_layer`）

**目標**：將 4 個含目標顏色的角塊，依序放到 U 面的正確位置並以正確方向朝上。

```
solve_first_layer(cube):
  for each step (ULB, URB, URF, ULF):
    for attempt in range(4):          ← 最多 4 次 D 旋轉重試
      if goal_function(state): break  ← 已到位
      path = bfs_phase(cube, goal, macros)
      if path found:
        apply path
        break
      else:
        apply D                       ← 解鎖 D 層，換個角度再試
```

**各步驟目標函數**（完整 3-sticker 驗證）：

```python
face_ulb(s): s[0]==t[0]  and s[16]==t[16] and s[21]==t[21]
face_urb(s): face_ulb(s) and s[1] ==t[1]  and s[5] ==t[5]  and s[20]==t[20]
face_urf(s): face_urb(s) and s[3] ==t[3]  and s[4] ==t[4]  and s[9] ==t[9]
face_ulf(s): face_urf(s) and s[2] ==t[2]  and s[17]==t[17] and s[8] ==t[8]
```

> 每個 sticker 都需與 `current_target_state` 完全吻合，確保角塊不只在正確位置，方向也正確。

#### BFS 參數

| 參數 | 值 |
|------|-----|
| 最大搜尋狀態數（安全上限） | 150,000 |
| 搜尋單位 | Macro（非單步） |
| 每步可用宏數 | 3–25 個（依階段遞減） |

---

### 4. 第二層解法（`src/solver.py`）

第一層完成後，剩下 D 層（底面）的 4 個角塊需要：
1. **OLL（Orient Last Layer）**：讓底面 4 個 sticker 都朝下（顯示 D 顏色）
2. **PLL（Permute Last Layer）**：將角塊調整到正確位置，恢復完整已解狀態

#### OLL 宏（底面定向）

使用 `map_d(algo)` 把標準 U 層算法映射到 D 層（等效於上下翻轉後執行）：

| 算法 | 宏序列 |
|------|--------|
| (旋轉) | `D`, `D'` |
| Bottom Sune | `map_d(R U R' U R U U R')` |
| Bottom Anti-Sune | `map_d(R U U R' U' R U' R')` |
| H | `map_d(R R U U R U U R R)` |
| Pi | `map_d(R U U R R U' R R U' R R U U R)` |
| Headlights | `map_d(F R U R' U' F')` |
| T | `map_d(R U R' U' R' F R F')` |
| U | `map_d(F R U R' U' R U R' U' F')` |

**目標函數**：`s[12]==s[13]==s[14]==s[15]==D_color`（底面 4 格同色）

#### PLL 宏（底面排列）

| 算法 | 宏序列 |
|------|--------|
| (旋轉) | `D`, `D'`, `D D` |
| T-Perm | `map_d(R U R' U' R' F R R U' R' U' R U R' F')` |
| Y-Perm | `map_d(F R U' R' U' R U R' F' R U R' U' R' F R F')` |

**目標函數**：`tuple(state) == current_target_state`（完全已解）

**效能**：OLL 平均 < 0.2ms，PLL 平均 < 0.1ms（與解法路徑長度無關，BFS 搜尋空間極小）

#### `map_d` 映射原理

```
map_d(algo):
  U ↔ D（上下面互換）
  R ↔ L（左右面互換）
  F, B 保持不變
```

等效於將魔術方塊上下翻轉 180°，使 D 層演算法與標準 U 層演算法對稱。

---

### 5. 直接按 Second Layer 也能解的原因

**觀察**：打亂後不按 First Layer 直接按 Second Layer，有時能完整還原。

**原因**（設計上的副作用，非預期行為）：

1. 未呼叫 `compute_target_orientation`，`current_target_state` 維持預設值 = 標準已解狀態
2. 打亂步數固定 **8 步**，打亂後的狀態距離已解僅 8 步遠
3. OLL BFS 使用 7–14 步的長算法，並探索最多 **150,000 個狀態**
4. 從 8 步深的打亂狀態出發，這些算法的組合路徑**有機會意外找到已解狀態**（2×2 共 3,674,160 個狀態，150k 探索量佔 4%）
5. 一旦 OLL BFS 找到已解狀態：OLL 目標（D 面同色）自動成立，PLL 目標（完全吻合 `current_target_state`）也同時成立 → 直接完成

**正確使用流程**仍應為：`Random → First Layer → Second Layer`

> 直接使用 Second Layer 對 **深度打亂（15 步以上）不保證成功**。
> 一旦未找到解法，目前的 Random 功能只做 8 步打亂，故此副作用目前對用戶有效。

---

## 驗證工具

| 腳本 | 用途 |
|------|------|
| `test_panda3d_anim.py` | 在 Panda3D 場景中實際執行 `wrtReparentTo` + `setHpr`，驗證 6 個轉動的視覺效果與邏輯置換完全一致 |
| `verify_rotmap.py` | 使用 Ursina 實際旋轉矩陣（非標準數學矩陣）驗證 rot_map 角度 |
| `test_firstlayer.py` | 200 組 8 步隨機打亂，逐一執行 `solve_first_layer` 並驗證完整 12-sticker 結果 |
| `test_fullsolve.py` | 200 組 8 步隨機打亂，完整執行 First Layer + OLL + PLL 並驗證 `is_solved()` |
| `test_timing.py` | 測量 OLL / PLL 各自的 BFS 耗時（平均 < 1ms） |

**測試結果**：200/200 通過（含完整三階段解法）

---

## 已知行為 / 限制 / 開發中

- **Second Layer 副作用**：因打亂步數僅 8 步，直接按 Second Layer（跳過 First Layer）有時可完整還原。這是 BFS 廣度搜尋的副作用，詳見上方「直接按 Second Layer 也能解的原因」。正確流程為 `Random → First Layer → Second Layer`。
- **轉動動畫速度**：目前固定，未開放使用者調整。
- **打亂步數**：固定 8 步，可考慮未來開放設定。

---

## 版本紀錄

詳見 [CHANGELOG.md](CHANGELOG.md)