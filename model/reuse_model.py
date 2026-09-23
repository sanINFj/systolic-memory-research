"""
Data-reuse model for tiled GEMM.

Dataflows:

OS = Output Stationary
    The output/partial-sum tile remains stationary while
    the K dimension is processed.

WS = Weight Stationary
    The weight tile remains reusable while multiple M tiles
    are processed.

This is an analytical memory-traffic model.
It is NOT cycle-accurate yet.
"""

from traffic_model import calculate_tile_counts
from tiling_model import tile_footprint


def calculate_reuse_traffic(
    M,
    K,
    N,
    Mt,
    Kt,
    Nt,
    dataflow
):
    """
    Calculate external-memory traffic using a simple
    data-reuse model.
    """

    if dataflow not in ["OS", "WS"]:
        raise ValueError(
            "dataflow must be 'OS' or 'WS'"
        )

    m_tiles, k_tiles, n_tiles = calculate_tile_counts(
        M, K, N,
        Mt, Kt, Nt
    )

    footprint = tile_footprint(
        Mt, Kt, Nt
    )

    A_tile = footprint["A_bytes"]
    B_tile = footprint["B_bytes"]
    C_tile = footprint["C_bytes"]

    # --------------------------------------------------
    # Output Stationary
    # --------------------------------------------------
    #
    # A/B are streamed for each output tile and K tile.
    # C stays stationary across K.
    #
    # A:
    #   m_tiles * n_tiles * k_tiles
    #
    # B:
    #   m_tiles * n_tiles * k_tiles
    #
    # C:
    #   m_tiles * n_tiles
    #
    # --------------------------------------------------

    if dataflow == "OS":

        A_reads = (
            m_tiles
            * n_tiles
            * k_tiles
            * A_tile
        )

        B_reads = (
            m_tiles
            * n_tiles
            * k_tiles
            * B_tile
        )

        C_writes = (
            m_tiles
            * n_tiles
            * C_tile
        )

    # --------------------------------------------------
    # Weight Stationary
    # --------------------------------------------------
    #
    # B tile is reused across all M tiles.
    #
    # B:
    #   n_tiles * k_tiles
    #
    # A:
    #   m_tiles * n_tiles * k_tiles
    #
    # C:
    #   m_tiles * n_tiles
    #
    # --------------------------------------------------

    else:

        A_reads = (
            m_tiles
            * n_tiles
            * k_tiles
            * A_tile
        )

        B_reads = (
            n_tiles
            * k_tiles
            * B_tile
        )

        C_writes = (
            m_tiles
            * n_tiles
            * C_tile
        )

    total_reads = A_reads + B_reads
    total_writes = C_writes
    total_traffic = total_reads + total_writes

    return {
        "dataflow": dataflow,

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


def calculate_reuse_factors(
    M,
    K,
    N,
    Mt,
    Kt,
    Nt,
    dataflow
):
    """
    Calculate simple effective reuse factors.

    Reuse factor = naive traffic / actual traffic.
    """

    footprint = tile_footprint(
        Mt, Kt, Nt
    )

    m_tiles, k_tiles, n_tiles = calculate_tile_counts(
        M, K, N,
        Mt, Kt, Nt
    )

    A_tile = footprint["A_bytes"]
    B_tile = footprint["B_bytes"]

    naive_A = (
        m_tiles
        * k_tiles
        * n_tiles
        * A_tile
    )

    naive_B = (
        m_tiles
        * k_tiles
        * n_tiles
        * B_tile
    )

    result = calculate_reuse_traffic(
        M,
        K,
        N,
        Mt,
        Kt,
        Nt,
        dataflow
    )

    A_reuse = (
        naive_A / result["A_reads"]
        if result["A_reads"] > 0
        else 1.0
    )

    B_reuse = (
        naive_B / result["B_reads"]
        if result["B_reads"] > 0
        else 1.0
    )

    return {
        "A_reuse": A_reuse,
        "B_reuse": B_reuse,
    }


def print_reuse_analysis():

    M = 128
    K = 128
    N = 128

    Mt = 32
    Kt = 32
    Nt = 32

    print("=" * 60)
    print("DATA REUSE ANALYSIS")
    print("=" * 60)

    print(
        f"GEMM : {M} x {K} * {K} x {N}"
    )

    print(
        f"Tile : {Mt} x {Kt} x {Nt}"
    )

    print()

    for dataflow in ["OS", "WS"]:

        traffic = calculate_reuse_traffic(
            M,
            K,
            N,
            Mt,
            Kt,
            Nt,
            dataflow
        )

        reuse = calculate_reuse_factors(
            M,
            K,
            N,
            Mt,
            Kt,
            Nt,
            dataflow
        )

        print(f"Dataflow: {dataflow}")

        print(
            f"  A reads : "
            f"{traffic['A_reads'] / 1024:.2f} KB"
        )

        print(
            f"  B reads : "
            f"{traffic['B_reads'] / 1024:.2f} KB"
        )

        print(
            f"  C writes: "
            f"{traffic['C_writes'] / 1024:.2f} KB"
        )

        print(
            f"  Total    : "
            f"{traffic['total_traffic'] / 1024:.2f} KB"
        )

        print(
            f"  A reuse  : "
            f"{reuse['A_reuse']:.2f}x"
        )

        print(
            f"  B reuse  : "
            f"{reuse['B_reuse']:.2f}x"
        )

        print()


if __name__ == "__main__":
    print_reuse_analysis()
