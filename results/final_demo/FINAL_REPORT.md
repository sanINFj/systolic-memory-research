# Memory-Aware RISC-V Systolic Array Accelerator for Matrix Multiplication

## 1. Objective

Evaluate how memory-bank mapping and memory organization affect operand
service, bank conflicts, data movement, and estimated execution performance
for a systolic matrix-multiplication accelerator under a 64 KiB memory budget.

## 2. Architecture

- Eight SRAM banks, each with 8 KiB capacity: 64 KiB aggregate capacity.
- Per-bank request FIFOs with depth 32.
- Up to 16 read requests presented per cycle.
- At most one queued request serviced per bank per cycle.
- Tagged responses identify the requesting operand.
- Four bank-mapping policies: modulo, split A/B, operand-aware, and XOR.
- A stall-aware systolic-array implementation holds PE state when `advance=0`.
- Signed 8-bit input operands and 32-bit accumulation in the stall-aware PE.

## 3. Implemented mapping policies

| Policy | Mapping idea |
|---|---|
| P0 | Modulo mapping using low address bits |
| P1 | Separate bank groups for A and B |
| P2 | Operand-aware bank assignment |
| P3 | XOR-based row/index bank selection |

## 4. RTL memory-service comparison

The concurrent RTL performance benchmark tested three request shapes with
Request counts below represent individual 8-bit operand reads. Each benchmark submits requests in batches of at most 16.

| Shape (M×K×N) | Reads | P0 cycles | P1 cycles | P2 cycles | P3 cycles |
|---|---:|---:|---:|---:|---:|
| 8×8×8 | 128 | 17 | 21 | 20 | 17 |
| 10×8×10 | 160 | 21 | 30 | 27 | 21 |
| 13×7×11 | 168 | 23 | 29 | 30 | 23 |

All 12 policy/shape runs completed response/tag/completeness checks with
zero overflow cycles. P0 and P3 tied for the lowest total measured cycles
for these particular workloads and request ordering. This is not evidence
that they are universally superior for every dataflow or access pattern.

Cycle definition: request-issue cycles plus extra response-drain cycles.
This metric is for the memory-service benchmark, not end-to-end RTL GEMM
execution time.

## 5. RTL verification

The recorded tests cover:
- Directed bank/FIFO concurrency and overflow checks.
- Existing end-to-end GEMM testbench and all-policy tests.
- Stall-aware systolic-array arithmetic.
- SRAM response/tag verification.
- A response-gated 2×2 memory-fed stall-aware GEMM.

The streaming baseline uses A=[[1,2],[3,4]] and B=[[5,6],[7,8]].
Expected output C=[[19,22],[43,50]]. The latest run passed all four output
checks, received 8/8 responses, and reported 16 operand-wait/stall cycles
over 23 measured wait/compute/flush cycles.

Important limitation: the response-gated streaming baseline fetches the
operands required for each wavefront before advancing the array. It is not
yet a fully overlapped memory/compute pipeline. The measured 23 cycles are
specific to this small testbench and should not be compared directly with
the concurrent memory-service benchmark's cycle counts.

## 6. Modeling and analysis

The project also includes Python models for physical mapping, bank conflicts,
combined tile banking, full-GEMM banking, dataflow execution, traffic,
capacity/tile selection, and architecture-hierarchy metrics.

Model-derived cycle, traffic, and PE-utilization estimates are analytical
results, not RTL measurements. Their assumptions should be stated when
presenting them. The 64 KiB capacity constraint applies to the modeled
memory organization; results that assume a particular tile or data layout
must be interpreted accordingly.

## 7. Main conclusions supported by current results

1. Mapping policy changes the distribution of requests across banks and the
   amount of queued work per bank.
2. In the three measured concurrent request workloads, P0 and P3 had the
   lowest measured memory-service cycle counts.
3. The response-gated 2×2 integration test verifies that actual SRAM
   responses can supply a stall-aware systolic GEMM with correct arithmetic.
4. The modeling suite extends analysis to larger workloads, memory traffic,
   capacity, and estimated compute utilization.
5. A fully overlapped memory/compute RTL benchmark across all four policies
   remains future work; the current evidence should not be described as one.

## 8. Demo sequence

1. Show the 8-bank SRAM and per-bank FIFO implementation.
2. Explain P0–P3 bank mapping.
3. Run the concurrent-policy benchmark and show the 12-run summary.
4. Open the bank-conflict and cycle comparison plots.
5. Run the stall-aware array arithmetic test.
6. Run the response-gated streaming GEMM and show the expected/actual C
   values, 8 responses, and PASS result.
7. Close with the distinction between measured RTL results and analytical
   model estimates.

## 9. Reproducibility

See `logs/final_validation.log` for the latest validation commands and output.
CSV tables, SVG plots, and benchmark logs are included alongside this report.
