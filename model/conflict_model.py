"""
Bank-conflict model.

Takes systolic-array memory accesses and determines
whether multiple requests target the same SRAM bank
during the same cycle.
"""

from banking_model import (
    get_bank,
    NUM_BANKS
)

from access_generator import (
    generate_accesses
)


def count_bank_conflicts(
    accesses,
    policy
):
    """
    Count bank conflicts for one complete access trace.

    A conflict occurs when more than one request targets
    the same bank during the same cycle.
    """

    total_conflicts = 0
    total_requests = 0

    cycle_results = []

    for entry in accesses:

        bank_counts = [
            0
            for _ in range(NUM_BANKS)
        ]

        requests = []

        # --------------------------------------------
        # A requests
        # --------------------------------------------

        for row, column in entry["A"]:

            # Simple linear address for A.
            address = (
                (row * 1024)
                + (column * 4)
            )

            bank = get_bank(
                address,
                policy=policy,
                row=row,
                column=column
            )

            bank_counts[bank] += 1
            requests.append(bank)

        # --------------------------------------------
        # B requests
        # --------------------------------------------

        for row, column in entry["B"]:

            # Simple linear address for B.
            address = (
                (row * 1024)
                + (column * 4)
            )

            bank = get_bank(
                address,
                policy=policy,
                row=row,
                column=column
            )

            bank_counts[bank] += 1
            requests.append(bank)

        # --------------------------------------------
        # Count conflicts
        # --------------------------------------------

        cycle_conflicts = 0

        for count in bank_counts:

            if count > 1:

                cycle_conflicts += (
                    count - 1
                )

        total_conflicts += cycle_conflicts
        total_requests += len(requests)

        cycle_results.append({
            "cycle": entry["cycle"],
            "bank_counts": bank_counts,
            "conflicts": cycle_conflicts
        })

    return {
        "policy": policy,
        "total_conflicts": total_conflicts,
        "total_requests": total_requests,
        "cycles": cycle_results
    }


def print_conflict_analysis():

    K = 8

    accesses = generate_accesses(K)

    print("=" * 70)
    print("BANK CONFLICT ANALYSIS")
    print("=" * 70)

    print(
        f"Array: 8x8"
    )

    print(
        f"K: {K}"
    )

    print()

    for policy in [
        "modulo",
        "row",
        "column"
    ]:

        result = count_bank_conflicts(
            accesses,
            policy
        )

        print(
            f"Policy: {policy}"
        )

        print(
            f"  Requests : "
            f"{result['total_requests']}"
        )

        print(
            f"  Conflicts: "
            f"{result['total_conflicts']}"
        )

        print()


if __name__ == "__main__":
    print_conflict_analysis()
