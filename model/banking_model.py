"""
Simple SRAM banking model.

Architecture:

    Total SRAM : 64 KB
    Banks      : 8
    Bank size  : 8 KB

The first version supports three simple banking policies:

    modulo
    row
    column

This is an analytical model only.
"""

NUM_BANKS = 8
BANK_SIZE_BYTES = 8 * 1024
TOTAL_SRAM_BYTES = NUM_BANKS * BANK_SIZE_BYTES


def modulo_bank(address):
    """
    Standard modulo banking.

    Bank is selected from the word address.
    """
    word_address = address // 4
    return word_address % NUM_BANKS


def row_bank(row):
    """
    Bank based on matrix row.
    """
    return row % NUM_BANKS


def column_bank(column):
    """
    Bank based on matrix column.
    """
    return column % NUM_BANKS


def get_bank(
    address,
    policy="modulo",
    row=0,
    column=0
):
    """
    Return the bank selected by a banking policy.
    """

    if policy == "modulo":
        return modulo_bank(address)

    elif policy == "row":
        return row_bank(row)

    elif policy == "column":
        return column_bank(column)

    else:
        raise ValueError(
            f"Unknown banking policy: {policy}"
        )


def print_banking_test():

    print("=" * 60)
    print("SRAM BANKING MODEL")
    print("=" * 60)

    print(
        f"Total SRAM : "
        f"{TOTAL_SRAM_BYTES / 1024:.0f} KB"
    )

    print(
        f"Number banks: "
        f"{NUM_BANKS}"
    )

    print(
        f"Bank size  : "
        f"{BANK_SIZE_BYTES / 1024:.0f} KB"
    )

    print()

    addresses = [
        0,
        4,
        8,
        12,
        16,
        20,
        24,
        28,
        32,
    ]

    print("Modulo banking:")

    for address in addresses:

        bank = modulo_bank(address)

        print(
            f"Address {address:3d} "
            f"-> Bank {bank}"
        )

    print()

    print("Row banking:")

    for row in range(8):

        print(
            f"Row {row} -> Bank "
            f"{row_bank(row)}"
        )

    print()

    print("Column banking:")

    for column in range(8):

        print(
            f"Column {column} -> Bank "
            f"{column_bank(column)}"
        )


if __name__ == "__main__":
    print_banking_test()
