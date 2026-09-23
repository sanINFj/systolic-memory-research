"""
SRAM banking model for the systolic-array-aware memory study.

Architecture:
    - 64 KB total SRAM
    - 8 banks
    - 8 KB per bank
    - INT8 operands
    - 8x8 systolic array

Banking policies:
    1. modulo
    2. split
    3. operand_aware
"""

ARRAY_SIZE = 8

NUM_BANKS = 8
BANK_SIZE_BYTES = 8 * 1024
TOTAL_SRAM_BYTES = NUM_BANKS * BANK_SIZE_BYTES

BYTES_PER_INT8 = 1

# First-pass physical placement.
A_BASE = 0
B_BASE = 32 * 1024


POLICIES = [
    "modulo",
    "split",
    "operand_aware",
]


def bank_from_byte_address(address):
    """
    Conventional interleaved SRAM banking.

    INT8 means one matrix element occupies one byte,
    so bank selection is directly:

        address % NUM_BANKS
    """
    return address % NUM_BANKS


def a_address(row, k, K):
    """
    Row-major A[M][K].

    A[row][k] -> A_BASE + row*K + k
    """
    return A_BASE + (row * K + k) * BYTES_PER_INT8


def b_address(k, col, N):
    """
    Row-major B[K][N].

    B[k][col] -> B_BASE + k*N + col
    """
    return B_BASE + (k * N + col) * BYTES_PER_INT8


def modulo_bank_A(row, k, K):
    return bank_from_byte_address(
        a_address(row, k, K)
    )


def modulo_bank_B(k, col, N):
    return bank_from_byte_address(
        b_address(k, col, N)
    )


def split_bank_A(row):
    """
    Split baseline:

        A -> banks 0,1,2,3
    """
    return row % 4


def split_bank_B(col):
    """
    Split baseline:

        B -> banks 4,5,6,7
    """
    return 4 + (col % 4)


def operand_aware_bank_A(row):
    """
    Proposed mapping:

        A row i -> bank i % 8
    """
    return row % NUM_BANKS


def operand_aware_bank_B(col):
    """
    Proposed mapping:

        B column j -> bank (j + 4) % 8
    """
    return (col + 4) % NUM_BANKS


def get_bank(operand, row, index, K, N, policy):
    """
    Return SRAM bank for one operand access.

    A:
        (row, index) = (i, k)

    B:
        (row, index) = (k, j)
    """

    if policy == "modulo":

        if operand == "A":
            return modulo_bank_A(
                row,
                index,
                K,
            )

        if operand == "B":
            return modulo_bank_B(
                row,
                index,
                N,
            )

    elif policy == "split":

        if operand == "A":
            return split_bank_A(row)

        if operand == "B":
            return split_bank_B(index)

    elif policy == "operand_aware":

        if operand == "A":
            return operand_aware_bank_A(row)

        if operand == "B":
            return operand_aware_bank_B(index)

    raise ValueError(
        f"Invalid operand/policy combination: "
        f"operand={operand}, policy={policy}"
    )


if __name__ == "__main__":

    print("SRAM Banking Model")
    print("==================")
    print(
        f"Total SRAM : "
        f"{TOTAL_SRAM_BYTES // 1024} KB"
    )
    print(
        f"Banks      : {NUM_BANKS}"
    )
    print(
        f"Bank size  : "
        f"{BANK_SIZE_BYTES // 1024} KB"
    )

    for policy in POLICIES:

        print()
        print(f"Policy: {policy}")

        for i in range(ARRAY_SIZE):

            a_bank = get_bank(
                "A",
                i,
                0,
                128,
                8,
                policy,
            )

            b_bank = get_bank(
                "B",
                0,
                i,
                128,
                8,
                policy,
            )

            print(
                f"  A row {i} -> bank {a_bank} | "
                f"B col {i} -> bank {b_bank}"
            )
