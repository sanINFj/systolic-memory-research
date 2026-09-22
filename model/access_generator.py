"""
Generate A/B memory accesses for an 8x8 systolic array.

This is a simplified access-pattern model.

The purpose is to determine which matrix elements are
requested by the systolic array at each cycle.
"""

ARRAY_SIZE = 8


def generate_accesses(K):
    """
    Generate A and B accesses for an 8x8 systolic array.

    Returns a list of cycles.

    Each cycle contains:

        A accesses
        B accesses

    represented as:

        (row, column)
    """

    cycles = []

    # Systolic computation proceeds through K.
    #
    # We use the standard skewed input schedule:
    #
    # A[i][k] enters row i at cycle i + k
    # B[k][j] enters column j at cycle j + k

    total_cycles = K + 2 * (ARRAY_SIZE - 1)

    for t in range(total_cycles):

        A_accesses = []
        B_accesses = []

        # --------------------------------------------
        # A accesses
        # --------------------------------------------

        for i in range(ARRAY_SIZE):

            k = t - i

            if 0 <= k < K:

                A_accesses.append(
                    (i, k)
                )

        # --------------------------------------------
        # B accesses
        # --------------------------------------------

        for j in range(ARRAY_SIZE):

            k = t - j

            if 0 <= k < K:

                B_accesses.append(
                    (k, j)
                )

        cycles.append({
            "cycle": t,
            "A": A_accesses,
            "B": B_accesses
        })

    return cycles


def print_accesses(K=8):

    print("=" * 70)
    print("SYSTOLIC ACCESS GENERATOR")
    print("=" * 70)

    print(
        f"Array: {ARRAY_SIZE} x {ARRAY_SIZE}"
    )

    print(
        f"K: {K}"
    )

    print()

    accesses = generate_accesses(K)

    for entry in accesses:

        print(
            f"Cycle {entry['cycle']}:"
        )

        print(
            f"  A: {entry['A']}"
        )

        print(
            f"  B: {entry['B']}"
        )

        print()


if __name__ == "__main__":
    print_accesses()
