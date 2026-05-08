# Grover's Algorithm Simulation

This project provides a simulation of **Grover's Algorithm**, a quantum search algorithm that can find a specific item in an unsorted database with $O(\sqrt{N})$ complexity, compared to the classical $O(N)$.

## 📌 Project Overview
The implementation demonstrates how quantum interference can be used to amplify the probability amplitude of the target state. It includes:
- A **2-qubit** search implementation (target: $|11\rangle$).
- A **3-qubit** search implementation (target: $|111\rangle$).

## 📂 File Structure
- `grover_s_algorithm.py`: The core implementation using Qiskit.
- `grover_s_algorithm_project.md`: Detailed documentation and theoretical background.
- `grover_2qubits_result.png`: Simulation results for the 2-qubit case.
- `grover_3qubits_result.png`: Simulation results for the 3-qubit case.
- `CHANGELOG.md`: Log of updates and versions.

## 🚀 Quick Start
### Prerequisites
Install the necessary quantum computing libraries:
```bash
pip install qiskit qiskit-aer matplotlib
```

### Running the Simulation
Execute the script to see the probability amplification in action:
```bash
python grover_s_algorithm.py
```

## 📊 Results
The results are saved as histograms in the project directory. You will notice that the target states ($|11\rangle$ or $|111\rangle$) have significantly higher probabilities after the Grover iterations.

## 📄 License
Educational use.
