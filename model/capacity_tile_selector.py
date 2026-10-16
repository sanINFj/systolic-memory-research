"""
Capacity-aware macro-tile selector for systolic GEMM.

Architecture assumptions:
  - 64 KiB scratchpad
  - 8x8 systolic compute array
  - INT8 A and B operands
  - INT32 output accumulator tile
  - One A tile, one B tile, and one C tile resident at a time

This is an analytical traffic model, not RTL timing or measured
accelerator performance. It does not yet model bank conflicts.
"""

import csv
import math
import os

CAPACITY_BYTES = 64 * 1024
ARRAY_SIZE = 8
ACC_BYTES = 4

WORKLOADS = {
    "square_32": (32, 32, 32),
    "square_64": (64, 64, 64),
    "square_128": (128, 128, 128),
    "square_256": (256, 256, 256),
    "input_heavy": (256, 64, 64),
    "weight_heavy": (64, 64, 256),
    "k_heavy": (64, 256, 64),
    "rectangular_1": (128, 512, 128),
    "rectangular_2": (512, 128, 128),
    "edge_70x70x64": (70, 64, 70),
    "edge_13x29x17": (13, 17, 29),
}

BASE_TILE_SIZES = (8, 16, 32, 64, 128, 256, 512)


def candidates(dimension):
    """Power-of-two tile candidates plus the exact edge dimension."""
    values = {
        min(dimension, size)
        for size in BASE_TILE_SIZES
        if size <= dimension
    }
    values.add(dimension)
    return sorted(v for v in values if v >= 1)


def evaluate(M, K, N, BM, BK, BN):
    """
    Estimate the working set and operand traffic.

    Working set:
        A tile: BM * BK bytes
        B tile: BK * BN bytes
        C tile: BM * BN * 4 bytes

    Traffic assumes each A/B tile is loaded for each output-tile
    pair and K block. C is written once after accumulation.
    No inter-tile cache reuse is assumed.
    """
    footprint = BM * BK + BK * BN + ACC_BYTES * BM * BN

    if footprint > CAPACITY_BYTES:
        return None

    m_tiles = math.ceil(M / BM)
    n_tiles = math.ceil(N / BN)
    k_tiles = math.ceil(K / BK)

    a_bytes = M * K * n_tiles
    b_bytes = K * N * m_tiles
    c_bytes = M * N * ACC_BYTES

    total_bytes = a_bytes + b_bytes + c_bytes
    operand_tile_loads = 2 * m_tiles * n_tiles * k_tiles

    return {
        "BM": BM,
        "BK": BK,
        "BN": BN,
        "footprint_bytes": footprint,
        "capacity_utilization_pct": 100 * footprint / CAPACITY_BYTES,
        "m_tiles": m_tiles,
        "n_tiles": n_tiles,
        "k_tiles": k_tiles,
        "total_tiles": m_tiles * n_tiles * k_tiles,
        "A_bytes": a_bytes,
        "B_bytes": b_bytes,
        "C_bytes": c_bytes,
        "total_bytes": total_bytes,
        "operand_tile_loads": operand_tile_loads,
    }


def choose_tile(M, K, N):
    valid = []

    for BM in candidates(M):
        for BK in candidates(K):
            for BN in candidates(N):
                result = evaluate(M, K, N, BM, BK, BN)
                if result is not None:
                    valid.append(result)

    if not valid:
        raise RuntimeError(
            f"No legal tile for M={M}, K={K}, N={N}"
        )

    # Minimize estimated traffic first, then tile-load count.
    # Prefer larger tiles only as a deterministic tie-break.
    return min(
        valid,
        key=lambda r: (
            r["total_bytes"],
            r["operand_tile_loads"],
            -r["footprint_bytes"],
        ),
    )


def main():
    os.makedirs("results", exist_ok=True)
    rows = []

    print("\nCapacity-Aware GEMM Macro-Tile Selector")
    print("=======================================")
    print(f"Scratchpad capacity: {CAPACITY_BYTES:,} bytes")
    print(f"Compute array: {ARRAY_SIZE}x{ARRAY_SIZE}")
    print("Objective: minimize modeled bytes, then tile loads")
    print("\nAll traffic values are estimates under the stated assumptions.\n")

    for name, (M, K, N) in WORKLOADS.items():
        selected = choose_tile(M, K, N)

        # Fixed 8x8 output macro-tile baseline, with K blocked to 8.
        baseline = evaluate(
            M, K, N,
            min(ARRAY_SIZE, M),
            min(ARRAY_SIZE, K),
            min(ARRAY_SIZE, N),
        )

        reduction = 0.0
        if baseline["total_bytes"]:
            reduction = 100.0 * (
                baseline["total_bytes"] - selected["total_bytes"]
            ) / baseline["total_bytes"]

        row = {
            "workload": name,
            "M": M,
            "K": K,
            "N": N,
            **selected,
            "baseline_8x8_bytes": baseline["total_bytes"],
            "traffic_reduction_pct_vs_8x8": reduction,
        }
        rows.append(row)

        print(
            f"{name:20s} "
            f"tile=({selected['BM']:3d},"
            f"{selected['BK']:3d},"
            f"{selected['BN']:3d}) "
            f"footprint={selected['footprint_bytes']:6,d} B "
            f"tiles={selected['total_tiles']:5,d} "
            f"traffic={selected['total_bytes']:10,d} B "
            f"vs_8x8={reduction:6.2f}%"
        )

    filename = "results/capacity_tile_results.csv"
    fields = list(rows[0].keys())

    with open(filename, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nResults saved to {filename}")

    assert all(
        row["footprint_bytes"] <= CAPACITY_BYTES
        for row in rows
    ), "Capacity constraint violated"

    print("PASS: all selected working sets fit within 64 KiB.")


if __name__ == "__main__":
    main()
