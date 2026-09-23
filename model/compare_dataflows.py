"""
Compare OS and WS dataflows across the four fixed SRAM
banking organizations.

Experimental matrix:

    OS × modulo
    OS × split
    OS × operand_aware
    OS × xor

    WS × modulo
    WS × split
    WS × operand_aware
    WS × xor

This script measures SRAM request contention.

It deliberately does not modify the banking policies.
"""

import sys
from pathlib import Path

sys.path.append(
    str(Path(__file__).resolve().parent)
)

from banking_model import (
    POLICIES,
    get_bank,
)

from dataflow_model import (
    DATAFLOWS,
    generate_accesses,
)


def analyze_cycle(
    cycle,
    K,
    N,
    policy,
):
    """
    Count SRAM requests per bank for one cycle.
    """

    loads = [0] * 8

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

    total_requests = sum(loads)

    if total_requests == 0:

        service_cycles = 0
        stall_cycles = 0

    else:

        service_cycles = max(loads)

        stall_cycles = max(
            0,
            service_cycles - 1,
        )

    return {
        "loads": loads,
        "requests": total_requests,
        "service_cycles": service_cycles,
        "stall_cycles": stall_cycles,
    }


def analyze_configuration(
    dataflow,
    K,
    M=8,
    N=8,
    policy="modulo",
):
    """
    Analyze one dataflow/banking configuration.
    """

    trace = generate_accesses(
        dataflow=dataflow,
        K=K,
        M=M,
        N=N,
    )

    total_requests = 0
    total_service_cycles = 0
    total_stall_cycles = 0

    phase_stats = {}

    for cycle in trace:

        result = analyze_cycle(
            cycle=cycle,
            K=K,
            N=N,
            policy=policy,
        )

        total_requests += (
            result["requests"]
        )

        total_service_cycles += (
            result["service_cycles"]
        )

        total_stall_cycles += (
            result["stall_cycles"]
        )

        phase = cycle["phase"]

        if phase not in phase_stats:

            phase_stats[phase] = {
                "requests": 0,
                "service_cycles": 0,
                "stall_cycles": 0,
            }

        phase_stats[phase][
            "requests"
        ] += result["requests"]

        phase_stats[phase][
            "service_cycles"
        ] += result["service_cycles"]

        phase_stats[phase][
            "stall_cycles"
        ] += result["stall_cycles"]

    return {
        "dataflow": dataflow,
        "K": K,
        "M": M,
        "N": N,
        "policy": policy,
        "requests": total_requests,
        "service_cycles": total_service_cycles,
        "stall_cycles": total_stall_cycles,
        "phase_stats": phase_stats,
        "trace": trace,
    }


def print_summary(results):

    print()
    print(
        "OS / WS × SRAM BANKING COMPARISON"
    )
    print(
        "=" * 105
    )

    print(
        f"{'DF':<5}"
        f"{'K':>5}"
        f"{'Policy':>18}"
        f"{'Req':>8}"
        f"{'Service':>10}"
        f"{'Stall':>9}"
        f"{'WeightLd':>10}"
        f"{'Input':>9}"
    )

    print(
        "-" * 105
    )

    for result in results:

        phase_stats = result[
            "phase_stats"
        ]

        weight_stats = phase_stats.get(
            "weight_load",
            {},
        )

        input_stats = phase_stats.get(
            "input_stream",
            {},
        )

        print(
            f"{result['dataflow']:<5}"
            f"{result['K']:>5}"
            f"{result['policy']:>18}"
            f"{result['requests']:>8}"
            f"{result['service_cycles']:>10}"
            f"{result['stall_cycles']:>9}"
            f"{weight_stats.get('stall_cycles', 0):>10}"
            f"{input_stats.get('stall_cycles', 0):>9}"
        )


def print_phase_details(result):

    print()
    print(
        f"Dataflow: {result['dataflow']}"
    )
    print(
        f"K={result['K']} "
        f"M={result['M']} "
        f"N={result['N']}"
    )
    print(
        f"Banking: {result['policy']}"
    )

    print()
    print(
        "Phase breakdown:"
    )

    for phase, stats in result[
        "phase_stats"
    ].items():

        print(
            f"  {phase:15s} "
            f"requests="
            f"{stats['requests']:5d} "
            f"service="
            f"{stats['service_cycles']:5d} "
            f"stall="
            f"{stats['stall_cycles']:5d}"
        )


def main():

    results = []

    for K in [
        8,
        32,
        64,
        128,
        256,
    ]:

        for dataflow in DATAFLOWS:

            for policy in POLICIES:

                result = analyze_configuration(
                    dataflow=dataflow,
                    K=K,
                    M=8,
                    N=8,
                    policy=policy,
                )

                results.append(
                    result
                )

    print_summary(
        results
    )

    print()
    print(
        "=" * 105
    )
    print(
        "Detailed sanity check: K=8"
    )
    print(
        "=" * 105
    )

    for dataflow in DATAFLOWS:

        result = analyze_configuration(
            dataflow=dataflow,
            K=8,
            M=8,
            N=8,
            policy="split",
        )

        print_phase_details(
            result
        )


if __name__ == "__main__":
    main()
