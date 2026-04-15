# 03-MemoryHierarchy

## Chapters

- [CDNA2 Memory Hierarchy](03-MemoryHierarchy_pages_001_010.md#cdna2-memory-hierarchy)
- [A Team Effort](03-MemoryHierarchy_pages_001_010.md#a-team-effort)
- [Agenda](03-MemoryHierarchy_pages_001_010.md#agenda)
- [AMD CDNA2 GPU Hardware Layout](03-MemoryHierarchy_pages_001_010.md#amd-cdna2-gpu-hardware-layout)
- [AMD CDNA2 GPU Hardware Layout](03-MemoryHierarchy_pages_001_010.md#amd-cdna2-gpu-hardware-layout)
- [The CDNA2 Compute Unit (CU)](03-MemoryHierarchy_pages_001_010.md#the-cdna2-compute-unit-cu)
- [Compute Unit (CU)](03-MemoryHierarchy_pages_001_010.md#compute-unit-cu)
- [The CDNA2 Compute Unit (CU) – Scalar Unit](03-MemoryHierarchy_pages_001_010.md#the-cdna2-compute-unit-cu-scalar-unit)
- [The CDNA2 Compute Unit (CU) – Vector ALU](03-MemoryHierarchy_pages_001_010.md#the-cdna2-compute-unit-cu-vector-alu)
- [The CDNA2 Compute Unit (CU) – Matrix Cores](03-MemoryHierarchy_pages_001_010.md#the-cdna2-compute-unit-cu-matrix-cores)
- [The CDNA2 Compute Unit (CU) – Vector Memory Unit](03-MemoryHierarchy_pages_011_020.md#the-cdna2-compute-unit-cu-vector-memory-unit)
- [The CDNA2 Compute Unit (CU) - LDS](03-MemoryHierarchy_pages_011_020.md#the-cdna2-compute-unit-cu-lds)
- [The CDNA2 Compute Unit (CU) - Scheduler](03-MemoryHierarchy_pages_011_020.md#the-cdna2-compute-unit-cu-scheduler)
- [The CDNA2 Compute Unit (CU) - Scheduler](03-MemoryHierarchy_pages_011_020.md#the-cdna2-compute-unit-cu-scheduler)
- [GPU Occupancy on CDNA2](03-MemoryHierarchy_pages_011_020.md#gpu-occupancy-on-cdna2)
- [What is Occupancy?](03-MemoryHierarchy_pages_011_020.md#what-is-occupancy)
- [Occupancy: Limiting Factors](03-MemoryHierarchy_pages_011_020.md#occupancy-limiting-factors)
- [Occupancy: Limiting Factors - VGPRs](03-MemoryHierarchy_pages_011_020.md#occupancy-limiting-factors-vgprs)
- [Occupancy: Limiting Factors - SGPRs](03-MemoryHierarchy_pages_011_020.md#occupancy-limiting-factors-sgprs)
- [Occupancy: Register Spilling](03-MemoryHierarchy_pages_011_020.md#occupancy-register-spilling)
- [Occupancy: Limiting Factors - LDS](03-MemoryHierarchy_pages_021_030.md#occupancy-limiting-factors-lds)
- [Example: batched matrix-vector multiply](03-MemoryHierarchy_pages_021_030.md#example-batched-matrix-vector-multiply)
- [Example: batched matrix-vector multiply](03-MemoryHierarchy_pages_021_030.md#example-batched-matrix-vector-multiply)
- [Example occupancy calculation](03-MemoryHierarchy_pages_021_030.md#example-occupancy-calculation)
- [Example occupancy calculation](03-MemoryHierarchy_pages_021_030.md#example-occupancy-calculation)
- [Example occupancy calculation](03-MemoryHierarchy_pages_021_030.md#example-occupancy-calculation)
- [Example occupancy calculation](03-MemoryHierarchy_pages_021_030.md#example-occupancy-calculation)
- [Example occupancy calculation](03-MemoryHierarchy_pages_021_030.md#example-occupancy-calculation)
- [Wrap Up](03-MemoryHierarchy_pages_021_030.md#wrap-up)
- [DISCLAIMERS AND ATTRIBUTIONS](03-MemoryHierarchy_pages_021_030.md#disclaimers-and-attributions)
- [AMD](03-MemoryHierarchy_pages_031_031.md#amd)

---

## Detailed Table of Contents

- [CDNA2 Memory Hierarchy](03-MemoryHierarchy_pages_001_010.md#cdna2-memory-hierarchy)
- [A Team Effort](03-MemoryHierarchy_pages_001_010.md#a-team-effort)
- [Agenda](03-MemoryHierarchy_pages_001_010.md#agenda)
- [AMD CDNA2 GPU Hardware Layout](03-MemoryHierarchy_pages_001_010.md#amd-cdna2-gpu-hardware-layout)
- [AMD CDNA2 GPU Hardware Layout](03-MemoryHierarchy_pages_001_010.md#amd-cdna2-gpu-hardware-layout)
- [The CDNA2 Compute Unit (CU)](03-MemoryHierarchy_pages_001_010.md#the-cdna2-compute-unit-cu)
- [Compute Unit (CU)](03-MemoryHierarchy_pages_001_010.md#compute-unit-cu)
- [The CDNA2 Compute Unit (CU) – Scalar Unit](03-MemoryHierarchy_pages_001_010.md#the-cdna2-compute-unit-cu-scalar-unit)
- [The CDNA2 Compute Unit (CU) – Vector ALU](03-MemoryHierarchy_pages_001_010.md#the-cdna2-compute-unit-cu-vector-alu)
- [The CDNA2 Compute Unit (CU) – Matrix Cores](03-MemoryHierarchy_pages_001_010.md#the-cdna2-compute-unit-cu-matrix-cores)
- [The CDNA2 Compute Unit (CU) – Vector Memory Unit](03-MemoryHierarchy_pages_011_020.md#the-cdna2-compute-unit-cu-vector-memory-unit)
- [The CDNA2 Compute Unit (CU) - LDS](03-MemoryHierarchy_pages_011_020.md#the-cdna2-compute-unit-cu-lds)
- [The CDNA2 Compute Unit (CU) - Scheduler](03-MemoryHierarchy_pages_011_020.md#the-cdna2-compute-unit-cu-scheduler)
- [The CDNA2 Compute Unit (CU) - Scheduler](03-MemoryHierarchy_pages_011_020.md#the-cdna2-compute-unit-cu-scheduler)
- [GPU Occupancy on CDNA2](03-MemoryHierarchy_pages_011_020.md#gpu-occupancy-on-cdna2)
- [What is Occupancy?](03-MemoryHierarchy_pages_011_020.md#what-is-occupancy)
- [Occupancy: Limiting Factors](03-MemoryHierarchy_pages_011_020.md#occupancy-limiting-factors)
- [Occupancy: Limiting Factors - VGPRs](03-MemoryHierarchy_pages_011_020.md#occupancy-limiting-factors-vgprs)
- [Occupancy: Limiting Factors - SGPRs](03-MemoryHierarchy_pages_011_020.md#occupancy-limiting-factors-sgprs)
- [Occupancy: Register Spilling](03-MemoryHierarchy_pages_011_020.md#occupancy-register-spilling)
- [Occupancy: Limiting Factors - LDS](03-MemoryHierarchy_pages_021_030.md#occupancy-limiting-factors-lds)
- [Example: batched matrix-vector multiply](03-MemoryHierarchy_pages_021_030.md#example-batched-matrix-vector-multiply)
- [Example: batched matrix-vector multiply](03-MemoryHierarchy_pages_021_030.md#example-batched-matrix-vector-multiply)
- [Example occupancy calculation](03-MemoryHierarchy_pages_021_030.md#example-occupancy-calculation)
- [Example occupancy calculation](03-MemoryHierarchy_pages_021_030.md#example-occupancy-calculation)
- [Example occupancy calculation](03-MemoryHierarchy_pages_021_030.md#example-occupancy-calculation)
- [Example occupancy calculation](03-MemoryHierarchy_pages_021_030.md#example-occupancy-calculation)
- [Example occupancy calculation](03-MemoryHierarchy_pages_021_030.md#example-occupancy-calculation)
- [Wrap Up](03-MemoryHierarchy_pages_021_030.md#wrap-up)
- [DISCLAIMERS AND ATTRIBUTIONS](03-MemoryHierarchy_pages_021_030.md#disclaimers-and-attributions)
- [AMD](03-MemoryHierarchy_pages_031_031.md#amd)

---

## Browse by Page Range

| Page Range | Link |
|:---|:---|
| Pages 1-10 | [03-MemoryHierarchy_pages_001_010.md](03-MemoryHierarchy_pages_001_010.md) |
| Pages 11-20 | [03-MemoryHierarchy_pages_011_020.md](03-MemoryHierarchy_pages_011_020.md) |
| Pages 21-30 | [03-MemoryHierarchy_pages_021_030.md](03-MemoryHierarchy_pages_021_030.md) |
| Pages 31-31 | [03-MemoryHierarchy_pages_031_031.md](03-MemoryHierarchy_pages_031_031.md) |

