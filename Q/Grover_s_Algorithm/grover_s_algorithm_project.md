# Grover's Algorithm（量子搜尋演算法）

## 概念簡介

Grover's Algorithm 是一種量子演算法，用來在未排序資料庫中搜尋目標項目。

* 傳統搜尋：O(N)
* Grover：O(√N)

---

## 核心想法

1. 建立均勻疊加（superposition）
2. 標記目標（Oracle）
3. 放大目標機率（Amplitude Amplification）
4. 重複數次 → 測量

---

## Python 實作（Qiskit）

### 安裝

pip install qiskit

---

### 範例：搜尋 |11⟩

```python
from qiskit import QuantumCircuit
from qiskit_aer import Aer
from qiskit.visualization import plot_histogram

# 建立 2 個量子位元與 2 個古典位元
qc = QuantumCircuit(2, 2)

# 1. 建立疊加態
qc.h([0, 1])

# 2. Oracle (標記 |11⟩)
qc.cz(0, 1)

# 3. Diffusion (放大振幅)
qc.h([0, 1])
qc.x([0, 1])
qc.h(1)
qc.cx(0, 1)
qc.h(1)
qc.x([0, 1])
qc.h([0, 1])

# 測量
qc.measure([0, 1], [0, 1])

# 執行模擬
simulator = Aer.get_backend('qasm_simulator')
job = simulator.run(qc, shots=1024)
result = job.result()

counts = result.get_counts()
print(f"測量結果: {counts}")
```

---

### 範例：3 位元搜尋 |111⟩

在 3 位元 ($N=8$) 的情況下，最優迭代次數約為 2 次。

```python
from qiskit import QuantumCircuit
from qiskit_aer import Aer
import matplotlib.pyplot as plt

def grover_3qubits():
    qc = QuantumCircuit(3, 3)
    
    # 1. 初始化
    qc.h([0, 1, 2])
    
    # 進行 2 次迭代
    for _ in range(2):
        # 2. Oracle (標記 |111>)
        # 使用 Multi-Controlled Z
        qc.h(2)
        qc.ccx(0, 1, 2)
        qc.h(2)
        
        # 3. Diffusion
        qc.h([0, 1, 2])
        qc.x([0, 1, 2])
        qc.h(2)
        qc.ccx(0, 1, 2)
        qc.h(2)
        qc.x([0, 1, 2])
        qc.h([0, 1, 2])
    
    qc.measure([0, 1, 2], [0, 1, 2])
    return qc
```


---

## 預期結果

{'11': 約 1000}

---

## 小結

Grover 的核心是利用量子干涉放大正確答案的機率。
