
## Final Evaluation and Reproducibility

### Objective

This project studies how memory organization and bank-mapping policies affect
memory-service performance for a RISC-V-connected systolic-array matrix
multiplication accelerator under a constrained memory budget.

The evaluation combines SystemVerilog RTL simulations with Python architectural
models. Analytical estimates and RTL measurements are reported separately.

### RTL Architecture

The RTL includes banked SRAM, bank mapping, per-bank request queues, processing
elements, and systolic-array implementations with valid and stall-aware control.

The evaluated mapping policies are:

- **P0 — Modulo mapping**
- **P1 — Split A/B mapping**
- **P2 — Operand-aware mapping**
- **P3 — XOR mapping**

### Validation

The recorded tests include:

- Physical-mapping unit tests: 5 passed.
- Stall-aware 2×2 systolic GEMM: expected outputs verified.
- Memory-fed 8×8 benchmark: 128 read requests and 128 responses verified.
- Response-gated streaming 2×2 GEMM: 8 requests and 8 responses verified.
- Concurrent memory benchmark: 12 policy/workload runs completed with zero
  overflow cycles in the tested cases.

Run the physical-mapping tests from the repository root:

    python3 -m unittest -v tests.test_physical_mapping

The SystemVerilog tests use Icarus Verilog (`iverilog`) and `vvp`. Refer to the
testbench files and validation logs for test-specific compile commands.

### Concurrent Memory Benchmark

| Matrix shape (M × K × N) | Operand-read requests |
|---|---:|
| 8 × 8 × 8 | 128 |
| 10 × 8 × 10 | 160 |
| 13 × 7 × 11 | 168 |

For the tested request order and batch size, P0 and P3 tied for the lowest
measured total memory-service cycles across all three workload shapes.
This result applies to the tested configurations and does not establish a
universal ranking of mapping policies.

### Results

The `results/` directory contains model outputs, benchmark summaries, logs,
and plots. The final handoff package is `results/FINAL_DEMO_PACKAGE.zip`.

Key deliverables:

- `results/final_demo/FINAL_REPORT.md`
- `results/final_demo/DEMO_SCRIPT.md`
- `results/final_demo/tables/`
- `results/final_demo/plots/`
- `results/final_demo/logs/`

### Limitations

The streaming GEMM test is a staged, response-gated 2×2 demonstration, not a
fully overlapped memory-to-compute pipeline. The concurrent policy benchmark
measures memory-subsystem service behavior, not full end-to-end GEMM execution
for every mapping policy. Analytical architecture estimates are not direct RTL
measurements. Conclusions should be interpreted within the tested workloads,
request ordering, configurations, and simulation setup.

