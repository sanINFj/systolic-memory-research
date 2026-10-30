import math

BANKS, CAPACITY = 8, 8192

# (BM, BK, BN) from the capacity-selector output
workloads = {
    "square_32": (32, 32, 32),
    "square_64": (64, 64, 64),
    "square_128": (64, 128, 128),
    "square_256": (64, 128, 128),
    "input_heavy": (128, 64, 64),
    "weight_heavy": (64, 64, 128),
    "k_heavy": (64, 256, 64),
    "rectangular_1": (64, 128, 128),
    "rectangular_2": (64, 128, 128),
    "edge_70x70x64": (70, 64, 70),
    "edge_13x29x17": (13, 17, 29),
}

def mapped(is_a, r, c, K, N, policy):
    if policy == 0:
        addr = r*K+c if is_a else 32768+r*N+c
        return addr % 8, addr // 8

    if policy == 1:
        if is_a:
            return r % 4, (r//4)*K+c
        return 4+c%4, r*((N+3)//4)+c//4

    if policy == 2:
        if is_a:
            return r % 8, (r//8)*K+c
        return (c+4)%8, 4096+r*((N+7)//8)+c//8

    if policy == 3:
        bank = (r % 8) ^ (c % 8)
        if is_a:
            local = (r//8)*((K+7)//8)*8+(c//8)*8+(r%8)
        else:
            local = 4096+(r//8)*((N+7)//8)*8+(c//8)*8+(r%8)
        return bank, local

print("PER-BANK CAPACITY CHECK (8 banks x 8192 bytes)")
print("Policy: P0=modulo P1=split P2=operand-aware P3=XOR")
failures = 0

for name, (BM, BK, BN) in workloads.items():
    for policy in range(4):
        addresses = [set() for _ in range(BANKS)]

        for r in range(BM):
            for c in range(BK):
                b, a = mapped(True, r, c, BK, BN, policy)
                addresses[b].add(a)

        for r in range(BK):
            for c in range(BN):
                b, a = mapped(False, r, c, BK, BN, policy)
                addresses[b].add(a)

        counts = [len(x) for x in addresses]
        max_count = max(counts)
        max_addr = max((max(x) if x else -1) for x in addresses)
        passed = max_count <= CAPACITY and max_addr < CAPACITY

        if not passed:
            failures += 1

        print(f"{name:18} P{policy}: max_bank={max_count:5} "
              f"max_local_addr={max_addr:5} "
              f"{'PASS' if passed else 'FAIL'}")

print(f"\nTOTAL: {44-failures}/44 configurations passed")
if failures:
    raise SystemExit(1)
