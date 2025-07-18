import os
import tempfile
import yaml
import numpy as np
import matplotlib.pyplot as plt

from squidasm.run.stack.config import StackNetworkConfig
from application import Node1Program, Node2Program, SenderProgram
from multiprocessing import Pool, cpu_count
from squidasm.run.stack.run import run

# Parameters
mu, lam = 0.272, 0.94
N = 1000  # Number of runs per probability value
m = 300  # Fixed value of m
prob_values = list(range(0, 101, 5)) #define range of p values
div = 1000000

def simulate_failure_prob(p):
    p_value = p / div
    node1_program = Node1Program(m=m, mu=mu, lam=lam)
    node2_program = Node2Program(m=m, mu=mu, lam=lam)
    sender_program = SenderProgram(m=m)

    with open("../config.yaml", "r") as f:
        config = yaml.safe_load(f)

    qdevice_cfg = config.get("qdevice_cfg", {})
    qdevice_cfg["single_qubit_gate_depolar_prob"] = p_value
    qdevice_cfg["two_qubit_gate_depolar_prob"] = p_value

    for stack in config.get("stacks", []):
        if "qdevice_cfg" in stack:
            stack["qdevice_cfg"]["single_qubit_gate_depolar_prob"] = p_value
            stack["qdevice_cfg"]["two_qubit_gate_depolar_prob"] = p_value

    temp_file = tempfile.NamedTemporaryFile(mode="w+", suffix=".yaml", delete=False)
    try:
        yaml.dump(config, temp_file, sort_keys=False)
        temp_file.flush()
        temp_path = temp_file.name
        temp_file.close()

        cfg = StackNetworkConfig.from_file(temp_path)

        results = run(
            config=cfg,
            programs={
                "Node1": node1_program,
                "Node2": node2_program,
                "Sender": sender_program
            },
            num_times=N
        )

        failures = 0
        for i in range(N):
            sender_output = results[0][i]["xs"]
            node1_output = results[1][i]["y0"]
            node2_output = results[2][i]["y1"]
            if sender_output != node2_output or node1_output is None:
                failures += 1

        failure_prob = failures / N
        sem = np.sqrt(failure_prob * (1 - failure_prob) / N)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    return failure_prob, sem


if __name__ == "__main__":
    with Pool(processes=cpu_count()) as pool:
        results = pool.map(simulate_failure_prob, prob_values)

    failure_probs = [r[0] for r in results]
    error_bars = [r[1] for r in results]
    p_values = [p / div for p in prob_values]

    # Plotting
    plt.figure(figsize=(8, 5))
    plt.errorbar(p_values, failure_probs, yerr=error_bars, fmt='o-', capsize=5, label="Failure Probability")
    plt.axhline(y=0.05, color='red', linestyle='--', label="5% Threshold")
    plt.xlabel("Gate Depolarizing Probability")
    plt.ylabel("Failure Probability")
    plt.title(f"Failure Probability vs Gate Depolarizing Probability (R0 Faulty, N={N}, m={m})")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig("node1_faulty_noise_1000.png", dpi=300)