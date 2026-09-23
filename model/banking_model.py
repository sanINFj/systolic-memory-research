"""
SRAM Banking Model
==================

Fixed architecture:
    - 64 KB total SRAM
    - 8 banks
    - 8 KB per bank
    - INT8 operands
    - 8x8 systolic array

Banking policies:
    1. modulo
    2. split
    3. operand_aware
    4. xor

These policies are treated as fixed experimental configurations.
"""

# ------------------------------------------------------------
# Architecture constants
# ------------------------------------------------------------

ARRAY_SIZE = 8

NUM_BANKS = 8

BANK_SIZE_BYTES = 8 * 1024

TOTAL_SRAM_BYTES = (
    NUM_BANKS * BANK_SIZE_BYTES
)

BYTES_PER_INT8 = 1


# ------------------------------------------------------------
# First-pass physical placement
# ------------------------------------------------------------

# A occupies the lower part of SRAM.
A_BASE = 0

# B starts at 32 KB.
B_BASE = 32 * 1024


# ------------------------------------------------------------
# Experimental policies
# ------------------------------------------------------------

POLICIES = [
    "modulo",
    "split",
    "operand_aware",
    "xor",
]


# ------------------------------------------------------------
# Conventional modulo banking
# ------------------------------------------------------------

def bank_from_byte_address(address):
    """
    Conventional interleaved banking.

    Since operands are INT8, each matrix element occupies
    one byte.

        bank = byte_address % NUM_BANKS
    """

    return address % NUM_BANKS


def a_address(row, k, K):
    """
    Row-major address of A[row][k].

        A[row][k]
            ->
        A_BASE + (row*K + k)
    """

    return (
        A_BASE
        + (row * K + k) * BYTES_PER_INT8
    )


def b_address(k, col, N):
    """
    Row-major address of B[k][col].

        B[k][col]
            ->
        B_BASE + (k*N + col)
    """

    return (
        B_BASE
        + (k * N + col) * BYTES_PER_INT8
    )


def modulo_bank_A(row, k, K):
    """
    Conventional modulo banking for A.
    """

    address = a_address(
        row=row,
        k=k,
        K=K,
    )

    return bank_from_byte_address(
        address
    )


def modulo_bank_B(k, col, N):
    """
    Conventional modulo banking for B.
    """

    address = b_address(
        k=k,
        col=col,
        N=N,
    )

    return bank_from_byte_address(
        address
    )


# ------------------------------------------------------------
# Split banking
# ------------------------------------------------------------

def split_bank_A(row):
    """
    Static split banking.

    A uses banks:

        0, 1, 2, 3
    """

    return row % 4


def split_bank_B(col):
    """
    Static split banking.

    B uses banks:

        4, 5, 6, 7
    """

    return 4 + (col % 4)


# ------------------------------------------------------------
# Systolic-array-aware banking
# ------------------------------------------------------------

def operand_aware_bank_A(row):
    """
    Systolic-array-aware mapping for A.

        A row i -> bank i

    The mapping distributes the eight active
    systolic rows across all eight banks.
    """

    return row % NUM_BANKS


def operand_aware_bank_B(col):
    """
    Systolic-array-aware mapping for B.

        B column j -> bank (j + 4) % 8

    The offset separates the initial A and B
    spatial mappings.
    """

    return (
        col + 4
    ) % NUM_BANKS


# ------------------------------------------------------------
# XOR banking
# ------------------------------------------------------------

def xor_bank_A(row, k):
    """
    XOR-based banking for A.

        bank = row XOR k

    Both the systolic row and reduction dimension
    participate in bank selection.
    """

    return (
        row ^ k
    ) % NUM_BANKS


def xor_bank_B(k, col):
    """
    XOR-based banking for B.

        bank = column XOR k

    Both the systolic column and reduction dimension
    participate in bank selection.
    """

    return (
        col ^ k
    ) % NUM_BANKS


# ------------------------------------------------------------
# Unified bank-selection interface
# ------------------------------------------------------------

def get_bank(
    operand,
    row,
    index,
    K,
    N,
    policy,
):
    """
    Return the SRAM bank for one operand access.

    For A:

        operand = "A"
        row     = i
        index   = k

    For B:

        operand = "B"
        row     = k
        index   = j

    Parameters
    ----------
    operand : str
        "A" or "B"

    row : int
        Row/reduction coordinate depending on operand.

    index : int
        Column/reduction coordinate depending on operand.

    K : int
        GEMM reduction dimension.

    N : int
        GEMM output-column dimension.

    policy : str
        One of:

            modulo
            split
            operand_aware
            xor
    """

    # --------------------------------------------------------
    # Conventional modulo
    # --------------------------------------------------------

    if policy == "modulo":

        if operand == "A":

            return modulo_bank_A(
                row=row,
                k=index,
                K=K,
            )

        if operand == "B":

            return modulo_bank_B(
                k=row,
                col=index,
                N=N,
            )

    # --------------------------------------------------------
    # Static split
    # --------------------------------------------------------

    elif policy == "split":

        if operand == "A":

            return split_bank_A(
                row=row
            )

        if operand == "B":

            return split_bank_B(
                col=index
            )

    # --------------------------------------------------------
    # Systolic-array-aware
    # --------------------------------------------------------

    elif policy == "operand_aware":

        if operand == "A":

            return operand_aware_bank_A(
                row=row
            )

        if operand == "B":

            return operand_aware_bank_B(
                col=index
            )

    # --------------------------------------------------------
    # XOR
    # --------------------------------------------------------

    elif policy == "xor":

        if operand == "A":

            return xor_bank_A(
                row=row,
                k=index,
            )

        if operand == "B":

            return xor_bank_B(
                k=row,
                col=index,
            )

    # --------------------------------------------------------
    # Invalid configuration
    # --------------------------------------------------------

    raise ValueError(
        "Invalid operand/policy combination: "
        f"operand={operand}, "
        f"policy={policy}"
    )


# ------------------------------------------------------------
# Standalone sanity check
# ------------------------------------------------------------

if __name__ == "__main__":

    print()
    print("SRAM Banking Model")
    print("==================")
    print(
        f"Total SRAM : "
        f"{TOTAL_SRAM_BYTES // 1024} KB"
    )
    print(
        f"Number of banks : {NUM_BANKS}"
    )
    print(
        f"Bank size : "
        f"{BANK_SIZE_BYTES // 1024} KB"
    )
    print(
        f"Data type : INT8"
    )
    print()

    K = 128
    N = 8

    for policy in POLICIES:

        print(
            f"Policy: {policy}"
        )

        for i in range(ARRAY_SIZE):

            a_bank = get_bank(
                operand="A",
                row=i,
                index=0,
                K=K,
                N=N,
                policy=policy,
            )

            b_bank = get_bank(
                operand="B",
                row=0,
                index=i,
                K=K,
                N=N,
                policy=policy,
            )

            print(
                f"  A row {i} -> bank {a_bank} | "
                f"B col {i} -> bank {b_bank}"
            )

        print()
