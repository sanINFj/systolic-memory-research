"""
Cycle-Level FIFO SRAM Bank-Service Model
========================================

Fixed architecture:
    - 64 KB total SRAM
    - 8 banks
    - 8 KB per bank
    - 8x8 systolic array
    - INT8 operands
    - 1 read per bank per cycle

This model explicitly simulates:

    1. Request arrival
    2. Bank mapping
    3. Per-bank FIFO queues
    4. One request served per bank per cycle
    5. Request waiting time

Arbitration:
    FIFO within each bank.

The research variable is SRAM banking organization,
not arbitration policy.

Current assumptions:
    - read requests only
    - one request can be serviced by each bank per cycle
    - no cache
    - no variable SRAM latency
    - no writes
    - no RISC-V interaction
    - independent banks

Latency convention:
    wait_cycles =
        service_cycle - arrival_cycle

    latency =
        wait_cycles + 1

Therefore, a request arriving and being served
in the same cycle has:

    wait_cycles = 0
    latency     = 1
"""

from collections import deque

from access_generator import generate_accesses
from banking_model import (
    NUM_BANKS,
    POLICIES,
    get_bank,
)


# ============================================================
# Request creation
# ============================================================

def make_request(
    operand,
    row,
    index,
    arrival_cycle,
    K,
    N,
    policy,
    request_id,
):
    """
    Create one memory request.

    For A:
        row   = systolic row i
        index = reduction dimension k

    For B:
        row   = reduction dimension k
        index = systolic column j
    """

    bank = get_bank(
        operand=operand,
        row=row,
        index=index,
        K=K,
        N=N,
        policy=policy,
    )

    request = {
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

    return request


# ============================================================
# Generate individual requests
# ============================================================

def generate_requests(
    K,
    M=8,
    N=8,
    policy="modulo",
):
    """
    Convert the systolic access trace into individual
    memory requests.
    """

    access_trace = generate_accesses(
        K=K,
        M=M,
        N=N,
    )

    requests = []

    request_id = 0

    for cycle in access_trace:

        arrival_cycle = cycle["cycle"]

        # ----------------------------------------------------
        # A requests
        # ----------------------------------------------------

        for row, k in cycle["A"]:

            requests.append(
                make_request(
                    operand="A",
                    row=row,
                    index=k,
                    arrival_cycle=arrival_cycle,
                    K=K,
                    N=N,
                    policy=policy,
                    request_id=request_id,
                )
            )

            request_id += 1

        # ----------------------------------------------------
        # B requests
        # ----------------------------------------------------

        for k, col in cycle["B"]:

            requests.append(
                make_request(
                    operand="B",
                    row=k,
                    index=col,
                    arrival_cycle=arrival_cycle,
                    K=K,
                    N=N,
                    policy=policy,
                    request_id=request_id,
                )
            )

            request_id += 1

    return requests


# ============================================================
# FIFO bank service
# ============================================================

class FIFOBankService:

    def __init__(
        self,
        num_banks=NUM_BANKS,
    ):

        self.num_banks = num_banks

        # One FIFO queue per bank.
        self.queues = [
            deque()
            for _ in range(num_banks)
        ]

        # Requests in the order they were served.
        self.served_requests = []

        # Number of cycles each bank was busy.
        self.bank_busy_cycles = [
            0
            for _ in range(num_banks)
        ]

        # Maximum queue depth observed
        # for each bank.
        self.max_queue_depth = [
            0
            for _ in range(num_banks)
        ]

    # --------------------------------------------------------
    # Add request
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Service one cycle
    # --------------------------------------------------------

    def service_cycle(
        self,
        cycle,
    ):
        """
        Each bank services at most one request.

        FIFO ordering is maintained independently
        inside each bank.
        """

        serviced = []

        for bank in range(
            self.num_banks
        ):

            queue = self.queues[bank]

            if not queue:
                continue

            # FIFO:
            # oldest request is served first.
            request = queue.popleft()

            request["service_cycle"] = cycle

            # Waiting time excludes the service cycle.
            request["wait_cycles"] = (
                cycle
                - request["arrival_cycle"]
            )

            # Latency includes the service cycle.
            request["latency"] = (
                request["wait_cycles"]
                + 1
            )

            serviced.append(
                request
            )

            self.served_requests.append(
                request
            )

            self.bank_busy_cycles[bank] += 1

        return serviced

    # --------------------------------------------------------
    # Check whether queues are empty
    # --------------------------------------------------------

    def empty(self):

        return all(
            len(queue) == 0
            for queue in self.queues
        )

    # --------------------------------------------------------
    # Current queue depths
    # --------------------------------------------------------

    def queue_depths(self):

        return [
            len(queue)
            for queue in self.queues
        ]


# ============================================================
# Cycle-level simulation
# ============================================================

def simulate_policy(
    K,
    M=8,
    N=8,
    policy="modulo",
    trace=False,
):
    """
    Simulate one GEMM output tile.

    The simulation continues until:

        1. all injection requests have arrived
        2. all bank FIFOs are empty

    total_cycles represents the actual memory-service
    completion time.

    If the final request is served at cycle 18,
    total_cycles = 19.
    """

    requests = generate_requests(
        K=K,
        M=M,
        N=N,
        policy=policy,
    )

    service = FIFOBankService(
        num_banks=NUM_BANKS
    )

    # --------------------------------------------------------
    # Group requests by arrival cycle.
    # --------------------------------------------------------

    arrivals = {}

    for request in requests:

        cycle = request[
            "arrival_cycle"
        ]

        if cycle not in arrivals:

            arrivals[cycle] = []

        arrivals[cycle].append(
            request
        )

    injection_cycles = (
        K + M + N - 2
    )

    cycle = 0

    # --------------------------------------------------------
    # Simulation loop
    # --------------------------------------------------------

    while True:

        # ----------------------------------------------------
        # Stop once:
        #
        #   - all requests have arrived
        #   - all requests have been served
        # ----------------------------------------------------

        if (
            cycle >= injection_cycles
            and service.empty()
        ):
            break

        arriving = arrivals.get(
            cycle,
            [],
        )

        # ----------------------------------------------------
        # New requests enter their bank FIFOs.
        # ----------------------------------------------------

        for request in arriving:

            service.enqueue(
                request
            )

        # ----------------------------------------------------
        # Each bank serves one request.
        # ----------------------------------------------------

        served = service.service_cycle(
            cycle
        )

        # ----------------------------------------------------
        # Optional detailed trace.
        # ----------------------------------------------------

        if trace:

            print()
            print(
                f"Cycle {cycle}"
            )

            print(
                f"  Arrivals: "
                f"{len(arriving)}"
            )

            for request in arriving:

                print(
                    f"    "
                    f"{request['operand']}"
                    f"[{request['row']},"
                    f"{request['index']}] "
                    f"-> bank "
                    f"{request['bank']}"
                )

            print(
                f"  Served: "
                f"{len(served)}"
            )

            for request in served:

                print(
                    f"    "
                    f"bank "
                    f"{request['bank']} "
                    f"-> "
                    f"{request['operand']}"
                    f"[{request['row']},"
                    f"{request['index']}] "
                    f"(wait="
                    f"{request['wait_cycles']}, "
                    f"latency="
                    f"{request['latency']})"
                )

            print(
                "  Queue depths: "
                + " ".join(
                    f"B{bank}={depth}"
                    for bank, depth
                    in enumerate(
                        service.queue_depths()
                    )
                )
            )

        cycle += 1

    # ========================================================
    # Basic statistics
    # ========================================================

    total_requests = len(
        requests
    )

    total_cycles = cycle

    # --------------------------------------------------------
    # Wait cycles
    # --------------------------------------------------------

    wait_cycles = [
        request["wait_cycles"]
        for request in requests
    ]

    if wait_cycles:

        total_wait_cycles = sum(
            wait_cycles
        )

        average_wait_cycles = (
            total_wait_cycles
            / len(wait_cycles)
        )

        maximum_wait_cycles = max(
            wait_cycles
        )

    else:

        total_wait_cycles = 0
        average_wait_cycles = 0.0
        maximum_wait_cycles = 0

    # --------------------------------------------------------
    # Latency
    # --------------------------------------------------------

    latencies = [
        request["latency"]
        for request in requests
    ]

    if latencies:

        average_latency = (
            sum(latencies)
            / len(latencies)
        )

        maximum_latency = max(
            latencies
        )

    else:

        average_latency = 0.0
        maximum_latency = 0

    # --------------------------------------------------------
    # A/B wait statistics
    # --------------------------------------------------------

    a_wait_cycles = [
        request["wait_cycles"]
        for request in requests
        if request["operand"] == "A"
    ]

    b_wait_cycles = [
        request["wait_cycles"]
        for request in requests
        if request["operand"] == "B"
    ]

    average_A_wait = (
        sum(a_wait_cycles)
        / len(a_wait_cycles)
        if a_wait_cycles
        else 0.0
    )

    average_B_wait = (
        sum(b_wait_cycles)
        / len(b_wait_cycles)
        if b_wait_cycles
        else 0.0
    )

    maximum_A_wait = (
        max(a_wait_cycles)
        if a_wait_cycles
        else 0
    )

    maximum_B_wait = (
        max(b_wait_cycles)
        if b_wait_cycles
        else 0
    )

    # --------------------------------------------------------
    # A/B latency
    # --------------------------------------------------------

    a_latencies = [
        request["latency"]
        for request in requests
        if request["operand"] == "A"
    ]

    b_latencies = [
        request["latency"]
        for request in requests
        if request["operand"] == "B"
    ]

    average_A_latency = (
        sum(a_latencies)
        / len(a_latencies)
        if a_latencies
        else 0.0
    )

    average_B_latency = (
        sum(b_latencies)
        / len(b_latencies)
        if b_latencies
        else 0.0
    )

    # --------------------------------------------------------
    # Bank utilization
    # --------------------------------------------------------

    if total_cycles > 0:

        bank_utilization = [
            busy / total_cycles
            for busy
            in service.bank_busy_cycles
        ]

    else:

        bank_utilization = [
            0.0
            for _ in range(NUM_BANKS)
        ]

    average_bank_utilization = (
        sum(bank_utilization)
        / NUM_BANKS
    )

    # --------------------------------------------------------
    # Queue depth
    # --------------------------------------------------------

    maximum_queue_depth = max(
        service.max_queue_depth
    )

    # --------------------------------------------------------
    # Return complete result
    # --------------------------------------------------------

    return {
        "K": K,
        "M": M,
        "N": N,
        "policy": policy,

        "requests":
            total_requests,

        "injection_cycles":
            injection_cycles,

        "total_cycles":
            total_cycles,

        # Wait statistics
        "total_wait_cycles":
            total_wait_cycles,

        "average_wait_cycles":
            average_wait_cycles,

        "maximum_wait_cycles":
            maximum_wait_cycles,

        # Latency statistics
        "average_latency":
            average_latency,

        "maximum_latency":
            maximum_latency,

        # A/B wait statistics
        "average_A_wait":
            average_A_wait,

        "average_B_wait":
            average_B_wait,

        "maximum_A_wait":
            maximum_A_wait,

        "maximum_B_wait":
            maximum_B_wait,

        # A/B latency statistics
        "average_A_latency":
            average_A_latency,

        "average_B_latency":
            average_B_latency,

        # Bank statistics
        "bank_utilization":
            bank_utilization,

        "average_bank_utilization":
            average_bank_utilization,

        "maximum_queue_depth":
            maximum_queue_depth,

        "maximum_queue_depth_per_bank":
            service.max_queue_depth,

        # Detailed request information
        "requests_detail":
            service.served_requests,
    }


# ============================================================
# Summary table
# ============================================================

def print_summary(
    K_VALUES,
    M=8,
    N=8,
):

    print()
    print(
        "Cycle-Level FIFO Bank Service"
    )
    print(
        "=============================================="
    )
    print()

    print(
        f"{'K':>4} "
        f"{'Policy':>15} "
        f"{'Req':>6} "
        f"{'Cycles':>7} "
        f"{'AvgWait':>9} "
        f"{'MaxWait':>9} "
        f"{'AvgLat':>9} "
        f"{'MaxLat':>8} "
        f"{'MaxQ':>6}"
    )

    print(
        "-" * 90
    )

    for K in K_VALUES:

        for policy in POLICIES:

            result = simulate_policy(
                K=K,
                M=M,
                N=N,
                policy=policy,
                trace=False,
            )

            print(
                f"{K:4d} "
                f"{policy:>15} "
                f"{result['requests']:6d} "
                f"{result['total_cycles']:7d} "
                f"{result['average_wait_cycles']:9.3f} "
                f"{result['maximum_wait_cycles']:9d} "
                f"{result['average_latency']:9.3f} "
                f"{result['maximum_latency']:8d} "
                f"{result['maximum_queue_depth']:6d}"
            )


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":

    print_summary(
        K_VALUES=[
            8,
            32,
            64,
            128,
            256,
        ],
        M=8,
        N=8,
    )

    # --------------------------------------------------------
    # Detailed trace
    # --------------------------------------------------------

    print()
    print()
    print(
        "Detailed trace: "
        "8x8x8 split banking"
    )
    print(
        "====================================="
    )

    simulate_policy(
        K=8,
        M=8,
        N=8,
        policy="split",
        trace=True,
    )
