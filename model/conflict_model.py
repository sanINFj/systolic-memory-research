"""
Bank-service-latency model.

Assumption:

    Each SRAM bank can service one read per cycle.

For every injection cycle:

    bank_load[b] =
        number of requests assigned to bank b

    service_cycles =
        max(bank_load)

    stall_cycles =
        service_cycles - 1

The ideal lower bound is:

    ceil(total_requests / NUM_BANKS)

This model measures memory-service contention only.
It does not yet model the complete accelerator pipeline.
"""


import math

from access_generator import generate_accesses
from banking_model import (
    NUM_BANKS,
    POLICIES,
    get_bank,
)


def bank_loads_for_cycle(
    cycle,
    K,
    N,
    policy,
):
    """
    Return request count for every SRAM bank.
    """

    loads = [
        0
        for _ in range(NUM_BANKS)
    ]

    # -------------------------
    # A requests
    # -------------------------

    for row, k in cycle["A"]:

        bank = get_bank(
            operand="A",
            row=row,
            index=k,
            K=K,
            N=N,
            policy=policy,
        )

        loads[bank] += 1

    # -------------------------
    # B requests
    # -------------------------

    for k, col in cycle["B"]:

        bank = get_bank(
            operand="B",
            row=k,
            index=col,
            K=K,
            N=N,
            policy=policy,
        )

        loads[bank] += 1

    return loads


def analyze_cycle(
    cycle,
    K,
    N,
    policy,
):
    """
    Analyze one injection cycle.
    """

    loads = bank_loads_for_cycle(
        cycle=cycle,
        K=K,
        N=N,
        policy=policy,
    )

    total_requests = sum(loads)

    if total_requests == 0:

        service_cycles = 0
        stall_cycles = 0
        minimum_service_cycles = 0
        minimum_stall_cycles = 0

    else:

        service_cycles = max(loads)

        stall_cycles = max(
            0,
            service_cycles - 1,
        )

        minimum_service_cycles = math.ceil(
            total_requests / NUM_BANKS
        )

        minimum_stall_cycles = max(
            0,
            minimum_service_cycles - 1,
        )

    return {
        "cycle": cycle["cycle"],
        "loads": loads,
        "requests": total_requests,
        "service_cycles": service_cycles,
        "stall_cycles": stall_cycles,
        "minimum_service_cycles":
            minimum_service_cycles,
        "minimum_stall_cycles":
            minimum_stall_cycles,
    }


def analyze_policy(
    K,
    N=8,
    M=8,
    policy="modulo",
):
    """
    Analyze one complete output tile.
    """

    access_trace = generate_accesses(
        K=K,
        M=M,
        N=N,
    )

    cycle_results = []

    total_requests = 0
    total_service_cycles = 0
    total_stall_cycles = 0
    total_minimum_service_cycles = 0
    total_minimum_stall_cycles = 0

    for cycle in access_trace:

        result = analyze_cycle(
            cycle=cycle,
            K=K,
            N=N,
            policy=policy,
        )

        cycle_results.append(result)

        total_requests += (
            result["requests"]
        )

        total_service_cycles += (
            result["service_cycles"]
        )

        total_stall_cycles += (
            result["stall_cycles"]
        )

        total_minimum_service_cycles += (
            result["minimum_service_cycles"]
        )

        total_minimum_stall_cycles += (
            result["minimum_stall_cycles"]
        )

    return {
        "K": K,
        "M": M,
        "N": N,
        "policy": policy,

        "requests":
            total_requests,

        "service_cycles":
            total_service_cycles,

        "stall_cycles":
            total_stall_cycles,

        "minimum_service_cycles":
            total_minimum_service_cycles,

        "minimum_stall_cycles":
            total_minimum_stall_cycles,

        "excess_stall_cycles":
            (
                total_stall_cycles
                - total_minimum_stall_cycles
            ),

        "cycles":
            cycle_results,
    }


if __name__ == "__main__":

    print(
        "Bank Service-Latency Model"
    )
    print(
        "=========================="
    )

    for K in [
        8,
        32,
        64,
        128,
        256,
    ]:

        print()
        print(f"K = {K}")

        for policy in POLICIES:

            result = analyze_policy(
                K=K,
                M=8,
                N=8,
                policy=policy,
            )

            print(
                f"{policy:15s} "
                f"requests="
                f"{result['requests']:5d} "
                f"service="
                f"{result['service_cycles']:5d} "
                f"stall="
                f"{result['stall_cycles']:5d} "
                f"minimum="
                f"{result['minimum_stall_cycles']:5d} "
                f"excess="
                f"{result['excess_stall_cycles']:5d}"
            )
