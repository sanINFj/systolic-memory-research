"""
Sanity check for SRAM bank mappings.
"""


from banking_model import (
    ARRAY_SIZE,
    POLICIES,
    get_bank,
)


def main():

    K = 128
    N = 8

    print(
        "Bank Mapping Sanity Check"
    )
    print(
        "========================="
    )

    for policy in POLICIES:

        print()
        print(
            f"Policy: {policy}"
        )

        print(
            "A row mapping:"
        )

        for i in range(ARRAY_SIZE):

            bank = get_bank(
                operand="A",
                row=i,
                index=0,
                K=K,
                N=N,
                policy=policy,
            )

            print(
                f"  A row {i} -> "
                f"bank {bank}"
            )

        print(
            "B column mapping:"
        )

        for j in range(ARRAY_SIZE):

            bank = get_bank(
                operand="B",
                row=0,
                index=j,
                K=K,
                N=N,
                policy=policy,
            )

            print(
                f"  B col {j} -> "
                f"bank {bank}"
            )


if __name__ == "__main__":
    main()
