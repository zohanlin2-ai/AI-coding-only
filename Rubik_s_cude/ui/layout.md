# Rubik's Cube UI 設計規格 (Ursina Engine)

本專案使用 [Ursina Engine](https://www.ursinaengine.org/) 實作 3D 圖形介面，具備流暢的動畫表現與遊戲化的操作體驗。

## 1. 介面佈局 (Screen Layout)

- **3D 景觀區**：主畫面置中，背景為深灰漸層。顯示由 8 個 `CubeEntity` 組成的魔術方塊。
- **操作面板 (左下角)**：
    - `Random` 按鈕：觸發隨機序列動畫。
    - `First Layer` 按鈕：執行 Phase 0 解法動畫。
    - `Second Layer` 按鈕：執行 Phase 1+2 完整還原。
- **視角控制 (右下角)**：
    - 方向鍵組合按鈕 (`←`, `→`, `↑`, `↓`)，用於 90 度步進式的地平線/垂直旋轉相機。
- **狀態顯示 (頂部與側邊)**：
    - 即時字體顯示目前動作佇列 (`Action Queue`)。
    - 顯示目前偵測到的最佳目標顏色與階層解法進度。

## 2. 互動設計 (Interaction)

### 動畫流程控制
- **佇列管理**：UI 按鈕不直接操作 `CubeState`，而是將動作推入 `action_queue`。
- **互鎖機制**：當動畫正在播放時 (`is_animating = True`)，大部分 UI 按鈕會暫時進入「等待」狀態，防止邏輯狀態因連續點擊而發生競爭衝突。

### 相機控制
- **鍵盤控制**：支援使用標準方向鍵進行視角轉動。
- **自動對焦**：視角中心點固定於 `(0,0,0)`，確保魔術方塊始終位於畫面中心。

## 3. 分色設計 (Color Coding)

魔術方塊使用高對比度的現代色票：
- **U (White)**: #FFFFFF
- **D (Yellow)**: #FFFF00
- **R (Red)**: #FF0000
- **L (Orange)**: #FFA500
- **F (Green)**: #00FF00
- **B (Blue)**: #0000FF

## 4. UI 元件清單

| 元件類型 | 功能描述 | 實作類別 |
| :--- | :--- | :--- |
| **Logic Cube** | 包含 8 個子方塊的集合實體 | `Entity` |
| **Solve Button** | 觸發解題演算法並播放序列 | `Button` |
| **Status Label** | 顯示目標顏色與 BFS 狀態 | `Text` |
| **Orbit Center** | 用於 `wrtReparentTo` 的旋轉軸心 | `Entity` |