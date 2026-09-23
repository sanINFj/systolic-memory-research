"""
Dataflow Execution Model
========================

Compare Output-Stationary (OS) and Weight-Stationary (WS)
execution organizations while keeping fixed:

    - 8x8 compute array
    - INT8 operands
    - 8 SRAM banks
    - 1 read per bank per cycle
    - FIFO bank service
    - four fixed banking policies

This is an architectural memory/execution model.

It is not the final RTL implementation.
"""

import sys
from pathlib import Path
from collections import deque


sys.path.append(
    str(Path(__file__).resolve().parent)
)

from banking_model import (
    NUM_BANKS,
    POLICIES,
    get_bank,
)

from dataflow_model import (
    generate_os_accesses,
)


ARRAY_SIZE = 8


# ============================================================
# Request creation
# ============================================================

def make_request(
    request_id,
    operand,
    row,
    index,
    arrival_cycle,
    bank,
):
    return {
        "id": request_id,
        "operand": operand,
        "row": row,
        "index": index,
        "arrival_cycle": arrival_cycle,
        "bank": bank,
        "service_cycle": None,
        "wait_cycles": None,
        "latency": None,
    }


# ============================================================
# FIFO bank service
# ============================================================

class FIFOBankService:

    def __init__(self):

        self.queues = [
            deque()
            for _ in range(NUM_BANKS)
        ]

        self.served_requests = []

        self.bank_busy_cycles = [
            0
            for _ in range(NUM_BANKS)
        ]

        self.max_queue_depth = [
            0
            for _ in range(NUM_BANKS)
        ]

    def enqueue(self, request):

        bank = request["bank"]

        self.queues[bank].append(
            request
        )

        depth = len(
            self.queues[bank]
        )

        if depth > self.max_queue_depth[bank]:
            self.max_queue_depth[bank] = depth

    def service(self, cycle):

        served = []

        for bank in range(NUM_BANKS):

            if not self.queues[bank]:
                continue

            request = self.queues[bank].popleft()

            request["service_cycle"] = cycle

            request["wait_cycles"] = (
                cycle
                - request["arrival_cycle"]
            )

            request["latency"] = (
                request["wait_cycles"]
                + 1
            )

            self.served_requests.append(
                request
            )

            self.bank_busy_cycles[bank] += 1

            served.append(
                request
            )

        return served

    def empty(self):

        return all(
            len(queue) == 0
            for queue in self.queues
        )

    def pending_count(self):

        return sum(
            len(queue)
            for queue in self.queues
        )


# ============================================================
# OS request generation
# ============================================================

def generate_os_requests(
    cycle,
    K,
    M,
    N,
    policy,
    request_id_start,
):
    """
    Generate all A/B requests belonging to one OS
    systolic injection.
    """

    requests = []

    request_id = request_id_start

    # --------------------------------------------------------
    # A requests
    # --------------------------------------------------------

    for row in range(M):

        k = cycle - row

        if 0 <= k < K:

            bank = get_bank(
                operand="A",
                row=row,
                index=k,
                K=K,
                N=N,
                policy=policy,
            )

            requests.append(
                make_request(
                    request_id=request_id,
                    operand="A",
                    row=row,
                    index=k,
                    arrival_cycle=cycle,
                    bank=bank,
                )
            )

            request_id += 1

    # --------------------------------------------------------
    # B requests
    # --------------------------------------------------------

    for col in range(N):

        k = cycle - col

        if 0 <= k < K:

            bank = get_bank(
                operand="B",
                row=k,
                index=col,
                K=K,
                N=N,
                policy=policy,
            )

            requests.append(
                make_request(
                    request_id=request_id,
                    operand="B",
                    row=k,
                    index=col,
                    arrival_cycle=cycle,
                    bank=bank,
                )
            )

            request_id += 1

    return requests


# ============================================================
# WS request generation
# ============================================================

def generate_ws_weight_requests(
    k_base,
    K,
    M,
    N,
    policy,
    request_id_start,
    arrival_cycle,
):
    """
    Generate B/weight requests for one WS K tile.
    """

    requests = []

    request_id = request_id_start

    k_end = min(
        k_base + ARRAY_SIZE,
        K,
    )

    for k in range(k_base, k_end):

        for col in range(N):

            bank = get_bank(
                operand="B",
                row=k,
                index=col,
                K=K,
                N=N,
                policy=policy,
            )

            requests.append(
                make_request(
                    request_id=request_id,
                    operand="B",
                    row=k,
                    index=col,
                    arrival_cycle=arrival_cycle,
                    bank=bank,
                )
            )

            request_id += 1

    return requests


