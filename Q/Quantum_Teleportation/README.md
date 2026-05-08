# Quantum Teleportation

This project demonstrates the **Quantum Teleportation** protocol using Qiskit. It allows the transfer of a quantum state from one qubit (Alice's) to another (Bob's) using a shared entangled pair and classical communication.

## 📌 Project Overview
The protocol consists of several key steps:
1. **Entanglement**: Creating a Bell pair shared between Alice and Bob.
2. **Alice's Operation**: Alice performs a CNOT and a Hadamard gate on her qubits.
3. **Measurement**: Alice measures her two qubits and sends the results (2 classical bits) to Bob.
4. **Bob's Correction**: Bob applies specific quantum gates (X or Z) based on Alice's results to recreate the original state.

## 📂 File Structure
- `quantum_teleportation.py`: The implementation script using Qiskit 1.0+ dynamic circuits.
- `quantum_teleportation_project.md`: Detailed explanation of the concepts and mathematical background.
- `CHANGELOG.md`: History of changes for this project.

## 🚀 Quick Start
### Prerequisites
Install Qiskit and the Aer simulator:
```bash
pip install qiskit qiskit-aer
```

### Running the Simulation
The script includes an automated verification step. It teleports a state and then applies the inverse transformation on Bob's end to confirm the state was correctly received.
```bash
python quantum_teleportation.py
```

## 🛠 Advanced Features
- **Dynamic Circuits**: Uses `if_test` for conditional logic, representing the latest standard in quantum programming.
- **Verification Logic**: Automatically calculates the success rate of the teleportation.

## 📄 License
Educational use.
