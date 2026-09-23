"""
Dataflow-aware SRAM access model
================================

Fixed accelerator:
    - 8x8 systolic array
    - INT8 operands
    - INT32 accumulation
    - 8 SRAM banks
    - 64 KB total SRAM

Dataflows:
    1. OS - Output Stationary
    2. WS - Weight Stationary

Important:
    The banking policies remain fixed and are imported from
    banking_model.py.

This file models the SRAM-side operand traffic associated with
the two dataflow organizations.

OS:
    - A and B are streamed according to the existing skewed
      systolic schedule.
    - This corresponds to the access pattern already used by
      access_generator.py.

WS:
    - B/weights are loaded into the array as a stationary
      operand tile.
    - A/input values are then streamed through the compute
      structure.
    - Weight loading and input streaming are represented as
      separate memory phases.

This is an architectural memory-traffic model.
It is NOT yet the final RTL implementation of WS.
"""


ARRAY_SIZE = 8


DATAFLOWS = [
    "OS",
    "WS",
]


def generate_os_accesses(K, M=ARRAY_SIZE, N=ARRAY_SIZE):
    """
    Generate the existing Output-Staytionary-style skewed
    systolic access schedule.

    A[i][k]:
        k = t - i

    B[k][j]:
        k = t - j

    Returns:
        List of cycles.
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

        for i in range(M):

            k = t - i

            if 0 <= k < K:
                A_accesses.append((i, k))

        for j in range(N):

            k = t - j

            if 0 <= k < K:
                B_accesses.append((k, j))

        cycles.append(
            {
                "cycle": t,
                "phase": "compute",
                "A": A_accesses,
                "B": B_accesses,
            }
        )

    return cycles


def generate_ws_accesses(K, M=ARRAY_SIZE, N=ARRAY_SIZE):
    """
    Generate a Weight-Stationary memory access schedule.

    The model uses K in tiles of ARRAY_SIZE.

    For every K tile:

        Phase 1:
            Load an 8xN weight tile B[k][j].

        Phase 2:
            Stream the corresponding A rows through the array.

    Weight accesses:
        B[k][j]

    Input accesses:
        A[i][k]

    The weight load phase is explicitly separated from the
    input streaming phase so that the memory system can later
    be evaluated under the same banking policies.

    This model assumes that a weight tile is loaded once and
    then reused while the corresponding input values are streamed.

    It is intentionally a memory-organization model rather than
    a claim about the exact final RTL WS datapath.
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

    cycles = []

    weight_tile_start = 0

    for k_base in range(
        0,
        K,
        ARRAY_SIZE,
    ):

        k_end = min(
            k_base + ARRAY_SIZE,
            K,
        )

        # --------------------------------------------------
        # Phase 1: load stationary weights
        # --------------------------------------------------

        local_k = 0

        for k in range(k_base, k_end):

            B_accesses = []

            for j in range(N):

                B_accesses.append(
                    (k, j)
                )

            cycles.append(
                {
                    "cycle": len(cycles),
                    "phase": "weight_load",
                    "A": [],
                    "B": B_accesses,
                    "k_base": k_base,
                    "k": k,
                }
            )

            local_k += 1

        # --------------------------------------------------
        # Phase 2: stream inputs
        # --------------------------------------------------

        for k in range(k_base, k_end):

            A_accesses = []

            for i in range(M):

                A_accesses.append(
                    (i, k)
                )

            cycles.append(
                {
                    "cycle": len(cycles),
                    "phase": "input_stream",
                    "A": A_accesses,
                    "B": [],
                    "k_base": k_base,
                    "k": k,
                }
            )

    return cycles


def generate_accesses(
    dataflow,
    K,
    M=ARRAY_SIZE,
    N=ARRAY_SIZE,
):
    """
    Dispatch to the requested dataflow.
    """

    if dataflow == "OS":

        return generate_os_accesses(
            K=K,
            M=M,
            N=N,
        )

    if dataflow == "WS":

        return generate_ws_accesses(
            K=K,
            M=M,
            N=N,
        )

    raise ValueError(
        f"Unknown dataflow: {dataflow}"
    )


def summarize_accesses(
    dataflow,
    K,
    M=ARRAY_SIZE,
    N=ARRAY_SIZE,
):
    """
    Return basic traffic statistics.
    """

    cycles = generate_accesses(
        dataflow=dataflow,
        K=K,
        M=M,
        N=N,
    )

    total_A = 0
    total_B = 0

    weight_load_cycles = 0
    input_stream_cycles = 0
    compute_cycles = 0

    for cycle in cycles:

        total_A += len(
            cycle["A"]
        )

        total_B += len(
            cycle["B"]
        )

        if cycle["phase"] == "weight_load":
            weight_load_cycles += 1

        elif cycle["phase"] == "input_stream":
            input_stream_cycles += 1

        elif cycle["phase"] == "compute":
            compute_cycles += 1

    return {
        "dataflow": dataflow,
        "K": K,
        "M": M,
        "N": N,
        "cycles": len(cycles),
        "A_requests": total_A,
        "B_requests": total_B,
        "total_requests": total_A + total_B,
        "weight_load_cycles": weight_load_cycles,
        "input_stream_cycles": input_stream_cycles,
        "compute_cycles": compute_cycles,
    }


if __name__ == "__main__":

    print(
        "Dataflow Access Model"
    )
    print(
        "====================="
    )

    for K in [
        8,
        32,
        64,
    ]:

        print()
        print(
            f"K = {K}"
        )

        for dataflow in DATAFLOWS:

            result = summarize_accesses(
                dataflow=dataflow,
                K=K,
                M=8,
                N=8,
            )

            print(
                f"{dataflow:3s} "
                f"cycles="
                f"{result['cycles']:4d} "
                f"A="
                f"{result['A_requests']:5d} "
                f"B="
                f"{result['B_requests']:5d} "
                f"total="
                f"{result['total_requests']:5d}"
            )
