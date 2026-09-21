import numpy as np


def gemm(a, b):
    """
    Golden reference for C = A @ B.

    Inputs:
        a: M x K int8 matrix
        b: K x N int8 matrix

    Output:
        M x N int32 matrix
    """

    a = np.asarray(a, dtype=np.int32)
    b = np.asarray(b, dtype=np.int32)

    return a @ b


if __name__ == "__main__":
    a = np.array(
        [
            [1, 2],
            [3, 4],
        ],
        dtype=np.int8,
    )

    b = np.array(
        [
            [5, 6],
            [7, 8],
        ],
        dtype=np.int8,
    )

    c = gemm(a, b)

    print("A:")
    print(a)

    print("\nB:")
    print(b)

    print("\nC = A @ B:")
    print(c)
