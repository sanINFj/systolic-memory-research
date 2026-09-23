"""
Generate the operand access pattern seen by an 8x8 systolic array.

For a standard skewed systolic schedule:

    A request:
        A[i][k] where k = t - i

    B request:
        B[k][j] where k = t - j

M and N may be smaller than 8 for edge tiles.
"""

ARRAY_SIZE = 8


def generate_accesses(K, M=ARRAY_SIZE, N=ARRAY_SIZE):
    """
    Generate A/B requests for one output tile.

    Parameters:
        K : GEMM reduction dimension
        M : active output rows, 1..8
        N : active output columns, 1..8

    Returns:
        List of dictionaries containing A and B requests
        for each systolic injection cycle.
    """

    if M < 1 or M > ARRAY_SIZE:
        raise ValueError(
            f"M must be between 1 and {ARRAY_SIZE}"
        )

    if N < 1 or N > ARRAY_SIZE:
        raise ValueError(
            f"N must be between 1 and {ARRAY_SIZE}"
        )

    if K < 1:
        raise ValueError("K must be >= 1")

    total_cycles = K + M + N - 2

    cycles = []

    for t in range(total_cycles):

        A_accesses = []
        B_accesses = []

        # A enters from the left.
        for i in range(M):

            k = t - i

            if 0 <= k < K:
                A_accesses.append((i, k))

        # B enters from the top.
        for j in range(N):

            k = t - j

            if 0 <= k < K:
                B_accesses.append((k, j))

        cycles.append(
            {
                "cycle": t,
                "A": A_accesses,
                "B": B_accesses,
            }
        )

    return cycles


if __name__ == "__main__":

    K = 8

    accesses = generate_accesses(
        K=K,
        M=8,
        N=8,
    )

    print(f"Access trace for 8x8x{K}")
    print(f"Injection cycles: {len(accesses)}")
    print()

    for cycle in accesses:

        print(
            f"cycle {cycle['cycle']:2d}: "
            f"A={cycle['A']} "
            f"B={cycle['B']}"
        )
