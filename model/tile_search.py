"""
Configuration-aware tile search.

Searches legal tile shapes for:

    - SRAM configurations A/B/C
    - OS/WS dataflows

For each legal tile we calculate:

    - SRAM-aware external traffic
    - analytical compute cycles

The goal is to determine whether different SRAM
organizations actually produce different optimal
configurations for different workloads.
"""

from memory_model import get_config
from tiling_model import tile_footprint
from residency_model import calculate_residency
from execution_model import gemm_compute_cycles


# ------------------------------------------------------------
# Candidate tile dimensions
# ------------------------------------------------------------

TILE_SIZES = [8, 16, 32, 64, 128, 256]


# ------------------------------------------------------------
# Tile legality
# ------------------------------------------------------------

def tile_fits_config(
    Mt,
    Kt,
    Nt,
    config_name
):
    """
    Check whether a tile fits in the SRAM partition.
    """

    config = get_config(config_name)

    footprint = tile_footprint(
        Mt,
        Kt,
        Nt
    )

    A_capacity = (
        config["inputs_kb"] * 1024
    )

    B_capacity = (
        config["weights_kb"] * 1024
    )

    C_capacity = (
        config["outputs_kb"] * 1024
    )

    A_fits = (
        footprint["A_bytes"]
        <= A_capacity
    )

    B_fits = (
        footprint["B_bytes"]
        <= B_capacity
    )

    C_fits = (
        footprint["C_bytes"]
        <= C_capacity
    )

    return (
        A_fits
        and B_fits
        and C_fits
    )


# ------------------------------------------------------------
# Search
# ------------------------------------------------------------

def search_tiles(
    M,
    K,
    N,
    config_name,
    dataflow
):

    results = []

    # Don't search tiles larger than the workload dimension.

    Mt_candidates = [
        x for x in TILE_SIZES
        if x <= M
    ]

    Kt_candidates = [
        x for x in TILE_SIZES
        if x <= K
    ]

    Nt_candidates = [
        x for x in TILE_SIZES
        if x <= N
    ]

    for Mt in Mt_candidates:

        for Kt in Kt_candidates:

            for Nt in Nt_candidates:

                # ----------------------------------------
                # SRAM capacity check
                # ----------------------------------------

                if not tile_fits_config(
                    Mt,
                    Kt,
                    Nt,
                    config_name
                ):
                    continue

                # ----------------------------------------
                # Traffic model
                # ----------------------------------------

                traffic = calculate_residency(
                    M,
                    K,
                    N,
                    Mt,
                    Kt,
                    Nt,
                    config_name,
                    dataflow
                )

                if traffic is None:
                    continue

                # ----------------------------------------
                # Compute model
                # ----------------------------------------

                compute_cycles = (
                    gemm_compute_cycles(
                        M,
                        K,
                        N,
                        Mt,
                        Kt,
                        Nt
                    )
                )

                results.append({

                    "config": config_name,
                    "dataflow": dataflow,

                    "Mt": Mt,
                    "Kt": Kt,
                    "Nt": Nt,

                    "traffic":
                        traffic["total_traffic"],

                    "A_reads":
                        traffic["A_reads"],

                    "B_reads":
                        traffic["B_reads"],

                    "C_writes":
                        traffic["C_writes"],

                    "compute_cycles":
                        compute_cycles,
                })

    return results


# ------------------------------------------------------------
# Best candidates
# ------------------------------------------------------------

def get_traffic_optimal(results):

    if not results:
        return None

    return min(
        results,
        key=lambda x: (
            x["traffic"],
            x["compute_cycles"]
        )
    )


def get_compute_optimal(results):

    if not results:
        return None

    return min(
        results,
        key=lambda x: (
            x["compute_cycles"],
            x["traffic"]
        )
    )


# ------------------------------------------------------------
# Pareto frontier
# ------------------------------------------------------------

def is_dominated(
    candidate,
    other
):

    traffic_better_or_equal = (
        other["traffic"]
        <= candidate["traffic"]
    )

    cycles_better_or_equal = (
        other["compute_cycles"]
        <= candidate["compute_cycles"]
    )

    strictly_better = (
        other["traffic"]
        < candidate["traffic"]
        or
        other["compute_cycles"]
        < candidate["compute_cycles"]
    )

    return (
        traffic_better_or_equal
        and cycles_better_or_equal
        and strictly_better
    )


def get_pareto_frontier(results):

    frontier = []

    for candidate in results:

        dominated = False

        for other in results:

            if other is candidate:
                continue

            if is_dominated(
                candidate,
                other
            ):
                dominated = True
                break

        if not dominated:
            frontier.append(
                candidate
            )

    frontier.sort(
        key=lambda x: (
            x["traffic"],
            x["compute_cycles"]
        )
    )

    return frontier


# ------------------------------------------------------------
# Printing
# ------------------------------------------------------------

def print_result(
    label,
    result
):

    print(label)

    if result is None:

        print(
            "  No legal tile"
        )

        print()

        return

    print(
        f"  Tile: "
        f"{result['Mt']} "
        f"x {result['Kt']} "
        f"x {result['Nt']}"
    )

    print(
        f"  A reads: "
        f"{result['A_reads'] / 1024:.2f} KB"
    )

    print(
        f"  B reads: "
        f"{result['B_reads'] / 1024:.2f} KB"
    )

    print(
        f"  C writes: "
        f"{result['C_writes'] / 1024:.2f} KB"
    )

    print(
        f"  Total traffic: "
        f"{result['traffic'] / 1024:.2f} KB"
    )

    print(
        f"  Compute cycles: "
        f"{result['compute_cycles']}"
    )

    print()


# ------------------------------------------------------------
# Main analysis
# ------------------------------------------------------------

def print_best_results(
    M,
    K,
    N
):

    print("=" * 90)
    print(
        "CONFIGURATION-AWARE TILE SEARCH"
    )
    print("=" * 90)

    print(
        f"GEMM: "
        f"{M} x {K} * {K} x {N}"
    )

    print()

    for config_name in [
        "A",
        "B",
        "C"
    ]:

        for dataflow in [
            "OS",
            "WS"
        ]:

            print("-" * 90)

            print(
                f"CONFIGURATION: "
                f"{config_name}    "
                f"DATAFLOW: "
                f"{dataflow}"
            )

            print()

            results = search_tiles(
                M,
                K,
                N,
                config_name,
                dataflow
            )

            if not results:

                print(
                    "No legal tile."
                )

                print()

                continue

            traffic_best = (
                get_traffic_optimal(
                    results
                )
            )

            compute_best = (
                get_compute_optimal(
                    results
                )
            )

            pareto = (
                get_pareto_frontier(
                    results
                )
            )

            print_result(
                "TRAFFIC-OPTIMAL:",
                traffic_best
            )

            print_result(
                "COMPUTE-OPTIMAL:",
                compute_best
            )

            print(
                "PARETO FRONTIER:"
            )

            for result in pareto:

                print(
                    f"  "
                    f"{result['Mt']}x"
                    f"{result['Kt']}x"
                    f"{result['Nt']} : "
                    f"traffic="
                    f"{result['traffic']/1024:.2f} KB, "
                    f"cycles="
                    f"{result['compute_cycles']}"
                )

            print()


if __name__ == "__main__":

    print_best_results(
        M=128,
        K=128,
        N=128
    )
