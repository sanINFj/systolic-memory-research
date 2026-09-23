import numpy as np


def gemm(A, B):
    """
    Golden GEMM reference.

    A: M x K
    B: K x N
    Returns: M x N
    """
    return A.astype(np.int32) @ B.astype(np.int32)


def generate_gemm(M, K, N, seed=0):
    """
    Generate deterministic INT8 GEMM operands.
    """
    rng = np.random.default_rng(seed)

    A = rng.integers(-8, 8, size=(M, K), dtype=np.int8)
    B = rng.integers(-8, 8, size=(K, N), dtype=np.int8)

    return A, B


if __name__ == "__main__":
    M, K, N = 8, 8, 8

    A, B = generate_gemm(M, K, N)

    C = gemm(A, B)

    print("A:")
    print(A)

    print("\nB:")
    print(B)

    print("\nC = A @ B:")
    print(C)
