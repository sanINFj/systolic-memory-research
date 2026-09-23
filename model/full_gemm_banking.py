"""
Full-GEMM analytical SRAM banking model.

Compute architecture:

    8x8 systolic array
    INT8 operands
    INT8 x INT8 -> INT32

Memory architecture:

    64 KB SRAM
    8 banks
    8 KB per bank

Bank assumption:

    One read per bank per cycle.

For every systolic injection cycle:

    service_cycles = maximum requests to any bank

    ideal_service_cycles =
        ceil(total_requests / 8)

    stall_cycles =
        service_cycles - 1

This is an analytical memory-service model.
It is not yet the complete accelerator runtime.
"""


import csv
import math
import os

from access_generator import generate_accesses
from banking_model import (
    NUM_BANKS,
    BANK_SIZE_BYTES,
    A_BASE,
    B_BASE,
)


ARRAY_SIZE = 8


POLICIES = [
    "modulo",
    "split",
    "operand_aware",
]


# GEMM workloads:
#
# M = output rows
# K = reduction dimension
# N = output columns

WORKLOADS = {

    "square_32":
        (32, 32, 32),

    "square_64":
        (64, 64, 64),

    "square_128":
        (128, 128, 128),

    "square_256":
        (256, 256, 256),

    "input_heavy":
        (256, 64, 64),

    "weight_heavy":
        (64, 64, 256),

    "k_heavy":
        (64, 256, 64),

    "rectangular_1":
        (128, 512, 128),

    "rectangular_2":
        (512, 128, 128),
}


# Deliberately non-8-aligned workloads.
#
# These exercise partial edge tiles.

STRESS_WORKLOADS = {

    "edge_70x70x64":
        (70, 64, 70),

    "edge_13x29x17":
        (13, 17, 29),
}


def modulo_bank(
    operand,
    row,
    col,
    K,
    N,
):
    """
    Conventional byte-address modulo banking.

    A[row][k]:

        address = A_BASE + row*K + k

    B[k][col]:

        address = B_BASE + k*N + col

    Because operands are INT8, one element occupies
    one byte.
    """

    if operand == "A":

        address = (
            A_BASE
            + row * K
            + col
        )

    elif operand == "B":

        address = (
            B_BASE
            + row * N
            + col
        )

    else:

        raise ValueError(
            f"Unknown operand: {operand}"
        )

    return address % NUM_BANKS


def split_bank(
    operand,
    row,
    col,
):
    """
    Split banking baseline.

        A -> banks 0..3
        B -> banks 4..7
    """

    if operand == "A":

        return row % 4

    if operand == "B":

        return 4 + (col % 4)

    raise ValueError(
        f"Unknown operand: {operand}"
    )


def operand_aware_bank(
    operand,
    row,
    col,
):
    """
    Proposed systolic-array-aware mapping.

        A row i -> bank i % 8

        B column j -> bank (j + 4) % 8
    """

    if operand == "A":

        return row % NUM_BANKS

    if operand == "B":

        return (col + 4) % NUM_BANKS

    raise ValueError(
        f"Unknown operand: {operand}"
    )


def get_bank(
    operand,
    row,
    col,
    K,
    N,
    policy,
):
    """
    Select SRAM bank for one global matrix element.
    """

    if policy == "modulo":

        return modulo_bank(
            operand,
            row,
            col,
            K,
            N,
        )

    if policy == "split":

        return split_bank(
            operand,
            row,
            col,
        )

    if policy == "operand_aware":

        return operand_aware_bank(
            operand,
            row,
            col,
        )

    raise ValueError(
        f"Unknown policy: {policy}"
    )


def analyze_output_tile(
    M,
    K,
    N,
    m0,
    n0,
    policy,
):
    """
    Analyze one output tile.

    m0:
        global starting row

    n0:
        global starting column
    """

    tile_M = min(
        ARRAY_SIZE,
        M - m0,
    )

    tile_N = min(
        ARRAY_SIZE,
        N - n0,
    )

    accesses = generate_accesses(
        K=K,
        M=tile_M,
        N=tile_N,
    )

    total_requests = 0
    total_service_cycles = 0
    total_ideal_service_cycles = 0
    total_stall_cycles = 0

    max_bank_load = 0

    for cycle in accesses:

        bank_loads = [
            0
            for _ in range(NUM_BANKS)
        ]

        # -------------------------
        # A accesses
        # -------------------------

        for local_row, k in cycle["A"]:

            global_row = (
                m0 + local_row
            )

            bank = get_bank(
                operand="A",
                row=global_row,
                col=k,
                K=K,
                N=N,
                policy=policy,
            )

            bank_loads[bank] += 1

        # -------------------------
        # B accesses
        # -------------------------

        for k, local_col in cycle["B"]:

            global_col = (
                n0 + local_col
            )

            bank = get_bank(
                operand="B",
                row=k,
                col=global_col,
                K=K,
                N=N,
                policy=policy,
            )

            bank_loads[bank] += 1

        requests = sum(
            bank_loads
        )

        if requests == 0:
            continue

        service_cycles = max(
            bank_loads
        )

        ideal_service_cycles = math.ceil(
            requests / NUM_BANKS
        )

        stall_cycles = max(
            0,
            service_cycles - 1,
        )

        total_requests += requests

        total_service_cycles += (
            service_cycles
        )

        total_ideal_service_cycles += (
            ideal_service_cycles
        )

        total_stall_cycles += (
            stall_cycles
        )

        max_bank_load = max(
            max_bank_load,
            service_cycles,
        )

    return {

        "tile_M":
            tile_M,

        "tile_N":
            tile_N,

        "requests":
            total_requests,

        "service_cycles":
            total_service_cycles,

        "ideal_service_cycles":
            total_ideal_service_cycles,

        "stall_cycles":
            total_stall_cycles,

        "excess_stall_cycles":
            (
                total_service_cycles
                - total_ideal_service_cycles
            ),

        "max_bank_load":
            max_bank_load,
    }


