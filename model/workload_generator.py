"""
GEMM workload generator for the systolic-array memory study.

Each workload is described by:
    M x K  *  K x N  =  M x N
"""


WORKLOADS = [
    # Small square
    {"name": "square_32",  "M": 32,  "K": 32,  "N": 32},

    # Medium square
    {"name": "square_64",  "M": 64,  "K": 64,  "N": 64},

    # Large square
    {"name": "square_128", "M": 128, "K": 128, "N": 128},

    # Larger workload
    {"name": "square_256", "M": 256, "K": 256, "N": 256},

    # Input-activation heavy
    {"name": "input_heavy", "M": 256, "K": 64, "N": 64},

    # Weight-heavy
    {"name": "weight_heavy", "M": 64, "K": 64, "N": 256},

    # K-heavy
    {"name": "k_heavy", "M": 64, "K": 256, "N": 64},

    # Rectangular mixed workload
    {"name": "rectangular_1", "M": 128, "K": 512, "N": 128},

    {"name": "rectangular_2", "M": 512, "K": 128, "N": 128},
]


def get_workloads():
    """Return the complete workload list."""
    return WORKLOADS


def print_workloads():
    """Print workloads in a readable format."""

    print("=" * 60)
    print("GEMM WORKLOADS")
    print("=" * 60)

    for i, workload in enumerate(WORKLOADS):
        name = workload["name"]
        M = workload["M"]
        K = workload["K"]
        N = workload["N"]

        print(
            f"{i:2d}: {name:16s} "
            f"{M:4d} x {K:4d}  *  "
            f"{K:4d} x {N:4d}  =  "
            f"{M:4d} x {N:4d}"
        )

    print("=" * 60)
    print(f"Total workloads: {len(WORKLOADS)}")


if __name__ == "__main__":
    print_workloads()
