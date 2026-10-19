# 5-minute project demo

## 0:00–0:40 — Problem and design
Explain the 64 KiB SRAM budget, eight banks, queued bank service, and why
bank conflicts can stall operand delivery.

## 0:40–1:30 — Mapping policies
Compare P0 modulo, P1 split A/B, P2 operand-aware, and P3 XOR mapping.

## 1:30–2:30 — Memory benchmark
Show the 12-run RTL summary:
8×8×8: P0/P3 17 cycles, P1 21, P2 20.
10×8×10: P0/P3 21, P1 30, P2 27.
13×7×11: P0/P3 23, P1 29, P2 30.
Mention zero overflow and that cycles represent memory-service benchmarking.

## 2:30–3:30 — Compute verification
Run the stall-aware array test. Show C = [[19,22],[43,50]].

## 3:30–4:20 — SRAM-fed streaming test
Run the streaming baseline. Show 8 requests, 8 responses, correct outputs,
and response-gated operand waits. Explain that this is staged rather than
fully overlapped memory/compute execution.

## 4:20–5:00 — Modeling and conclusion
Show the traffic, capacity, conflict, and architecture plots. Clearly label
larger-workload cycle/PE-utilization results as model estimates rather than
RTL measurements.