def generate_ws_input_requests(
    k,
    K,
    M,
    N,
    policy,
    request_id_start,
    arrival_cycle,
):
    """
    Generate A requests for one WS input slice.
    """

    requests = []

    request_id = request_id_start

    for row in range(M):

        bank = get_bank(
            operand="A",
            row=row,
            index=k,
            K=K,
            N=N,
            policy=policy,
        )

        requests.append(
            make_request(
                request_id=request_id,
                operand="A",
                row=row,
                index=k,
                arrival_cycle=arrival_cycle,
                bank=bank,
            )
        )

        request_id += 1

    return requests


# ============================================================
# OS simulation
# ============================================================

def simulate_os(
    K,
    M=ARRAY_SIZE,
    N=ARRAY_SIZE,
    policy="modulo",
):
    """
    Simulate OS execution.

    Important timing rule:

        One injection is introduced exactly once.

        Its requests enter the bank FIFOs.

        The simulator waits until all requests belonging
        to that injection have been serviced.

        Only then does the next injection begin.

    This is a conservative whole-injection backpressure model.
    """

    access_trace = generate_os_accesses(
        K=K,
        M=M,
        N=N,
    )

    service = FIFOBankService()

    request_id = 0

    injection_pointer = 0

    current_requests = None

    total_requests = 0

    compute_cycles = 0
    stall_cycles = 0

    cycle = 0

    trace = []

    while injection_pointer < len(access_trace):

        # ----------------------------------------------------
        # IMPORTANT:
        #
        # Only enqueue the current injection ONCE.
        #
        # This fixes the infinite-loop bug.
        # ----------------------------------------------------

        if current_requests is None:

            nominal = access_trace[
                injection_pointer
            ]

            current_requests = (
                generate_os_requests(
                    cycle=nominal["cycle"],
                    K=K,
                    M=M,
                    N=N,
                    policy=policy,
                    request_id_start=request_id,
                )
            )

            request_id += len(
                current_requests
            )

            for request in current_requests:

                # Arrival happens when this injection is
                # actually introduced to the memory system.
                request["arrival_cycle"] = cycle

                service.enqueue(
                    request
                )

            total_requests += len(
                current_requests
            )

        # ----------------------------------------------------
        # Service one request per bank.
        # ----------------------------------------------------

        served = service.service(
            cycle
        )

        # ----------------------------------------------------
        # Check whether every operand required by the
        # current injection has arrived.
        # ----------------------------------------------------

        ready = all(
            request["service_cycle"] is not None
            for request in current_requests
        )

        if ready:

            compute_cycles += 1

            trace.append(
                {
                    "cycle": cycle,
                    "injection":
                        injection_pointer,
                    "served": len(served),
                    "pending":
                        service.pending_count(),
                    "ready": True,
                }
            )

            injection_pointer += 1

            # Allow the next injection to be generated
            # on the next cycle.
            current_requests = None

        else:

            stall_cycles += 1

            trace.append(
                {
                    "cycle": cycle,
                    "injection":
                        injection_pointer,
                    "served": len(served),
                    "pending":
                        service.pending_count(),
                    "ready": False,
                }
            )

        cycle += 1

        if cycle > 10000000:
            raise RuntimeError(
                "OS simulation exceeded safety limit"
            )

    # --------------------------------------------------------
    # Memory should normally already be empty because we
    # wait for every injection to complete.
    # --------------------------------------------------------

    while not service.empty():

        service.service(
            cycle
        )

        cycle += 1

    total_wait = sum(
        request["wait_cycles"]
        for request in service.served_requests
    )

    max_wait = max(
        (
            request["wait_cycles"]
            for request in service.served_requests
        ),
        default=0,
    )

    return {
        "dataflow": "OS",
        "K": K,
        "M": M,
        "N": N,
        "policy": policy,
        "requests": total_requests,
        "execution_cycles": cycle,
        "compute_cycles": compute_cycles,
        "stall_cycles": stall_cycles,
        "average_wait": (
            total_wait / total_requests
            if total_requests
            else 0
        ),
        "maximum_wait": max_wait,
        "bank_busy_cycles": sum(
            service.bank_busy_cycles
        ),
        "max_queue_depth": max(
            service.max_queue_depth,
            default=0,
        ),
        "requests_detail":
            service.served_requests,
        "trace": trace,
    }


# ============================================================
# WS simulation
# ============================================================

