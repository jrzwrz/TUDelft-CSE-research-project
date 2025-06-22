import math
import matplotlib.pyplot as plt
from application import Node1Program, Node2Program, SenderProgram
from multiprocessing import Pool, cpu_count
from squidasm.run.stack.config import StackNetworkConfig
from squidasm.run.stack.run import run
from math import comb

# Fixed config
cfg = StackNetworkConfig.from_file("../config.yaml")
mu, lam = 0.272, 0.94

N = 1000  # Total simulations per m value
NUM_CORES = cpu_count()
m_values = list(range(20, 400, 20))  # Range of m values


def multinomial(m, l1, l2, l3):
    return comb(m, l1) * comb(m - l1, l2)


def upper_bound_failure_probability(m, mu, lam):
    T = math.ceil(mu * m)
    Q = T - math.ceil(T * lam) + 1
    first_term = 0
    second_term = 0

    for l1 in range(T, m - T + 1):
        for l2 in range(0, T - Q + 1):
            l3 = m - l1 - l2
            temp = multinomial(m, l1, l2, l3) * ((1 / 3) ** l1) * ((1 / 6) ** l2) * ((1 / 2) ** l3)
            sum_term = sum(
                math.comb(T - l2, k) * ((2 / 3) ** k) * ((1 / 3) ** (T - l2 - k))
                for k in range(T - Q + 1 - l2, T - l2 + 1)
            )
            first_term += temp * sum_term

    for l1 in range(T, m - T + 1):
        for l2 in range(T - Q + 1, m - l1 + 1):
            l3 = m - l1 - l2
            first_term += multinomial(m, l1, l2, l3) * ((1 / 3) ** l1) * ((1 / 6) ** l2) * ((1 / 2) ** l3)

    for l1 in range(0, T):
        first_term += math.comb(m, l1) * ((1 / 3) ** l1) * ((2 / 3) ** (m - l1))

    for i in range(m - T + 1, m + 1):
        second_term += math.comb(m, i) * ((1 / 3) ** i) * ((2 / 3) ** (m - i))

    return first_term + second_term


def simulate_chunk(args):
    m, chunk_size = args
    node1_program = Node1Program(m=m, mu=mu, lam=lam)
    node2_program = Node2Program(m=m, mu=mu, lam=lam)
    sender_program = SenderProgram(m=m)

    results = run(
        config=cfg,
        programs={"Node1": node1_program, "Node2": node2_program, "Sender": sender_program},
        num_times=chunk_size
    )

    failures = 0
    for i in range(chunk_size):
        sender_output = results[0][i]["xs"]
        node1_output = results[1][i]["y0"]
        node2_output = results[2][i]["y1"]
        if sender_output != node2_output or node1_output is None:
            failures += 1

    return m, failures, chunk_size


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

    # Aggregate failures per m
    results_by_m = {}
    for m, failures, runs in chunk_results:
        if m not in results_by_m:
            results_by_m[m] = {"failures": 0, "runs": 0}
        results_by_m[m]["failures"] += failures
        results_by_m[m]["runs"] += runs

    m_values_sorted = sorted(results_by_m.keys())
    failure_probs = []
    sems = []
    upper_bounds = []

    for m in m_values_sorted:
        failures = results_by_m[m]["failures"]
        runs = results_by_m[m]["runs"]
        prob = failures / runs
        sem = math.sqrt(prob * (1 - prob) / runs)
        failure_probs.append(prob)
        sems.append(sem)
        upper_bounds.append(upper_bound_failure_probability(m, mu, lam))

    # Plotting
    plt.figure(figsize=(6, 4))
    plt.plot(
        m_values_sorted, upper_bounds,
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
    plt.title(f"Failure Probabilities (R0 Faulty, N={N})")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig("node1_faulty_1000.png", dpi=300)