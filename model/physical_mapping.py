"""Reference physical layouts for an 8-bank, 64 KiB SRAM.

Coordinates are local to the currently resident GEMM tile:
    A[row, k], shape M x K
    B[k, col], shape K x N

Returns (bank, local_byte_address).

This is a reference model, not a hardware-performance simulator.
"""

from dataclasses import dataclass
from math import ceil

NUM_BANKS = 8
BANK_SIZE_BYTES = 8192
TOTAL_SRAM_BYTES = NUM_BANKS * BANK_SIZE_BYTES

# Modulo layout keeps A and B in separate 32 KiB address regions.
A_BASE = 0
B_BASE = 32 * 1024

# For policies that distribute both operands across banks, reserve
# the lower 4 KiB of each bank for A and upper 4 KiB for B.
SHARED_BANK_OPERAND_SPLIT = BANK_SIZE_BYTES // 2

POLICIES = ("modulo", "split", "operand_aware", "xor")


@dataclass(frozen=True)
class PhysicalAddress:
    bank: int
    local_addr: int


def map_element(operand, row, index, K, N, policy):
    """Map one tile-local A[row,index] or B[row,index] element."""

    if operand not in ("A", "B"):
        raise ValueError("operand must be 'A' or 'B'")
    if policy not in POLICIES:
        raise ValueError(f"unknown policy: {policy}")
    if row < 0 or index < 0 or K < 1 or N < 1:
        raise ValueError("coordinates must be nonnegative; K and N positive")

    if operand == "A":
        # A[row, k]
        if index >= K:
            raise ValueError(f"A reduction index {index} outside K={K}")

        if policy == "modulo":
            address = A_BASE + row * K + index
            bank = address % NUM_BANKS
            local = address // NUM_BANKS

        elif policy == "split":
            # A occupies banks 0..3.
            bank = row % 4
            local = (row // 4) * K + index

        elif policy == "operand_aware":
            # One A row per bank; consecutive row groups are compacted.
            bank = row % NUM_BANKS
            local = (row // NUM_BANKS) * K + index

        else:  # xor
            # For a fixed bank, row_low uniquely determines k_low.
            bank = (row ^ index) % NUM_BANKS
            local = (
                ((row // 8) * ceil(K / 8) + (index // 8)) * 8
                + (row % 8)
            )

    else:
        # B[row, index] means B[k, col].
        k, col = row, index
        if col >= N:
            raise ValueError(f"B column {col} outside N={N}")

        if policy == "modulo":
            address = B_BASE + k * N + col
            bank = address % NUM_BANKS
            local = address // NUM_BANKS

        elif policy == "split":
            # B occupies banks 4..7.
            bank = 4 + (col % 4)
            local = k * ceil(N / 4) + (col // 4)

        elif policy == "operand_aware":
            # Each bank's B addresses start in its upper 4 KiB region.
            bank = (col + 4) % NUM_BANKS
            local = SHARED_BANK_OPERAND_SPLIT + (
                k * ceil(N / 8) + (col // 8)
            )

        else:  # xor
            bank = (col ^ k) % NUM_BANKS
            local = SHARED_BANK_OPERAND_SPLIT + (
                ((k // 8) * ceil(N / 8) + (col // 8)) * 8
                + (k % 8)
            )

    if not 0 <= bank < NUM_BANKS:
        raise AssertionError(f"invalid bank {bank}")
    if not 0 <= local < BANK_SIZE_BYTES:
        raise ValueError(
            f"{policy}: {operand}[{row},{index}] maps outside SRAM: "
            f"bank={bank}, local_addr={local}; "
            f"bank capacity is {BANK_SIZE_BYTES} bytes"
        )

    return PhysicalAddress(bank=bank, local_addr=local)


def enumerate_layout(M, K, N, policy):
    """Return all physical addresses for the resident A and B tiles."""

    if min(M, K, N) < 1:
        raise ValueError("M, K, and N must all be positive")

    result = {}
    for i in range(M):
        for k in range(K):
            result[("A", i, k)] = map_element("A", i, k, K, N, policy)

    for k in range(K):
        for j in range(N):
            result[("B", k, j)] = map_element("B", k, j, K, N, policy)

    return result


def validate_layout(M, K, N, policy):
    """Raise AssertionError if distinct elements alias physically."""

    layout = enumerate_layout(M, K, N, policy)
    seen = {}

    for logical, physical in layout.items():
        location = (physical.bank, physical.local_addr)
        if location in seen:
            raise AssertionError(
                f"physical alias under {policy}: {seen[location]} and "
                f"{logical} both map to bank={physical.bank}, "
                f"local_addr={physical.local_addr}"
            )
        seen[location] = logical

    occupancy = [0] * NUM_BANKS
    for physical in layout.values():
        occupancy[physical.bank] += 1

    return {
        "policy": policy,
        "elements": len(layout),
        "bank_occupancy": occupancy,
        "max_local_addr": max(p.local_addr for p in layout.values()),
    }
