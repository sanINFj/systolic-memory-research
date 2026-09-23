"""
On-chip SRAM organization and GEMM footprint model.

Fixed total SRAM:
    64 KB

Physical organization:
    8 banks x 8 KB

Logical allocations:
    A: 16 KB weights, 32 KB inputs, 16 KB outputs
    B: 24 KB weights, 24 KB inputs, 16 KB outputs
    C: 32 KB weights, 16 KB inputs, 16 KB outputs

Data types:
    Inputs/weights : INT8  = 1 byte
    Accumulator    : INT32 = 4 bytes
"""

TOTAL_SRAM_KB = 64

NUM_BANKS = 8
BANK_SIZE_KB = 8

BYTES_PER_INT8 = 1
BYTES_PER_INT32 = 4


MEMORY_CONFIGS = {
    "A": {
        "weights_kb": 16,
        "inputs_kb": 32,
        "outputs_kb": 16,
    },

    "B": {
        "weights_kb": 24,
        "inputs_kb": 24,
        "outputs_kb": 16,
    },

    "C": {
        "weights_kb": 32,
        "inputs_kb": 16,
        "outputs_kb": 16,
    },
}


def validate_config(config):
    """Check that a memory configuration fits inside the SRAM budget."""

    total = (
        config["weights_kb"]
        + config["inputs_kb"]
        + config["outputs_kb"]
    )

    return total == TOTAL_SRAM_KB


def get_config(name):
    """Return a memory configuration by name."""

    if name not in MEMORY_CONFIGS:
        raise ValueError(f"Unknown memory configuration: {name}")

    return MEMORY_CONFIGS[name]


def gemm_footprint(M, K, N):
    """
    Calculate the storage required for one GEMM.

    A = M x K, INT8
    B = K x N, INT8
    C = M x N, INT32
    """

    input_bytes = M * K * BYTES_PER_INT8
    weight_bytes = K * N * BYTES_PER_INT8
    output_bytes = M * N * BYTES_PER_INT32

    return {
        "input_bytes": input_bytes,
        "weight_bytes": weight_bytes,
        "output_bytes": output_bytes,
    }


def bytes_to_kb(num_bytes):
    """Convert bytes to KB."""

    return num_bytes / 1024.0


def analyze_workload(workload, config_name):
    """
    Determine whether each GEMM operand fits in the selected
    logical SRAM allocation.
    """

    M = workload["M"]
    K = workload["K"]
    N = workload["N"]

    footprint = gemm_footprint(M, K, N)
    config = get_config(config_name)

    input_capacity = config["inputs_kb"] * 1024
    weight_capacity = config["weights_kb"] * 1024
    output_capacity = config["outputs_kb"] * 1024

    return {
        "workload": workload["name"],
        "config": config_name,

        "input_bytes": footprint["input_bytes"],
        "weight_bytes": footprint["weight_bytes"],
        "output_bytes": footprint["output_bytes"],

        "input_fits": footprint["input_bytes"] <= input_capacity,
        "weight_fits": footprint["weight_bytes"] <= weight_capacity,
        "output_fits": footprint["output_bytes"] <= output_capacity,
    }


def print_memory_organization():
    """Print the physical SRAM organization."""

    print("=" * 60)
    print("ON-CHIP SRAM ORGANIZATION")
    print("=" * 60)

    print(f"Total SRAM : {TOTAL_SRAM_KB} KB")
    print(f"Banks      : {NUM_BANKS}")
    print(f"Bank size  : {BANK_SIZE_KB} KB")

    print()

    for name, config in MEMORY_CONFIGS.items():

        total = (
            config["weights_kb"]
            + config["inputs_kb"]
            + config["outputs_kb"]
        )

        print(f"Configuration {name}")
        print(f"  Weights : {config['weights_kb']:2d} KB")
        print(f"  Inputs  : {config['inputs_kb']:2d} KB")
        print(f"  Outputs : {config['outputs_kb']:2d} KB")
        print(f"  Total   : {total:2d} KB")
        print(f"  Valid   : {validate_config(config)}")
        print()


def print_workload_analysis(workload):

    M = workload["M"]
    K = workload["K"]
    N = workload["N"]

    footprint = gemm_footprint(M, K, N)

    print("=" * 60)
    print(f"WORKLOAD: {workload['name']}")
    print(f"GEMM: {M} x {K} * {K} x {N}")
    print("=" * 60)

    print(
        f"Input  A : {bytes_to_kb(footprint['input_bytes']):8.2f} KB"
    )

    print(
        f"Weight B : {bytes_to_kb(footprint['weight_bytes']):8.2f} KB"
    )

    print(
        f"Output C : {bytes_to_kb(footprint['output_bytes']):8.2f} KB"
    )

    print()

    for config_name in MEMORY_CONFIGS:

        result = analyze_workload(workload, config_name)

        print(f"Configuration {config_name}")

        print(f"  Input fits  : {result['input_fits']}")
        print(f"  Weight fits : {result['weight_fits']}")
        print(f"  Output fits : {result['output_fits']}")

        print()


if __name__ == "__main__":

    # A representative workload for now.
    workload = {
        "name": "square_128",
        "M": 128,
        "K": 128,
        "N": 128,
    }

    print_memory_organization()
    print_workload_analysis(workload)
