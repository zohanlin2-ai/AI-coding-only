# Quantum Random Number Generator (QRNG)

This project implements a **Quantum Random Number Generator** using IBM's Qiskit framework. It leverages the principle of quantum superposition to generate truly random numbers.

## 📌 Project Overview
The goal is to simulate a quantum circuit that puts a qubit into a superposition state and then measures it. The measurement outcome is inherently random (50% chance of 0 or 1), providing a source of entropy.

## ⚛️ Quantum Circuit
The core logic consists of:
1. Initializing a qubit in state $|0\rangle$.
2. Applying a **Hadamard Gate (H)** to create a superposition: $\frac{1}{\sqrt{2}}(|0\rangle + |1\rangle)$.
3. **Measuring** the qubit to collapse the state into 0 or 1.

![Quantum Circuit Diagram](qrng_circuit.png)

## 📂 File Structure
- `qrng.py`: Main Python script containing the QRNG logic.
- `qrng_project.md`: Detailed technical documentation.
- `qrng_circuit.png`: Visualization of the quantum circuit.
- `CHANGELOG.md`: Tracked changes for the project.

## 🚀 Quick Start
### Prerequisites
Ensure you have Python installed and install the required dependencies:
```bash
pip install qiskit qiskit-aer
```

### Running the Generator
Execute the script to generate random bits and numbers:
```bash
python qrng.py
```

## 🛠 Features
- Single-bit generation.
- Multi-bit integer generation (e.g., 8-bit, 16-bit).
- Uses `AerSimulator` for high-performance local simulation.

## 📄 License
This project is for educational purposes.
