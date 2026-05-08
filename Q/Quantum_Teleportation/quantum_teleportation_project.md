# 量子隱形傳態 (Quantum Teleportation)

## 概念簡介
量子隱形傳態是一種利用**量子糾纏（entanglement）**與**經典通訊**，將一個量子態從一個位置傳送到另一個位置的方法。

重點：
- 不會傳送「物質」，只傳送「量子狀態」
- 需要三個量子位元（qubits）
- 需要經典通訊（2 bits）

---

## 基本流程

1. 建立糾纏對（Bell pair）
2. Alice 持有：
   - 要傳送的量子位（ψ）
   - 糾纏對的一半
3. Alice 對兩個 qubit 做操作並測量
4. 將測量結果（2 bits）傳給 Bob
5. Bob 根據結果做修正，還原 ψ

---

## 數學表示（簡化）

初始態：
|ψ⟩ = α|0⟩ + β|1⟩

Bell state：
(|00⟩ + |11⟩) / √2

最終 Bob 可重建：
α|0⟩ + β|1⟩


---

## Python 模擬實作（使用 Qiskit）

### 安裝
```bash
pip install qiskit