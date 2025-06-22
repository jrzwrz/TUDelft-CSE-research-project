import math
import matplotlib.pyplot as plt
from application import Node1Program, Node2Program, SenderProgram
from multiprocessing import Pool, cpu_count
from squidasm.run.stack.config import StackNetworkConfig
from squidasm.run.stack.run import run
from math import comb, ceil

# Fixed config
cfg = StackNetworkConfig.from_file("../config.yaml")
mu, lam = 0.272, 0.94
N = 1000  # Total number of runs per m
NUM_CORES = cpu_count()
m_values = list(range(20, 400, 20))  # Range of m values


def simulate_chunk(args):
    m, chunk_size = args
    node1_program = Node1Program(m=m, mu=mu, lam=lam)
    node2_program = Node2Program(m=m, mu=mu, lam=lam)
    sender_program = SenderProgram(m=m, mu=mu, lam=lam)

    results = run(
        config=cfg,
        programs={"Node1": node1_program, "Node2": node2_program, "Sender": sender_program},
        num_times=chunk_size
    )

    failures = 0
    for i in range(chunk_size):
        node1_output = results[1][i]["y0"]
        node2_output = results[2][i]["y1"]
        sender_output = results[0][i]["xs"]
        if node1_output != node2_output and None not in (node1_output, node2_output):
            failures += 1
        if sender_output == -1:
            failures += 1

    return m, failures, chunk_size


def multinomial(m, l1, l2, l3):
    return comb(m, l1) * comb(m - l1, l2)


def theoretical_failure_bounds(m, mu, lam):
    T = ceil(mu * m)
    Q = T - ceil(T * lam) + 1
    pf_down = 0
    total_prob = 0

    for l3 in range(T, m - Q + 1):
        for l1 in range(T - Q, m - Q - l3 + 1):
            l2 = m - l1 - l3
            prob = multinomial(m, l1, l2, l3) * (1 / 3) ** m
            pf_down += prob * (0.5) ** Q
            total_prob += prob

    pf_up = pf_down + (1 - total_prob)
    return pf_up


if __name__ == "__main__":
    # Prepare chunked simulation tasks
    tasks = []
    for m in m_values:
        base_chunk = N // NUM_CORES
        remainder = N % NUM_CORES
        for i in range(NUM_CORES):
            chunk = base_chunk + (1 if i < remainder else 0)
            if chunk > 0:
                tasks.append((m, chunk))

    # Run parallel chunks
    with Pool(processes=NUM_CORES) as pool:
        chunk_results = pool.map(simulate_chunk, tasks)

    # Aggregate results
    results_by_m = {}
    for m, failures, runs in chunk_results:
        if m not in results_by_m:
            results_by_m[m] = {"failures": 0, "runs": 0}
        results_by_m[m]["failures"] += failures
        results_by_m[m]["runs"] += runs

    m_values_sorted = sorted(results_by_m.keys())
    failure_probs = []
    sems = []
    theoretical_upper = []

    for m in m_values_sorted:
        failures = results_by_m[m]["failures"]
        runs = results_by_m[m]["runs"]
        prob = failures / runs
        sem = math.sqrt(prob * (1 - prob) / runs)
        failure_probs.append(prob)
        sems.append(sem)
        theoretical_upper.append(theoretical_failure_bounds(m, mu, lam))

    # Plot results
    plt.figure(figsize=(6, 4))
    plt.plot(
        m_values_sorted, theoretical_upper,
        "o",
        markerfacecolor="white",
        markeredgecolor="green",
        markeredgewidth=1.5,
        linestyle="None",
        label=r"Theoretical $p_f^{(S),\uparrow}$"
    )
    plt.errorbar(
        m_values_sorted, failure_probs, yerr=sems,
        fmt='rx', label="Monte Carlo", capsize=5
    )
    plt.xlabel("number of four-qubit singlet states, $m$")
    plt.ylabel("failure probability")
    plt.title(f"Failure Probabilities (Sender Faulty, N={N})")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig("sender_faulty_1000.png", dpi=300)
