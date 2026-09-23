"""
Tiled GEMM external-memory traffic model.

This is an initial analytical model.

Assumptions:
    - A and B are INT8
    - C is INT32
    - Tiles are loaded from external memory
    - A tile and B tile are loaded for each K tile
    - C is written back after all K tiles are accumulated
    - No cache reuse between independent output tiles yet

This model will be refined when WS/OS dataflows are added.
"""

from memory_model import BYTES_PER_INT8, BYTES_PER_INT32
from tiling_model import tile_footprint


def ceil_div(a, b):
    """Ceiling division."""

    return (a + b - 1) // b


def calculate_tile_counts(M, K, N, Mt, Kt, Nt):
    """
    Calculate the number of tiles in each GEMM dimension.
    """

    m_tiles = ceil_div(M, Mt)
    k_tiles = ceil_div(K, Kt)
    n_tiles = ceil_div(N, Nt)

    return m_tiles, k_tiles, n_tiles


def calculate_traffic(M, K, N, Mt, Kt, Nt):
    """
    Estimate external-memory traffic for tiled GEMM.

    A tile:
        Mt x Kt

    B tile:
        Kt x Nt

    C tile:
        Mt x Nt
    """

    m_tiles, k_tiles, n_tiles = calculate_tile_counts(
        M, K, N, Mt, Kt, Nt
    )

    footprint = tile_footprint(Mt, Kt, Nt)

    A_tile_bytes = footprint["A_bytes"]
    B_tile_bytes = footprint["B_bytes"]
    C_tile_bytes = footprint["C_bytes"]

    # A and B are loaded once for every M/K/N tile combination
    A_reads = m_tiles * k_tiles * n_tiles * A_tile_bytes
    B_reads = m_tiles * k_tiles * n_tiles * B_tile_bytes

    # Each output tile is written once after all K tiles
    C_writes = m_tiles * n_tiles * C_tile_bytes

    total_reads = A_reads + B_reads
    total_writes = C_writes

    total_traffic = total_reads + total_writes

    return {
        "m_tiles": m_tiles,
        "k_tiles": k_tiles,
        "n_tiles": n_tiles,

        "A_reads": A_reads,
        "B_reads": B_reads,
        "C_writes": C_writes,

        "total_reads": total_reads,
        "total_writes": total_writes,
        "total_traffic": total_traffic,
    }


def print_traffic(M, K, N, Mt, Kt, Nt):

    result = calculate_traffic(
        M, K, N,
        Mt, Kt, Nt
    )

    print("=" * 60)
    print("TILED GEMM TRAFFIC")
    print("=" * 60)

    print(
        f"GEMM : {M} x {K} * {K} x {N}"
    )

    print(
        f"Tile : {Mt} x {Kt} * {Kt} x {Nt}"
    )

    print()

    print(
        f"M tiles : {result['m_tiles']}"
    )

    print(
        f"K tiles : {result['k_tiles']}"
    )

    print(
        f"N tiles : {result['n_tiles']}"
    )

    print()

    print(
        f"A reads : {result['A_reads'] / 1024:.2f} KB"
    )

    print(
        f"B reads : {result['B_reads'] / 1024:.2f} KB"
    )

    print(
        f"C writes: {result['C_writes'] / 1024:.2f} KB"
    )

    print()

    print(
        f"Total reads : {result['total_reads'] / 1024:.2f} KB"
    )

    print(
        f"Total writes: {result['total_writes'] / 1024:.2f} KB"
    )

    print(
        f"Total traffic: {result['total_traffic'] / 1024:.2f} KB"
    )


if __name__ == "__main__":

    print_traffic(
        M=128,
        K=128,
        N=128,
        Mt=32,
        Kt=32,
        Nt=32
    )
