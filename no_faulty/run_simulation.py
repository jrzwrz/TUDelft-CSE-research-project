import matplotlib.pyplot as plt
import math
from scipy.stats import binom
from application import Node1Program, Node2Program, SenderProgram
from multiprocessing import Pool, cpu_count
from squidasm.run.stack.config import StackNetworkConfig
from squidasm.run.stack.run import run

# Fixed config
cfg = StackNetworkConfig.from_file("../config.yaml")
mu, lam = 0.272, 0.94

N = 1000  # Total number of simulations per m
m_values = list(range(20, 400, 20))  # Range of m values
NUM_CORES = cpu_count()


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
        if node1_output is None or node2_output is None or node1_output != node2_output:
            failures += 1

    return m, failures, chunk_size


if __name__ == "__main__":
    # Prepare tasks: split N simulations into chunks per m
    tasks = []
    for m in m_values:
        base_chunk = N // NUM_CORES
        remainder = N % NUM_CORES
        for i in range(NUM_CORES):
            chunk = base_chunk + (1 if i < remainder else 0)
            if chunk > 0:
                tasks.append((m, chunk))

    # Run all chunks in parallel
    with Pool(processes=NUM_CORES) as pool:
        chunk_results = pool.map(simulate_chunk, tasks)

    # Aggregate results by m
    results_by_m = {}
    for m, failures, runs in chunk_results:
        if m not in results_by_m:
            results_by_m[m] = {"failures": 0, "runs": 0}
        results_by_m[m]["failures"] += failures
        results_by_m[m]["runs"] += runs

    # Prepare plot data
    m_values_sorted = sorted(results_by_m.keys())
    failure_probs = []
    sems = []
    exact_probs = []

    for m in m_values_sorted:
        failures = results_by_m[m]["failures"]
        total_runs = results_by_m[m]["runs"]
        prob = failures / total_runs
        sem = math.sqrt(prob * (1 - prob) / total_runs)
        failure_probs.append(prob)
        sems.append(sem)

        T = math.ceil(mu * m)
        exact_probs.append(binom.cdf(T - 1, m, 1 / 3))

    # Plotting
    plt.figure(figsize=(6, 4))
    plt.plot(
        m_values_sorted, exact_probs,
        "o",
        markerfacecolor="white",
        markeredgecolor="green",
        markeredgewidth=1.5,
        linestyle="None",
        label="Exact (Eq. 25)"
    )
    plt.errorbar(
        m_values_sorted, failure_probs, yerr=sems,
        fmt='rx', label="Monte Carlo", capsize=5
    )
    plt.xlabel("number of four-qubit singlet states, $m$")
    plt.ylabel("failure probability")
    plt.title(f"Failure Probabilities (No Faulty, N={N})")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig("no_faulty_1000.png", dpi=300)
