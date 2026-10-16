"""
Combined capacity-aware tiling and SRAM bank-conflict analysis.

This is an analytical model, not measured hardware performance.
It uses the existing 8x8 systolic access generator and bank mappings.

Compares:
  - Fixed 8x8x8 microtile configuration
  - Capacity-aware macro-tile configuration

Metrics are reported separately:
  - Estimated bytes transferred
  - Estimated bank service cycles
  - Ideal service cycles under an aggregate 8-bank bound
  - Excess service cycles relative to that bound

Limitations:
  - Does not simulate RTL timing or concurrent macrotiles.
  - Does not model physical SRAM layout, DMA, or inter-tile caching.
  - Assumes one read per bank per cycle.
"""

import csv
import os
import sys
import math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import access_generator
import banking_model as bank_model
import capacity_tile_selector as tile_model
import full_gemm_banking as gemm_model

ARRAY_SIZE = 8
NUM_BANKS = bank_model.NUM_BANKS

POLICIES = ["modulo", "split", "operand_aware"]


def measure_bank_service(M, K, N, BM, BK, BN, policy):
    """Estimate service cycles across macrotiles and 8x8 microtiles."""

    requests_total = 0
    service_total = 0
    ideal_total = 0
    max_bank_load = 0

    for m0 in range(0, M, BM):
        macro_m = min(BM, M - m0)

        for n0 in range(0, N, BN):
            macro_n = min(BN, N - n0)

            for k0 in range(0, K, BK):
                block_k = min(BK, K - k0)

                for mm in range(m0, m0 + macro_m, ARRAY_SIZE):
                    tm = min(ARRAY_SIZE, m0 + macro_m - mm)

                    for nn in range(n0, n0 + macro_n, ARRAY_SIZE):
                        tn = min(ARRAY_SIZE, n0 + macro_n - nn)

                        schedule = access_generator.generate_accesses(
                            K=block_k, M=tm, N=tn
                        )

                        for cycle in schedule:
                            loads = [0] * NUM_BANKS

                            for local_row, local_k in cycle["A"]:
                                global_row = mm + local_row
                                global_k = k0 + local_k

                                bank = gemm_model.get_bank(
                                    operand="A",
                                    row=global_row,
                                    col=global_k,
                                    K=K,
                                    N=N,
                                    policy=policy,
                                )
                                loads[bank] += 1

                            for local_k, local_col in cycle["B"]:
                                global_k = k0 + local_k
                                global_col = nn + local_col

                                bank = gemm_model.get_bank(
                                    operand="B",
                                    row=global_k,
                                    col=global_col,
                                    K=K,
                                    N=N,
                                    policy=policy,
                                )
                                loads[bank] += 1

                            count = sum(loads)
                            if count == 0:
                                continue

                            service = max(loads)
                            ideal = math.ceil(count / NUM_BANKS)

                            requests_total += count
                            service_total += service
                            ideal_total += ideal
                            max_bank_load = max(max_bank_load, service)

    return {
        "requests": requests_total,
        "service_cycles": service_total,
        "ideal_service_cycles": ideal_total,
        "excess_service_cycles": service_total - ideal_total,
        "max_bank_load": max_bank_load,
    }


def make_row(name, dims, config_name, tile, policy, baseline_bytes):
    M, K, N = dims
    BM, BK, BN = tile

    estimate = tile_model.evaluate(M, K, N, BM, BK, BN)
    if estimate is None:
        raise RuntimeError(f"Illegal tile for {name}: {tile}")

    service = measure_bank_service(
        M, K, N, BM, BK, BN, policy
    )

    reduction = (
        100.0 * (baseline_bytes - estimate["total_bytes"])
        / baseline_bytes
        if baseline_bytes else 0.0
    )

    return {
        "workload": name,
        "M": M,
        "K": K,
        "N": N,
        "configuration": config_name,
        "policy": policy,
        "BM": BM,
        "BK": BK,
        "BN": BN,
        "footprint_bytes": estimate["footprint_bytes"],
        "capacity_utilization_pct": estimate["capacity_utilization_pct"],
        "estimated_A_bytes": estimate["A_bytes"],
        "estimated_B_bytes": estimate["B_bytes"],
        "estimated_C_bytes": estimate["C_bytes"],
        "estimated_total_bytes": estimate["total_bytes"],
        "baseline_8x8_bytes": baseline_bytes,
        "traffic_reduction_pct_vs_8x8": reduction,
        **service,
    }


def main():
    os.makedirs("results", exist_ok=True)
    rows = []

    print("\nCombined Capacity and Banking Analysis")
    print("=======================================")
    print("Policies:", ", ".join(POLICIES))
    print("Metrics: modeled traffic and bank service, reported separately")
    print("WARNING: analytical estimates, not RTL performance measurements\n")

    for name, dims in tile_model.WORKLOADS.items():
        M, K, N = dims

        selected = tile_model.choose_tile(M, K, N)
        adaptive_tile = (selected["BM"], selected["BK"], selected["BN"])

        baseline_tile = (
            min(ARRAY_SIZE, M),
            min(ARRAY_SIZE, K),
            min(ARRAY_SIZE, N),
        )

        baseline = tile_model.evaluate(M, K, N, *baseline_tile)
        baseline_bytes = baseline["total_bytes"]

        print(f"{name}: baseline={baseline_tile}, selected={adaptive_tile}")

        for policy in POLICIES:
            for config_name, tile in (
                ("fixed_8x8", baseline_tile),
                ("capacity_selected", adaptive_tile),
            ):
                row = make_row(
                    name, dims, config_name, tile, policy, baseline_bytes
                )
                rows.append(row)

                print(
                    f"  {policy:14s} {config_name:18s} "
                    f"bytes={row['estimated_total_bytes']:>10,d} "
                    f"service={row['service_cycles']:>9,d} "
                    f"ideal={row['ideal_service_cycles']:>9,d} "
                    f"excess={row['excess_service_cycles']:>8,d}"
                )

    output = "results/combined_tile_banking_results.csv"
    with open(output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nSaved {len(rows)} experiment rows to {output}")
    print("PASS: all evaluated configurations satisfy the modeled capacity limit.")


if __name__ == "__main__":
    main()
