"""
Configuration-aware GEMM tile selection.

The selector searches a small set of candidate tile sizes
and keeps only tiles that fit inside a selected SRAM
organization.

This is NOT the workload-aware selector from the research
idea yet. It is simply a legal-tile finder.
"""

from memory_model import get_config
from tiling_model import tile_footprint
from traffic_model import calculate_traffic


CANDIDATE_TILES = [
    (8, 8, 8),
    (16, 16, 16),
    (32, 32, 32),
    (64, 64, 64),
]


def tile_fits_config(Mt, Kt, Nt, config_name):

    config = get_config(config_name)
    footprint = tile_footprint(Mt, Kt, Nt)

    input_capacity = config["inputs_kb"] * 1024
    weight_capacity = config["weights_kb"] * 1024
    output_capacity = config["outputs_kb"] * 1024

    return (
        footprint["A_bytes"] <= input_capacity
        and footprint["B_bytes"] <= weight_capacity
        and footprint["C_bytes"] <= output_capacity
    )


def find_legal_tiles(config_name):

    legal_tiles = []

    for Mt, Kt, Nt in CANDIDATE_TILES:

        if tile_fits_config(Mt, Kt, Nt, config_name):
            legal_tiles.append((Mt, Kt, Nt))

    return legal_tiles


def select_lowest_traffic_tile(
    M,
    K,
    N,
    config_name
):
    """
    Among legal candidate tiles, select the tile with
    the lowest estimated external-memory traffic.

    This is an analytical baseline, not the final
    workload-aware selector.
    """

    legal_tiles = find_legal_tiles(config_name)

    if not legal_tiles:
        raise ValueError(
            f"No legal tile found for configuration {config_name}"
        )

    best_tile = None
    best_traffic = None

    for Mt, Kt, Nt in legal_tiles:

        traffic = calculate_traffic(
            M,
            K,
            N,
            Mt,
            Kt,
            Nt
        )

        total = traffic["total_traffic"]

        if best_traffic is None or total < best_traffic:
            best_traffic = total
            best_tile = (Mt, Kt, Nt)

    return best_tile, best_traffic


def print_analysis(M, K, N):

    print("=" * 60)
    print("CONFIGURATION-AWARE TILE ANALYSIS")
    print("=" * 60)

    print(f"GEMM: {M} x {K} * {K} x {N}")
    print()

    for config_name in ["A", "B", "C"]:

        print(f"Configuration {config_name}")

        legal = find_legal_tiles(config_name)

        print("  Legal tiles:")

        for tile in legal:
            print(
                f"    {tile[0]} x {tile[1]} x {tile[2]}"
            )

        best_tile, best_traffic = select_lowest_traffic_tile(
            M,
            K,
            N,
            config_name
        )

        print(
            f"  Selected tile: "
            f"{best_tile[0]} x "
            f"{best_tile[1]} x "
            f"{best_tile[2]}"
        )

        print(
            f"  Estimated traffic: "
            f"{best_traffic / 1024:.2f} KB"
        )

        print()


if __name__ == "__main__":

    print_analysis(
        M=128,
        K=128,
        N=128
    )
