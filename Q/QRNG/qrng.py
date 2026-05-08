from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator

def generate_random_bit():
    qc = QuantumCircuit(1, 1)

    # Apply H gate to create superposition
    qc.h(0)
    # Perform measurement
    qc.measure(0, 0)

    # Use AerSimulator as the backend
    simulator = AerSimulator()
    
    # In newer Qiskit versions, transpilation is required before execution
    compiled_circuit = transpile(qc, simulator)
    
    # Execute the circuit
    result = simulator.run(compiled_circuit, shots=1).result()
    counts = result.get_counts(compiled_circuit)

    # Return the measurement result (0 or 1)
    return int(list(counts.keys())[0])

def generate_random_number(bits=8):
    number = 0
    for i in range(bits):
        bit = generate_random_bit()
        # Move the bit to the corresponding position and perform OR operation
        number |= (bit << i)
    return number

if __name__ == "__main__":
    print("--- Generating 10 independent random bits ---")
    for _ in range(10):
        print(generate_random_bit(), end=" ")
    print("\n")

    print("--- Generating an 8-bit random number (0-255) ---")
    print(generate_random_number(8))
    
    print("--- Generating a 16-bit random number (0-65535) ---")
    print(generate_random_number(16))
