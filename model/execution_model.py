"""
First-order execution model for an 8x8 systolic array.

This estimates compute-side cycles for tiled GEMM.

It is intentionally analytical and will later be validated
against the RTL implementation.
"""

import math


ARRAY_SIZE = 8


def ceil_div(a, b):
    return (a + b - 1) // b


def tile_compute_cycles(Mt, Kt, Nt, array_size=ARRAY_SIZE):
    """
    Estimate cycles for one Mt x Kt x Nt GEMM tile.

    An array_size x array_size systolic array processes
    output microtiles of array_size x array_size.

    Approximate latency for each microtile:

        Kt + 2*(array_size - 1)

    The second term represents systolic fill/drain overhead.
    """

    m_microtiles = ceil_div(Mt, array_size)
    n_microtiles = ceil_div(Nt, array_size)

    fill_drain = 2 * (array_size - 1)

    cycles_per_microtile = Kt + fill_drain

    total_cycles = (
        m_microtiles
        * n_microtiles
        * cycles_per_microtile
    )

    return total_cycles


def gemm_compute_cycles(
    M,
    K,
    N,
    Mt,
    Kt,
    Nt,
    array_size=ARRAY_SIZE
):
    """
    Estimate total compute-side cycles for the complete GEMM.
    """

    m_tiles = ceil_div(M, Mt)
    k_tiles = ceil_div(K, Kt)
    n_tiles = ceil_div(N, Nt)

    tile_cycles = tile_compute_cycles(
        Mt,
        Kt,
        Nt,
        array_size
    )

    total_cycles = (
        m_tiles
        * k_tiles
        * n_tiles
        * tile_cycles
    )

    return total_cycles


def print_execution_analysis():

    M = 128
    K = 128
    N = 128

    tiles = [
        (64, 8, 64),
        (64, 64, 64),
        (32, 32, 32),
        (8, 8, 64),
    ]

    print("=" * 70)
    print("SYSTOLIC EXECUTION MODEL")
    print("=" * 70)

    print(f"GEMM: {M} x {K} * {K} x {N}")
    print()

    for Mt, Kt, Nt in tiles:

        cycles = gemm_compute_cycles(
            M,
            K,
            N,
            Mt,
            Kt,
            Nt
        )

        print(
            f"Tile {Mt}x{Kt}x{Nt}: "
            f"{cycles} compute cycles"
        )


if __name__ == "__main__":
    print_execution_analysis()
