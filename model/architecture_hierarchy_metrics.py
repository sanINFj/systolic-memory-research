#!/usr/bin/env python3
"""First-order analytical comparison; not measured RTL performance."""
import csv
import math
from pathlib import Path

ARRAY = 8
SCRATCHPAD_BYTES = 64 * 1024
CACHE_BYTES = 32 * 1024
LINE_BYTES = 64
EXTERNAL_BW = 16
STARTUP = 20

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
    "edge_13x29x17": (13, 29, 17),
}
ARCHS = ("direct_memory", "cache", "scratchpad", "cache_scratchpad")


def ceildiv(a, b):
    return (a + b - 1) // b


def tiled_traffic(M, K, N, tm, tk, tn):
    traffic = 0
    groups = 0
    for m in range(0, M, tm):
        mm = min(tm, M - m)
        for n in range(0, N, tn):
            nn = min(tn, N - n)
            groups += 1
            traffic += 4 * mm * nn  # output write
            for k in range(0, K, tk):
                kk = min(tk, K - k)
                traffic += mm * kk + kk * nn
    return traffic, groups


def choose_tile(M, K, N):
    # Greedy capacity-aware search in multiples of the 8x8 array.
    best = None
    for tm in range(ARRAY, min(M, 128) + 1, ARRAY):
        for tk in range(ARRAY, min(K, 256) + 1, ARRAY):
            for tn in range(ARRAY, min(N, 128) + 1, ARRAY):
                footprint = tm * tk + tk * tn + 4 * tm * tn
                if footprint <= SCRATCHPAD_BYTES:
                    score = tm * tk * tn
                    if best is None or score > best[0]:
                        best = (score, tm, tk, tn)
    if best:
        return best[1:]
    return min(M, ARRAY), min(K, ARRAY), min(N, ARRAY)


def run(name, M, K, N, arch):
    macs = M * K * N
    ops = 2 * macs
    compute_cycles = ceildiv(macs, ARRAY * ARRAY)

    if arch == "direct_memory":
        traffic, groups = tiled_traffic(
            M, K, N, min(M, ARRAY), min(K, ARRAY), min(N, ARRAY)
        )
        cache_size = scratch_size = 0
    elif arch == "cache":
        raw = M * K + K * N + 4 * M * N
        traffic = ceildiv(raw, LINE_BYTES) * LINE_BYTES
        groups = ceildiv(M, ARRAY) * ceildiv(N, ARRAY)
        cache_size, scratch_size = CACHE_BYTES, 0
    elif arch == "scratchpad":
        tm, tk, tn = choose_tile(M, K, N)
        traffic, groups = tiled_traffic(M, K, N, tm, tk, tn)
        cache_size, scratch_size = 0, SCRATCHPAD_BYTES
    else:
        raw = M * K + K * N + 4 * M * N
        traffic = ceildiv(raw, LINE_BYTES) * LINE_BYTES
        tm, tk, tn = choose_tile(M, K, N)
        groups = ceildiv(M, tm) * ceildiv(N, tn) * ceildiv(K, tk)
        cache_size, scratch_size = CACHE_BYTES, SCRATCHPAD_BYTES

    memory_cycles = STARTUP + ceildiv(traffic, EXTERNAL_BW)
    total_cycles = max(compute_cycles, memory_cycles)
    utilization = min(100.0, 100.0 * macs / (total_cycles * ARRAY * ARRAY))

    return {
        "workload": name, "M": M, "K": K, "N": N,
        "architecture": arch, "MAC_operations": macs,
        "mul_add_operations": ops, "external_traffic_bytes": traffic,
        "arithmetic_intensity_ops_per_byte": round(ops / traffic, 4),
        "ideal_compute_cycles": compute_cycles,
        "estimated_memory_cycles": memory_cycles,
        "estimated_total_cycles": total_cycles,
        "estimated_effective_bandwidth_bytes_per_cycle": round(traffic / total_cycles, 4),
        "estimated_PE_utilization_pct": round(utilization, 2),
        "tile_groups": groups, "cache_capacity_bytes": cache_size,
        "scratchpad_capacity_bytes": scratch_size,
        "model_type": "analytical_estimate_not_RTL_measurement",
    }


def main():
    rows = [
        run(name, *shape, arch)
        for name, shape in WORKLOADS.items()
        for arch in ARCHS
    ]
    out = Path("results/architecture_hierarchy_metrics.csv")
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print("WARNING: analytical estimates, not RTL measurements.")
    print(f"{'Workload':<18} {'Architecture':<18} {'Traffic(B)':>12} "
          f"{'AI(op/B)':>10} {'Cycles(est)':>12} {'PE util %':>10}")
    for r in rows:
        print(f"{r['workload']:<18} {r['architecture']:<18} "
              f"{r['external_traffic_bytes']:>12,} "
              f"{r['arithmetic_intensity_ops_per_byte']:>10.3f} "
              f"{r['estimated_total_cycles']:>12,} "
              f"{r['estimated_PE_utilization_pct']:>10.2f}")
    print(f"\nSaved {len(rows)} rows to {out}")


if __name__ == "__main__":
    main()
