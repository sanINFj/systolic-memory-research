"""Analytical bank-conflict comparison for physical mapping policies.

This is a model, not an RTL timing or hardware-performance measurement.
Each generated cycle requests one A value per active systolic row and
one B value per active systolic column, using the same K-step wavefront
schedule for every policy.
"""

import csv
import os
import sys
from collections import Counter
from math import ceil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from physical_mapping import POLICIES, map_element, NUM_BANKS


def analyze(M, K, N, tile_m=8, tile_n=8):
    results = []

    for policy in POLICIES:
        requests = 0
        conflict_cycles = 0
        excess_requests = 0
        modeled_service_cycles = 0
        ideal_service_cycles = 0
        max_bank_load = 0

        # Iterate over output tiles. Each tile uses a common reduction
        # schedule, and every policy sees exactly the same logical requests.
        for m0 in range(0, M, tile_m):
            tm = min(tile_m, M - m0)

            for n0 in range(0, N, tile_n):
                tn = min(tile_n, N - n0)

                for k in range(K):
                    loads = [0] * NUM_BANKS

                    # One A request for each active output row.
                    for r in range(tm):
                        p = map_element(
                            "A", m0 + r, k, K, N, policy
                        )
                        loads[p.bank] += 1

                    # One B request for each active output column.
                    for c in range(tn):
                        p = map_element(
                            "B", k, n0 + c, K, N, policy
                        )
                        loads[p.bank] += 1

                    count = sum(loads)
                    if count == 0:
                        continue

                    service = max(loads)
                    ideal = ceil(count / NUM_BANKS)

                    requests += count
                    modeled_service_cycles += service
                    ideal_service_cycles += ideal
                    max_bank_load = max(max_bank_load, service)

                    if service > 1:
                        conflict_cycles += 1
                        excess_requests += sum(
                            max(0, load - 1) for load in loads
                        )

        results.append({
            "M": M,
            "K": K,
            "N": N,
            "policy": policy,
            "logical_requests": requests,
            "conflict_cycles": conflict_cycles,
            "conflict_cycle_pct": (
                100.0 * conflict_cycles
                / (ceil(M / tile_m) * ceil(N / tile_n) * K)
            ),
            "excess_bank_requests": excess_requests,
            "modeled_service_cycles": modeled_service_cycles,
            "aggregate_8_bank_lower_bound_cycles": ideal_service_cycles,
            "excess_service_cycles_vs_aggregate_bound": (
                modeled_service_cycles - ideal_service_cycles
            ),
            "max_requests_to_one_bank_in_a_cycle": max_bank_load,
        })

    return results


def main():
    # Workloads are deliberately modest enough for the reference model.
    workloads = [
        (8, 8, 8),
        (13, 17, 29),
        (64, 64, 64),
        (128, 256, 128),
    ]

    os.makedirs("results", exist_ok=True)
    all_rows = []

    print("Physical Mapping Bank-Conflict Analysis")
    print("=======================================")
    print("Assumption: each bank services at most one read per cycle.")
    print("Metrics are analytical estimates, not RTL or hardware measurements.")
    print()

    for M, K, N in workloads:
        rows = analyze(M, K, N)
        all_rows.extend(rows)

        print(f"Workload M={M}, K={K}, N={N}")
        for row in rows:
            print(
                f"  {row['policy']:14s} "
                f"conflict_cycles={row['conflict_cycles']:>8,d} "
                f"({row['conflict_cycle_pct']:6.2f}%) "
                f"excess_requests={row['excess_bank_requests']:>9,d} "
                f"modeled_service_cycles={row['modeled_service_cycles']:>10,d} "
                f"max_bank_load={row['max_requests_to_one_bank_in_a_cycle']}"
            )
        print()

    output = "results/physical_mapping_conflicts.csv"
    with open(output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(all_rows[0]))
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"Saved {len(all_rows)} rows to {output}")


if __name__ == "__main__":
    main()
