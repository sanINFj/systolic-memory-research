"""
SRAM-aware residency model.

This is a conservative first-order model.

Principle:

    Every operand must be loaded at least once.

Additional external-memory traffic occurs when the operand
cannot remain resident and therefore has to be reloaded.

Dataflows:

    OS:
        C/partial sums are stationary while K is processed.

    WS:
        B/weights are stationary while M is processed.

This model is intentionally simple and will later be
validated/refined against RTL and bandwidth measurements.
"""

from math import ceil

from memory_model import get_config
from tiling_model import tile_footprint


def ceil_div(a, b):
    return (a + b - 1) // b


def calculate_tile_counts(M, K, N, Mt, Kt, Nt):

    m_tiles = ceil_div(M, Mt)
    k_tiles = ceil_div(K, Kt)
    n_tiles = ceil_div(N, Nt)

    return m_tiles, k_tiles, n_tiles


def calculate_residency(
    M,
    K,
    N,
    Mt,
    Kt,
    Nt,
    config_name,
    dataflow
):
    """
    Calculate conservative external-memory traffic.

    Returns None if the tile does not fit.
    """

    if dataflow not in ["OS", "WS"]:
        raise ValueError(
            "dataflow must be 'OS' or 'WS'"
        )

    config = get_config(config_name)

    footprint = tile_footprint(
        Mt,
        Kt,
        Nt
    )

    A_tile = footprint["A_bytes"]
    B_tile = footprint["B_bytes"]
    C_tile = footprint["C_bytes"]

    input_capacity = config["inputs_kb"] * 1024
    weight_capacity = config["weights_kb"] * 1024
    output_capacity = config["outputs_kb"] * 1024

    # --------------------------------------------------
    # Check whether one computational tile fits.
    # --------------------------------------------------

    if A_tile > input_capacity:
        return None

    if B_tile > weight_capacity:
        return None

    if C_tile > output_capacity:
        return None

    m_tiles, k_tiles, n_tiles = calculate_tile_counts(
        M,
        K,
        N,
        Mt,
        Kt,
        Nt
    )

    # --------------------------------------------------
    # Minimum possible external traffic.
    #
    # These are hard lower bounds.
    # --------------------------------------------------

    min_A_reads = M * K
    min_B_reads = K * N
    min_C_writes = M * N * 4

    # --------------------------------------------------
    # OS model
    #
    # C tile remains resident while processing K.
    #
    # A and B are streamed according to the tiling.
    # --------------------------------------------------

    if dataflow == "OS":

        A_reads = (
            m_tiles
            * k_tiles
            * n_tiles
            * A_tile
        )

        B_reads = (
            m_tiles
            * k_tiles
            * n_tiles
            * B_tile
        )

        C_writes = (
            m_tiles
            * n_tiles
            * C_tile
        )

    # --------------------------------------------------
    # WS model
    #
    # B tiles are reused across M tiles.
    #
    # However, every distinct B tile must still be loaded
    # at least once.
    # --------------------------------------------------

    else:

        A_reads = (
            m_tiles
            * k_tiles
            * n_tiles
            * A_tile
        )

        B_reads = (
            k_tiles
            * n_tiles
            * B_tile
        )

        C_writes = (
            m_tiles
            * n_tiles
            * C_tile
        )

    # --------------------------------------------------
    # Enforce physical lower bounds.
    #
    # This prevents the analytical model from predicting
    # less traffic than the amount of actual data involved.
    # --------------------------------------------------

    A_reads = max(
        A_reads,
        min_A_reads
    )

    B_reads = max(
        B_reads,
        min_B_reads
    )

    C_writes = max(
        C_writes,
        min_C_writes
    )

    total_reads = (
        A_reads
        + B_reads
    )

    total_writes = C_writes

    total_traffic = (
        total_reads
        + total_writes
    )

    return {
        "config": config_name,
        "dataflow": dataflow,

        "m_tiles": m_tiles,
        "k_tiles": k_tiles,
        "n_tiles": n_tiles,

        "A_tile_bytes": A_tile,
        "B_tile_bytes": B_tile,
        "C_tile_bytes": C_tile,

        "A_reads": A_reads,
        "B_reads": B_reads,
        "C_writes": C_writes,

        "total_reads": total_reads,
        "total_writes": total_writes,
        "total_traffic": total_traffic,
    }


def print_residency_analysis():

    M = 128
    K = 128
    N = 128

    Mt = 32
    Kt = 32
    Nt = 32

    print("=" * 80)
    print("SRAM-AWARE RESIDENCY ANALYSIS")
    print("=" * 80)

    print(
        f"GEMM: {M} x {K} * {K} x {N}"
    )

    print(
        f"Tile: {Mt} x {Kt} x {Nt}"
    )

    print()

    for config_name in ["A", "B", "C"]:

        for dataflow in ["OS", "WS"]:

            result = calculate_residency(
                M,
                K,
                N,
                Mt,
                Kt,
                Nt,
                config_name,
                dataflow
            )

            print(
                f"{config_name}-{dataflow}"
            )

            if result is None:
                print(
                    "  Tile does not fit"
                )
                print()
                continue

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
                f"{result['total_traffic'] / 1024:.2f} KB"
            )

            print()


if __name__ == "__main__":
    print_residency_analysis()
