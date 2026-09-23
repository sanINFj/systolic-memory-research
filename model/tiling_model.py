"""
GEMM tiling model.

This model determines whether a selected GEMM tile fits
inside a particular SRAM organization.

Data types:
    A/B = INT8  = 1 byte
    C   = INT32 = 4 bytes
"""

from memory_model import get_config


BYTES_PER_INT8 = 1
BYTES_PER_INT32 = 4


def tile_footprint(Mt, Kt, Nt):
    """
    Calculate SRAM footprint for one GEMM tile.

    A tile: Mt x Kt
    B tile: Kt x Nt
    C tile: Mt x Nt
    """

    A_bytes = Mt * Kt * BYTES_PER_INT8
    B_bytes = Kt * Nt * BYTES_PER_INT8
    C_bytes = Mt * Nt * BYTES_PER_INT32

    return {
        "A_bytes": A_bytes,
        "B_bytes": B_bytes,
        "C_bytes": C_bytes,
    }


def tile_fits(Mt, Kt, Nt, config_name):
    """
    Check whether a tile fits in the selected SRAM allocation.
    """

    config = get_config(config_name)
    footprint = tile_footprint(Mt, Kt, Nt)

    A_capacity = config["inputs_kb"] * 1024
    B_capacity = config["weights_kb"] * 1024
    C_capacity = config["outputs_kb"] * 1024

    return {
        "A_fits": footprint["A_bytes"] <= A_capacity,
        "B_fits": footprint["B_bytes"] <= B_capacity,
        "C_fits": footprint["C_bytes"] <= C_capacity,
    }


def print_tile_analysis(Mt, Kt, Nt):

    footprint = tile_footprint(Mt, Kt, Nt)

    print("=" * 60)
    print(f"TILE: {Mt} x {Kt} * {Kt} x {Nt}")
    print("=" * 60)

    print(
        f"A tile: {footprint['A_bytes'] / 1024:.2f} KB"
    )

    print(
        f"B tile: {footprint['B_bytes'] / 1024:.2f} KB"
    )

    print(
        f"C tile: {footprint['C_bytes'] / 1024:.2f} KB"
    )

    print()

    for config_name in ["A", "B", "C"]:

        result = tile_fits(
            Mt,
            Kt,
            Nt,
            config_name
        )

        print(f"Configuration {config_name}")
        print(f"  A fits : {result['A_fits']}")
        print(f"  B fits : {result['B_fits']}")
        print(f"  C fits : {result['C_fits']}")
        print()


if __name__ == "__main__":

    # Start with a 32x32x32 tile.
    print_tile_analysis(32, 32, 32)

    # Compare with a larger tile.
    print_tile_analysis(64, 64, 64)
