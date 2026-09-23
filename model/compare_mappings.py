"""
Compare the three SRAM banking policies.

Policies:

    modulo
    split
    operand_aware
"""


from conflict_model import analyze_policy
from banking_model import POLICIES


K_VALUES = [
    8,
    32,
    64,
    128,
    256,
]


def print_header():

    print()

    print(
        f"{'K':>5} "
        f"{'Policy':>16} "
        f"{'Requests':>10} "
        f"{'Service':>10} "
        f"{'Stalls':>10} "
        f"{'MinStall':>10} "
        f"{'Excess':>10}"
    )

    print("-" * 85)


def main():

    print(
        "Systolic-Array SRAM Banking Comparison"
    )
    print(
        "======================================="
    )

    print_header()

    for K in K_VALUES:

        for policy in POLICIES:

            result = analyze_policy(
                K=K,
                M=8,
                N=8,
                policy=policy,
            )

            print(
                f"{K:5d} "
                f"{policy:>16} "
                f"{result['requests']:10d} "
                f"{result['service_cycles']:10d} "
                f"{result['stall_cycles']:10d} "
                f"{result['minimum_stall_cycles']:10d} "
                f"{result['excess_stall_cycles']:10d}"
            )


if __name__ == "__main__":
    main()