def simulate_ws(
    K,
    M=ARRAY_SIZE,
    N=ARRAY_SIZE,
    policy="modulo",
):
    """
    Conservative WS execution model.

    For every K tile:

        1. Load B/weights.
        2. Keep the weights stationary.
        3. Stream A values.
        4. Advance to the next K tile.

    B is therefore loaded once per K tile.
    """

    service = FIFOBankService()

    request_id = 0
    cycle = 0

    total_requests = 0
    weight_requests_total = 0
    input_requests_total = 0

    compute_cycles = 0
    stall_cycles = 0

    weight_load_cycles = 0
    input_stream_cycles = 0

    # --------------------------------------------------------
    # Process K in 8-element tiles.
    # --------------------------------------------------------

    for k_base in range(
        0,
        K,
        ARRAY_SIZE,
    ):

        # ====================================================
        # WEIGHT LOAD
        # ====================================================

        weight_requests = (
            generate_ws_weight_requests(
                k_base=k_base,
                K=K,
                M=M,
                N=N,
                policy=policy,
                request_id_start=request_id,
                arrival_cycle=cycle,
            )
        )

        request_id += len(
            weight_requests
        )

        total_requests += len(
            weight_requests
        )

        weight_requests_total += len(
            weight_requests
        )

        for request in weight_requests:

            service.enqueue(
                request
            )

        # Wait until all weights are available.

        while True:

            service.service(
                cycle
            )

            weight_load_cycles += 1

            ready = all(
                request["service_cycle"] is not None
                for request in weight_requests
            )

            if ready:
                break

            cycle += 1

        cycle += 1

        # ====================================================
        # INPUT STREAM
        # ====================================================

        k_end = min(
            k_base + ARRAY_SIZE,
            K,
        )

        for k in range(
            k_base,
            k_end,
        ):

            input_requests = (
                generate_ws_input_requests(
                    k=k,
                    K=K,
                    M=M,
                    N=N,
                    policy=policy,
                    request_id_start=request_id,
                    arrival_cycle=cycle,
                )
            )

            request_id += len(
                input_requests
            )

            total_requests += len(
                input_requests
            )

            input_requests_total += len(
                input_requests
            )

            for request in input_requests:

                service.enqueue(
                    request
                )

            # Wait until all A operands for this
            # compute slice are available.

            while True:

                service.service(
                    cycle
                )

                input_stream_cycles += 1

                ready = all(
                    request["service_cycle"] is not None
                    for request in input_requests
                )

                if ready:
                    break

                stall_cycles += 1

                cycle += 1

            # One compute step occurs once the entire
            # A slice is available.

            compute_cycles += 1

            cycle += 1

    total_wait = sum(
        request["wait_cycles"]
        for request in service.served_requests
    )

    max_wait = max(
        (
            request["wait_cycles"]
            for request in service.served_requests
        ),
        default=0,
    )

    return {
        "dataflow": "WS",
        "K": K,
        "M": M,
        "N": N,
        "policy": policy,
        "requests": total_requests,
        "weight_requests": weight_requests_total,
        "input_requests": input_requests_total,
        "execution_cycles": cycle,
        "compute_cycles": compute_cycles,
        "stall_cycles": stall_cycles,
        "weight_load_cycles": weight_load_cycles,
        "input_stream_cycles": input_stream_cycles,
        "average_wait": (
            total_wait / total_requests
            if total_requests
            else 0
        ),
        "maximum_wait": max_wait,
        "bank_busy_cycles": sum(
            service.bank_busy_cycles
        ),
        "max_queue_depth": max(
            service.max_queue_depth,
            default=0,
        ),
        "requests_detail":
            service.served_requests,
    }


# ============================================================
# Printing
# ============================================================

def print_result(result):

    print(
        f"{result['dataflow']:3s} "
        f"{result['K']:4d} "
        f"{result['policy']:15s} "
        f"{result['requests']:6d} "
        f"{result['execution_cycles']:8d} "
        f"{result['compute_cycles']:7d} "
        f"{result['stall_cycles']:7d} "
        f"{result['average_wait']:8.2f} "
        f"{result['maximum_wait']:8d} "
        f"{result['max_queue_depth']:7d}"
    )


# ============================================================
# Main experiment
# ============================================================

def run_comparison():

    print()
    print(
        "DATAFLOW EXECUTION MODEL"
    )
    print(
        "=" * 105
    )

    print(
        f"{'DF':3s} "
        f"{'K':4s} "
        f"{'Policy':15s} "
        f"{'Req':>6s} "
        f"{'Exec':>8s} "
        f"{'Compute':>7s} "
        f"{'Stall':>7s} "
        f"{'AvgWait':>8s} "
        f"{'MaxWait':>8s} "
        f"{'MaxQ':>7s}"
    )

    print(
        "-" * 105
    )

    for K in [
        8,
        32,
        64,
        128,
        256,
    ]:

        for policy in POLICIES:

            os_result = simulate_os(
                K=K,
                M=8,
                N=8,
                policy=policy,
            )

            print_result(
                os_result
            )

            ws_result = simulate_ws(
                K=K,
                M=8,
                N=8,
                policy=policy,
            )

            print_result(
                ws_result
            )

        print()


if __name__ == "__main__":

    run_comparison()
