from workload_generator import WORKLOADS
from tile_search import search_tiles


def run_sweep():

    print("=" * 90)
    print("WORKLOAD SWEEP")
    print("=" * 90)

    for workload in WORKLOADS:

        name = workload["name"]
        M = workload["M"]
        K = workload["K"]
        N = workload["N"]

        print()
        print(f"{name}: {M} x {K} * {K} x {N}")
        print("-" * 90)

        for config_name in ["A", "B", "C"]:

            for dataflow in ["OS", "WS"]:

                results = search_tiles(
                    M,
                    K,
                    N,
                    config_name,
                    dataflow
                )

                if not results:
                    print(
                        f"{config_name}-{dataflow}: "
                        "NO LEGAL TILE"
                    )
                    continue

                best = results[0]

                print(
                    f"{config_name}-{dataflow}: "
                    f"tile={best['Mt']}x{best['Kt']}x{best['Nt']} "
                    f"traffic={best['traffic']/1024:.2f} KB"
                )


if __name__ == "__main__":
    run_sweep()
