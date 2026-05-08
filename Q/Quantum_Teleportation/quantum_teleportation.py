import sys
import numpy as np
from qiskit import QuantumCircuit, transpile, ClassicalRegister
from qiskit_aer import AerSimulator
from qiskit.quantum_info import Statevector
from qiskit.visualization import plot_histogram

# Reconfigure stdout to use UTF-8 for Windows compatibility with Qiskit symbols
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

def create_quantum_teleportation_circuit():
    """
    Creates a quantum circuit for the teleportation protocol.
    
    Qubit 0: Alice's qubit containing the state to be teleported (psi)
    Qubit 1: Alice's half of the Bell pair
    Qubit 2: Bob's half of the Bell pair (will receive psi)
    """
    # Create a circuit with 3 qubits and 2 classical bits
    qc = QuantumCircuit(3, 2)

    # --- STEP 0: Initialize the state to be teleported (|ψ⟩) ---
    # We'll create a custom state: cos(theta/2)|0> + e^(i*phi)sin(theta/2)|1>
    # Let's use a state that is easy to verify, like applying H and S gates
    # to qubit 0. This results in 1/sqrt(2) (|0> + i|1>)
    qc.h(0)
    qc.s(0)
    qc.barrier()

    # --- STEP 1: Create entanglement (Bell pair) between qubit 1 and 2 ---
    # Alice (qubit 1) and Bob (qubit 2) share a Bell pair (|00> + |11>) / sqrt(2)
    qc.h(1)
    qc.cx(1, 2)
    qc.barrier()

    # --- STEP 2: Alice performs operations on her qubits (0 and 1) ---
    # Alice applies CNOT between the message qubit (0) and her entangled qubit (1)
    qc.cx(0, 1)
    # Alice applies a Hadamard gate to the message qubit (0)
    qc.h(0)
    qc.barrier()

    # --- STEP 3: Alice measures her qubits ---
    # Measure qubit 0 into classical bit 0, and qubit 1 into classical bit 1
    qc.measure(0, 0)
    qc.measure(1, 1)
    qc.barrier()

    # --- STEP 4: Bob corrects his qubit (2) based on Alice's measurements ---
    # In modern Qiskit (1.0+), we use the if_test context for dynamic circuits.
    with qc.if_test((qc.clbits[1], 1)):
        qc.x(2)
    with qc.if_test((qc.clbits[0], 1)):
        qc.z(2)
    
    return qc

def main():
    print("--- Quantum Teleportation Simulation ---")
    
    # 1. Create the circuit
    teleport_circuit = create_quantum_teleportation_circuit()
    
    # 2. Visualize the circuit
    print("\nQuantum Circuit Diagram:")
    print(teleport_circuit.draw(output='text'))
    
    # 3. Simulate the circuit
    # Note: To verify teleportation, we can look at the statevector before Bob's correction
    # or use the simulator to check the final distribution.
    # However, since measurement collapses the state, we usually verify by 
    # teleporting and then applying the inverse of the initial state-prep gates
    # to see if we get |0> back with 100% probability.
    
    # Let's verify by checking the Statevector if we hadn't measured Alice's qubits
    # (Deferred measurement principle)
    # Or more simply, let's just run it and see the result of Bob's qubit
    # To do this cleanly in simulation, we can use the 'save_statevector' instruction
    # from Aer, but let's stick to a basic shot-based execution for clarity.
    
    simulator = AerSimulator()
    compiled_circuit = transpile(teleport_circuit, simulator)
    
    # We need to measure Bob's qubit at the end to see if it matches the input state.
    # But wait, if we measure Bob's qubit, we just get 0 or 1.
    # To verify properly, let's add a final measurement to Bob's qubit
    # after applying the inverse of the initialization gates.
    # Initialization was H then S. Inverse is Sdg then H.
    
    verification_circuit = teleport_circuit.copy()
    verification_circuit.barrier()
    verification_circuit.sdg(2)
    verification_circuit.h(2)
    
    # Add a 3rd classical bit for Bob's measurement
    bob_cb = ClassicalRegister(1, "bob_result")
    verification_circuit.add_register(bob_cb)
    verification_circuit.measure(2, bob_cb[0])
    
    print("\nVerified Circuit (Initial state prep reversed on Bob's qubit):")
    print(verification_circuit.draw(output='text'))
    
    # Run simulation
    job = simulator.run(compiled_circuit if False else transpile(verification_circuit, simulator), shots=1024)
    result = job.result()
    counts = result.get_counts()
    
    print("\nSimulation Counts (Format: Bob_Result Alice_Reg1 Alice_Reg0):")
    print(counts)
    
    # Check if Bob always gets 0 (which means teleportation succeeded)
    # Since the classical bits are ordered [Bob Alice1 Alice0] or similar in Qiskit output strings
    # We check if the leading bit (Bob's result) is always '0'
    success_count = sum(count for bitstr, count in counts.items() if bitstr.startswith('0'))
    total_count = sum(counts.values())
    
    print(f"\nTeleportation Success Rate: {success_count/total_count * 100:.2f}%")
    if success_count == total_count:
        print("Success! Bob received the exact state Alice sent.")
    else:
        print("Verification failed or state was noisy.")

if __name__ == "__main__":
    main()