def analyze_gemm(
    M,
    K,
    N,
    policy,
):
    """
    Analyze complete MxK @ KxN GEMM.
    """

    total_requests = 0
    total_service_cycles = 0
    total_ideal_service_cycles = 0
    total_stall_cycles = 0
    max_bank_load = 0

    tile_count = 0

    tile_results = []

    for m0 in range(
        0,
        M,
        ARRAY_SIZE,
    ):

        for n0 in range(
            0,
            N,
            ARRAY_SIZE,
        ):

            result = analyze_output_tile(
                M=M,
                K=K,
                N=N,
                m0=m0,
                n0=n0,
                policy=policy,
            )

            tile_results.append(
                {
                    "m0": m0,
                    "n0": n0,
                    **result,
                }
            )

            tile_count += 1

            total_requests += (
                result["requests"]
            )

            total_service_cycles += (
                result["service_cycles"]
            )

            total_ideal_service_cycles += (
                result[
                    "ideal_service_cycles"
                ]
            )

            total_stall_cycles += (
                result["stall_cycles"]
            )

            max_bank_load = max(
                max_bank_load,
                result["max_bank_load"],
            )

    excess_stall_cycles = (
        total_service_cycles
        - total_ideal_service_cycles
    )

    return {

        "M": M,
        "K": K,
        "N": N,

        "policy": policy,

        "output_tiles":
            tile_count,

        "requests":
            total_requests,

        "service_cycles":
            total_service_cycles,

        "ideal_service_cycles":
            total_ideal_service_cycles,

        "stall_cycles":
            total_stall_cycles,

        "excess_stall_cycles":
            excess_stall_cycles,

        "max_bank_load":
            max_bank_load,

        "tile_results":
            tile_results,
    }


def print_result(result):

    print(
        f"{result['policy']:15s} "
        f"requests="
        f"{result['requests']:9d} "
        f"service="
        f"{result['service_cycles']:9d} "
        f"ideal="
        f"{result['ideal_service_cycles']:9d} "
        f"stall="
        f"{result['stall_cycles']:9d} "
        f"excess="
        f"{result['excess_stall_cycles']:9d} "
        f"maxload="
        f"{result['max_bank_load']:2d}"
    )


def run_suite(
    workloads,
    title,
):
    """
    Run all policies over all workloads.
    """

    print()
    print("=" * 105)
    print(title)
    print("=" * 105)

    all_results = []

    for name, dimensions in workloads.items():

        M, K, N = dimensions

        print()
        print(
            f"{name}: "
            f"M={M}, K={K}, N={N}"
        )

        print(
            f"{'Policy':15s} "
            f"{'Requests':>9s} "
            f"{'Service':>9s} "
            f"{'Ideal':>9s} "
            f"{'Stalls':>9s} "
            f"{'Excess':>9s} "
            f"{'MaxLoad':>7s}"
        )

        print("-" * 105)

        for policy in POLICIES:

            result = analyze_gemm(
                M=M,
                K=K,
                N=N,
                policy=policy,
            )

            print_result(
                result
            )

            all_results.append(
                {
                    "suite":
                        title,

                    "workload":
                        name,

                    "M":
                        M,

                    "K":
                        K,

                    "N":
                        N,

                    "policy":
                        policy,

                    "output_tiles":
                        result[
                            "output_tiles"
                        ],

                    "requests":
                        result[
                            "requests"
                        ],

                    "service_cycles":
                        result[
                            "service_cycles"
                        ],

                    "ideal_service_cycles":
                        result[
                            "ideal_service_cycles"
                        ],

                    "stall_cycles":
                        result[
                            "stall_cycles"
                        ],

                    "excess_stall_cycles":
                        result[
                            "excess_stall_cycles"
                        ],

                    "max_bank_load":
                        result[
                            "max_bank_load"
                        ],
                }
            )

    return all_results


def save_csv(results):

    os.makedirs(
        "results",
        exist_ok=True,
    )

    filename = (
        "results/"
        "full_gemm_banking_results.csv"
    )

    fieldnames = [

        "suite",

        "workload",

        "M",
        "K",
        "N",

        "policy",

        "output_tiles",

        "requests",

        "service_cycles",

        "ideal_service_cycles",

        "stall_cycles",

        "excess_stall_cycles",

        "max_bank_load",
    ]

    with open(
        filename,
        "w",
        newline="",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        writer.writerows(
            results
        )

    print()
    print(
        f"Results saved to:"
    )
    print(
        f"  {filename}"
    )


def main():

    print()
    print(
        "Full GEMM SRAM Banking Model"
    )
    print(
        "============================"
    )

    print(
        f"SRAM: "
        f"{NUM_BANKS} banks x "
        f"{BANK_SIZE_BYTES // 1024} KB"
    )

    print(
        "Bank service: "
        "1 read/bank/cycle"
    )

    main_results = run_suite(
        WORKLOADS,
        "MAIN WORKLOADS",
    )

    stress_results = run_suite(
        STRESS_WORKLOADS,
        "EDGE / STRESS WORKLOADS",
    )

    save_csv(
        main_results
        + stress_results
    )


if __name__ == "__main__":
    main()
