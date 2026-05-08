from qiskit import QuantumCircuit
from qiskit_aer import Aer
from qiskit.visualization import plot_histogram
import matplotlib.pyplot as plt

def run_simulation(qc, filename, title):
    print(f"正在執行模擬: {title}...")
    simulator = Aer.get_backend('qasm_simulator')
    job = simulator.run(qc, shots=1024)
    result = job.result()
    counts = result.get_counts()
    print(f"測量結果: {counts}")
    
    # 產出圖表
    plt.figure(figsize=(7, 5))
    plot_histogram(counts)
    plt.title(title)
    plt.savefig(filename)
    print(f"圖表已儲存至 {filename}")

def grover_2qubits():
    # 搜尋 |11>
    qc = QuantumCircuit(2, 2)
    qc.h([0, 1])
    
    # Oracle
    qc.cz(0, 1)
    
    # Diffusion
    qc.h([0, 1])
    qc.x([0, 1])
    qc.h(1)
    qc.cx(0, 1)
    qc.h(1)
    qc.x([0, 1])
    qc.h([0, 1])
    
    qc.measure([0, 1], [0, 1])
    return qc

def grover_3qubits():
    # 搜尋 |111>
    qc = QuantumCircuit(3, 3)
    qc.h([0, 1, 2])
    
    # 3 位元建議迭代 2 次
    for _ in range(2):
        # Oracle (|111>)
        # 用 CCX + H 實現 Multi-controlled Z
        qc.h(2)
        qc.ccx(0, 1, 2)
        qc.h(2)
        
        # Diffusion
        qc.h([0, 1, 2])
        qc.x([0, 1, 2])
        qc.h(2)
        qc.ccx(0, 1, 2)
        qc.h(2)
        qc.x([0, 1, 2])
        qc.h([0, 1, 2])
    
    qc.measure([0, 1, 2], [0, 1, 2])
    return qc

if __name__ == "__main__":
    # 執行 2 位元版本
    qc2 = grover_2qubits()
    run_simulation(qc2, "grover_2qubits_result.png", "Grover's Algorithm (2 Qubits, target: 11)")
    
    print("-" * 30)
    
    # 執行 3 位元版本
    qc3 = grover_3qubits()
    run_simulation(qc3, "grover_3qubits_result.png", "Grover's Algorithm (3 Qubits, target: 111)")
    
    print("\n所有實作已完成！")
