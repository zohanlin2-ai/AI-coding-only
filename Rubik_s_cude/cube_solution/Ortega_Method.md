# Ortega Method 2×2 快速解法指南

Ortega Method 是一種專為 2×2 魔術方塊設計的速解法，主要分為三個步驟。本模擬器的 Phase 1 與 Phase 2 也參考了部分相關算法。

---

## 1. Step 1: First Face (底面)
- **目標**：完成一個面的顏色 (例如白色)，**不需理會**側面是否對齊。
- **重點**：一般建議在 4 步以內完成。

## 2. Step 2: OLL (頂面翻色)
根據頂面剩下的形狀選擇對應公式（與 3×3 的 OLL 相同）：

| 案例 | 算法 (Algorithm) |
| :--- | :--- |
| **Sune** | `R U R' U R U2 R'` |
| **Anti-Sune** | `R U2 R' U' R U' R'` |
| **H** | `R2 U2 R U2 R2` |
| **Pi** | `R U2 R2 U' R2 U' R2 U2 R` |
| **Headlights** | `F (R U R' U') F'` |
| **T** | `(R U R' U') (R' F R F')` |
| **U** | `F (R U R' U')2 F'` |

## 3. Step 3: PBL (兩層位置對齊)
這是 Ortega 的核心，觀察上下兩層側面「成對顏色 (Bar)」的數量與位置：

| 狀態 | 位置擺放 | 公式 |
| :--- | :--- | :--- |
| **兩層都有 Bar** | 上下 Bar 皆放於**前方** | `R2 U' B2 U2 R2 U' R2` |
| **僅底層有 Bar** | Bar 放於**底層前方** | `R U' R F2 R' U R'` |
| **僅頂層有 Bar** | Bar 放於**頂層前方** | `R' U L' U2 R U' L` |
| **兩層都無 Bar** | 任意擺放 | `R2 F2 R2` |
| **兩層都已對齊** | 頂層 Bar 放於**左方** | (執行 T-Perm 或 J-Perm) |

---

## 學習資源建議

若想更深入練習手解技巧，推薦參考以下資源：
- [J Perm - 2x2 Ortega Method Tutorial](https://youtu.be/mREmNnefPew) (YouTube)
- [Ruwix - 2x2 Rubik's Cube Solver](https://ruwix.com/online-rubiks-cube-solver-program/2x2x2-pocket-cube-solver/)

> [!TIP]
> 本模擬器的自動解法 Phase 0 等同於完成了「完美的第一層」，因此在 Phase 2 階段通常只會遇到 PLL 的情況。