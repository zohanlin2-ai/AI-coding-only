# 2×2 魔術方塊模擬器解法說明

本文件說明此模擬器採用的自動解題策略：**Color-Neutral BFS 三階段分層法**。

---

## 快速導覽

- [1. 核心概念：Color-Neutral](#核心概念color-neutral顏色中立)
- [2. 狀態表示：24-Sticker 索引](#狀態表示24-sticker-索引)
- [3. Phase 0：First Layer (第一層)](#phase-0first-layer第一層)
- [4. Phase 1：OLL (底面定向)](#phase-1ollorient-last-layer底面定向)
- [5. Phase 2：PLL (底面排列)](#phase-2pllpermute-last-layer底面排列)
- [6. BFS 搜尋引擎與效能指標](#bfs-搜尋引擎)
- [7. 與 Ortega Method 的比較](#與-ortega-method-的關係)

---

## 概覽

| 階段 | 名稱 | 目標 | 演算法 |
|------|------|------|--------|
| Phase 0 | **First Layer** | 將目標顏色的 4 個角塊放置於頂面，並確保每個角塊方向正確 (3 個 sticker 全對) | Color-Neutral BFS + 角塊插入宏 |
| Phase 1 | **OLL** | 讓底面 4 個 sticker 全都朝下，顯示底面顏色 | BFS + OLL 算法宏 |
| Phase 2 | **PLL** | 使底面 4 個角塊排列至正確位置，完全還原 | BFS + PLL 算法宏 |

---

## 核心概念：Color-Neutral（顏色中立）

一般手解法通常固定某個顏色（如白色）作為第一層。本模擬器採用 **Color-Neutral** 策略：

1. 掃描打亂後的方塊 6 個面
2. 找出「在同一個面上出現最多次」的顏色 → 作為目標顏色
3. 從 24 個等效已解狀態中，找到與當前狀態 sticker 匹配數最多的那個 → 作為最終解目標

這樣做的優勢：從最接近已解的方向切入，可大幅減少 BFS 搜尋步數。

---

## 狀態表示：24-Sticker 索引

2×2 方塊 8 個角塊 × 3 個 sticker = 24 個 sticker，以 index 0–23 編號：

```
面   索引     視覺顏色（初始）
U    0–3      白色 (White)
R    4–7      紅色 (Red)
F    8–11     綠色 (Green)
D    12–15    黃色 (Yellow)
L    16–19    橘色 (Orange)
B    20–23    藍色 (Blue)
```

每個角塊在 3 個面各有一個 sticker，關鍵索引如下：

| 角塊 | U sticker | 側面 1 | 側面 2 |
|------|-----------|--------|--------|
| ULB  | s[0]  | s[16] (L面) | s[21] (B面) |
| URB  | s[1]  | s[5]  (R面) | s[20] (B面) |
| ULF  | s[2]  | s[17] (L面) | s[8]  (F面) |
| URF  | s[3]  | s[4]  (R面) | s[9]  (F面) |
| DFL  | s[12] | s[19] (L面) | s[10] (F面) |
| DFR  | s[13] | s[6]  (R面) | s[11] (F面) |
| DBL  | s[14] | s[18] (L面) | s[23] (B面) |
| DBR  | s[15] | s[7]  (R面) | s[22] (B面) |

---

## Phase 0：First Layer（第一層）

### 目標

將含有目標顏色的 4 個角塊，依序放置到頂面（U 面）的 ULB、URB、URF、ULF 位置，且每個角塊的 **全部 3 個 sticker** 均正確對應目標方向。

### 驗證條件

```python
face_ulb(s): s[0]==t[0]  and s[16]==t[16] and s[21]==t[21]
face_urb(s): face_ulb(s) and s[1]==t[1]   and s[5]==t[5]   and s[20]==t[20]
face_urf(s): face_urb(s) and s[3]==t[3]   and s[4]==t[4]   and s[9]==t[9]
face_ulf(s): face_urf(s) and s[2]==t[2]   and s[17]==t[17] and s[8]==t[8]
```

其中 `t = current_target_state`（從 24 個已解狀態中選出的最佳目標）。

### 宏操作（Macro）

BFS 不搜尋單步轉動，而是以**預定義的移動序列（宏）**為單位，大幅縮小搜尋樹：

**Standalone 宏**（D 層旋轉，用於調整底層角度）：
- `D`、`D'`、`D D`

**角塊插入宏**（從底層 D 插入到頂層 U）：

每個插入宏由一組 3–5 步的移動組成，形式如下：

| 類型 | 範例序列 | 用途 |
|------|---------|------|
| R 面插入 | `R' D' R` | 將 DBR 角塊插入 URF（U sticker 朝上） |
| R 面插入 (扭轉) | `R' D R` | 將 DBR 角塊插入 URF（U sticker 朝側） |
| F 面插入 | `F D F'` | 從 DFL 側插入 ULF |
| L 面插入 | `L' D L` | 從 DBL 插入 ULB |
| B 面插入 | `B D B'` | 從 DBL/DBR 插入 URB/ULB |

各步驟限制可用宏（非破壞性過濾）：
- **Step 1 (ULB)**：全部宏可用
- **Step 2 (URB)**：排除可能移動 ULB 的宏（L'、B 系列）
- **Step 3 (URF)**：排除可能移動 ULB、URB 的宏
- **Step 4 (ULF)**：排除可能移動 ULB、URB、URF 的宏

### 求解流程

```
for each corner (ULB → URB → URF → ULF):
    for attempt in range(4):       ← 最多 4 次 D 旋轉重試
        if goal_function(state): break  ← 已到位
        path = BFS(cube, goal, allowed_macros)
        if path found:
            apply path; break
        else:
            apply D                ← D 層旋轉解鎖，再試
```

---

## Phase 1：OLL（Orient Last Layer，底面定向）

### 目標

讓底面（D 面）的 4 個 sticker 全部朝下，顯示 D 顏色（索引 12–15 均等於目標底色）。

```python
goal: s[12] == s[13] == s[14] == s[15] == target_d_color
```

### OLL 算法對照

標準 OLL 算法設計用於頂面。本模擬器透過 `map_d()` 將其映射到底面。

**`map_d` 轉換規則**

```
U ↔ D    （上下互換）
R ↔ L    （左右互換）
F → F    （前面不變）
B → B    （後面不變）
```

等效於將方塊上下翻轉 180° 後執行標準算法，確保算法作用在 D 層角塊，且完成後 U 層保持原狀。

**OLL 案例與算法**

| 案例 | 名稱 | 原始 U 層算法 | 對應 D 層算法（map_d） |
|------|------|--------------|----------------------|
| 無角塊朝下 (Pi) | Pi | `R U2 R2 U' R2 U' R2 U2 R` | `L' D2 L2 D L2 D L2 D2 L'` |
| 對角 2 個朝下 | H | `R2 U2 R U2 R2` | `L2 D2 L' D2 L2` |
| 相鄰 1 個朝下 | Headlights | `F R U R' U' F'` | `F' L' D' L D F` |
| 1 個朝下 (順) | Sune | `R U R' U R U2 R'` | `L' D' L D' L' D2 L` |
| 1 個朝下 (逆) | Anti-Sune | `R U2 R' U' R U' R'` | `L' D2 L D L' D L` |
| T 形 | T | `R U R' U' R' F R F'` | `L' D' L D L F' L' F` |
| U 形 | U | `F R U R' U' R U R' U' F'` | `F' L' D' L D L' D' L D F` |

> 若底面已全部朝下（skip），BFS 立即回傳空路徑，此步驟跳過。

---

## Phase 2：PLL（Permute Last Layer，底面排列）

### 目標

所有 24 個 sticker 與目標狀態完全一致（方塊完全還原）：

```python
goal: tuple(state) == current_target_state
```

### PLL 算法

| 名稱 | 原始 U 層算法 | 對應 D 層（map_d） |
|------|--------------|-------------------|
| T-Perm | `R U R' U' R' F R2 U' R' U' R U R' F'` | `L' D' L D L F' L2 D L D L' D' L F` |
| Y-Perm | `F R U' R' U' R U R' F' R U R' U' R' F R F'` | `F' L' D L D L' D' L F L' D' L D L F' L' F` |

搭配 D 旋轉（`D`、`D'`、`D D`）共 5 種宏，BFS 可覆蓋所有 4 個底層角塊的排列組合。

---

## BFS 搜尋引擎

### 設計原則

- **搜尋單位**：宏（Macro），非單步移動。每個宏代表一組 3–17 步的序列
- **優勢**：比單步 BFS 少搜尋幾個數量級的中間狀態
- **安全上限**：每次 BFS 最多探索 **150,000 個不重複狀態**，超過則回傳空路徑（觸發 D 旋轉重試）

### 效能實測（200 組 8 步隨機打亂）

| 階段 | 平均耗時 | 最大耗時 |
|------|----------|----------|
| First Layer（4 個角塊） | ~1.5 s | ~6 s |
| OLL | < 1 ms | < 1 ms |
| PLL | < 1 ms | < 1 ms |

> First Layer BFS 較慢，因為需要 4 次獨立 BFS，每次使用 25+ 宏、最多 150k 狀態，且第一次呼叫需生成 24 個已解狀態（之後快取）。

---

## 完整解題流程圖

```
打亂後狀態
    │
    ▼
compute_target_orientation()
    ├─ 掃描 6 個面，找最多的顏色 → target_color
    └─ 從 24 個已解狀態中找匹配最多的 → current_target_state
    │
    ▼
Phase 0: solve_first_layer()
    ├─ Step 1: BFS → 放置 ULB 角塊（全 3 sticker）
    ├─ Step 2: BFS → 放置 URB 角塊（全 3 sticker，不破壞 ULB）
    ├─ Step 3: BFS → 放置 URF 角塊（全 3 sticker，不破壞 ULB+URB）
    └─ Step 4: BFS → 放置 ULF 角塊（全 3 sticker，不破壞其餘三個）
    │
    ▼
Phase 1: solve_bottom_oll()
    └─ BFS 使用 OLL 宏 → 底面 s[12..15] 全等於 D 顏色
    │
    ▼
Phase 2: solve_bottom_pll()
    └─ BFS 使用 PLL 宏 → 全部 24 sticker == current_target_state
    │
    ▼
Fully Solved ✓
```

---

## 與 Ortega Method 的關係

本模擬器的解法在結構上接近 **Ortega Method**（一種 2×2 競速解法）：

| Ortega Method | 本模擬器解法 |
|---------------|--------------|
| Step 1: Face（完成一個面，不理側面） | Phase 0（前半）：BFS 找 U sticker = 目標色 |
| Step 2: OLL（頂面翻色） | Phase 1：OLL（底面定向） |
| Step 3: PBL（兩層同時排列） | Phase 2：PLL（底面排列） |

**主要差異**：
- Ortega 的 Step 1 不要求側面對齊，而本模擬器的 Phase 0 要求 **全 3 sticker 正確**（位置 + 方向），等同完整的第一層
- Ortega 的 PBL 可同時處理上下兩層；本模擬器採 OLL + PLL 分開處理
- 本模擬器加入 **Color-Neutral** 選色策略，Ortega 手解法通常固定顏色

詳見 [Ortega_Method.md](Ortega_Method.md) 了解標準手解參考。

---

## 符號說明

| 符號 | 意義 |
|------|------|
| U, D, R, L, F, B | 上/下/右/左/前/後 面順時針旋轉 90° |
| U', D', R', L', F', B' | 對應面逆時針旋轉 90°（prime 逆轉） |
| U2, R2 ... | 對應面旋轉 180°（= 執行兩次） |
| map_d(algo) | 將 U 層算法透過 U↔D、R↔L 替換，轉為 D 層算法 |
| BFS | Breadth-First Search，廣度優先搜尋 |
| Macro | 宏操作：一組預定義的移動序列，作為 BFS 的單一展開步驟 |
| current_target_state | 24 個 sticker 的目標已解狀態（由 compute_target_orientation 選定） |
