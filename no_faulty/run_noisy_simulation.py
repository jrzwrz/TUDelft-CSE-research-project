import os
import tempfile
import yaml
import matplotlib.pyplot as plt
import numpy as np

from squidasm.run.stack.config import StackNetworkConfig
from application import Node1Program, Node2Program, SenderProgram
from multiprocessing import Pool, cpu_count
from squidasm.run.stack.run import run
from collections import defaultdict

# Parameters
mu, lam = 0.272, 0.94
N = 1000                            # Total number of runs per probability value
m = 300                             # Value of m
CHUNKS_PER_P = cpu_count()         # Divide per probability for full CPU utilization
prob_values = list(range(0, 101, 5)) # 0 to 20 inclusive, step 1
div = 1000000
def simulate_chunk(args):
    p, n_runs = args
    p_value = p / div

    # Initialize programs
    node1_program = Node1Program(m=m, mu=mu, lam=lam)
    node2_program = Node2Program(m=m, mu=mu, lam=lam)
    sender_program = SenderProgram(m=m)

    # Load and modify configuration
    with open("../config.yaml", "r") as f:
        config = yaml.safe_load(f)

    #Modify the gate error probabilities
    qdevice_cfg = config.get("qdevice_cfg", {})
    qdevice_cfg["single_qubit_gate_depolar_prob"] = p_value
    qdevice_cfg["two_qubit_gate_depolar_prob"] = p_value

    for stack in config.get("stacks", []):
        if "qdevice_cfg" in stack:
            stack["qdevice_cfg"]["single_qubit_gate_depolar_prob"] = p_value
            stack["qdevice_cfg"]["two_qubit_gate_depolar_prob"] = p_value

    #Simulate with temporary config file
    temp_file = tempfile.NamedTemporaryFile(mode="w+", suffix=".yaml", delete=False)
    try:
        yaml.dump(config, temp_file, sort_keys=False)
        temp_file.flush()
        temp_path = temp_file.name
        temp_file.close()

        cfg = StackNetworkConfig.from_file(temp_path)

        # Run simulation
        results = run(
            config=cfg,
            programs={
                "Node1": node1_program,
                "Node2": node2_program,
                "Sender": sender_program
            },
            num_times=n_runs
        )

        failures = 0
        for i in range(n_runs):
            sender_output = results[0][i]["xs"]
            node1_output = results[1][i]["y0"]
            node2_output = results[2][i]["y1"]
            if node1_output != node2_output or (node1_output is None or node2_output is None):
                failures += 1

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    return failures, n_runs, p  # Return p for grouping

if __name__ == "__main__":
    base_chunk = N // CHUNKS_PER_P
    remainder = N % CHUNKS_PER_P

    # Create list of chunk sizes with evenly distributed remainder
    chunk_sizes = [base_chunk + 1 if i < remainder else base_chunk for i in range(CHUNKS_PER_P)]

    # Build all tasks (p, chunk_size) for each prob value
    tasks = []
    for p in prob_values:
        tasks.extend([(p, chunk_sizes[i]) for i in range(CHUNKS_PER_P)])

    with Pool(processes=cpu_count()) as pool:
        chunk_results = pool.map(simulate_chunk, tasks)

    # Aggregate results
    failure_counts = defaultdict(int)
    total_counts = defaultdict(int)

    for failures, n_runs, p in chunk_results:
        failure_counts[p] += failures
        total_counts[p] += n_runs

    failure_probs = []
    error_bars = []
    p_values = []

    for p in prob_values:
        failures = failure_counts[p]
        total = total_counts[p]
        prob = failures / total
        sem = np.sqrt(prob * (1 - prob) / total) if total > 0 else 0
        failure_probs.append(prob)
        error_bars.append(sem)
        p_values.append(p / div)

    # Plotting with error bars
    plt.figure(figsize=(8, 5))
    plt.errorbar(p_values, failure_probs, yerr=error_bars, fmt='o-', capsize=5, label="Failure Probability")
    plt.axhline(y=0.05, color='red', linestyle='--', label="5% Threshold")
    plt.xlabel("Gate Depolarizing Probability")
    plt.ylabel("Failure Probability")
    plt.title(f"Failure Probability vs Gate Depolarizing Probability (No Faulty, N={N}, m={m})")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig("no_faulty_noise_test.png", dpi=300)