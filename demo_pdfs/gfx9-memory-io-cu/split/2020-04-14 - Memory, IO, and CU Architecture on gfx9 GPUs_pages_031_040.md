# 2020-04-14 - Memory, IO, and CU Architecture on gfx9 GPUs - Pages 31-40

<!-- Page 31 -->



# Per-CU Vector L1 Data Cache (TCP)




# Compute Unit




64-wide Vector Memory Unit




Read 64B/cycle Write 64B/cycle (or send read addr)





<p data-bbox="399,162,661,196">16 KiB Read/Write Data Cache




64B cache lines, 64-way set associative




64 MSHR in each set




- Write-through, Write-allocate if whole line is dirty




- If SLC & GLC bits are set in VMEM instruction, write-no-allocate




- Performs write-combining of multiple stores from a single wave




- VMEM GLC bit allows bypass of vL1D




- VMEM instructions controls replacement policy:




- Default to LRU replacement




- VMEM SLC bit set causes misses to insert as LRU




- Non-inclusive of L2 cache




- Virtually indexed, physically tagged





<p data-bbox="399,740,763,776">- 32-entry, fully associative, LRU replacement




- Supports 4KiB, 2MiB, and other page table entry sizes




- Up to 16 VMIDs in use at once




- 2 translations/cycle




- 64 outstanding misses




---


<!-- Page 32 -->



# AMD GCN Instruction Classes




Vector ALU (VALU): 64-wide ALU instruction.




Vector Memory (VMEM): 64-wide memory instruction.




Local Data Share (LDS): 64-wide memory operations to CU scratchpad.




Scalar ALU (SALU): ALU operation if every thread is working on identical data.




Scalar Memory (SMEM): Identical memory operation in all lanes.




Branch: Used if the entire wavefront wants to branch.




Internal: Wavefront bookkeeping. NOPs, workgroup barriers, wait-for-memory, etc.




---


<!-- Page 33 -->



# Inside a Compute Unit – Local Data Share




64 KiB scrachpad memory accessible from any SIMD-16 in this CU.




32 banks: useful for swizzling data between vector lanes or uncoalesced accesses.




- 128B per cycle results in a full wavefront serviced every 2 cycles.




- Includes atomic units for logical, integer, FP32. MI200 adds FP64.




- LDS network used for inter-lane swizzle and permute operations without needing storage space.




- All wavefronts within a workgroup can access the same range of LDS.




- Requested LDS storage per workgroup can thus limit CU occupancy




---


<!-- Page 34 -->



# Compute Unit Internals



Compute Unit

<table><tr><td>Wave Slots</td><td>Wave Slots</td><td>Wave Slots</td><td>Wave Slots</td></tr></table>

Vector Memory Unit



<table><tr><td>Vector ALU</td><td>Vector ALU</td><td>Vector ALU</td><td>Vector ALU</td></tr><tr><td></td><td></td><td></td><td></td></tr><tr><td></td><td></td><td></td><td></td></tr><tr><td>Vector Registers</td><td>Vector Registers</td><td>Vector Registers</td><td>Vector Registers</td></tr></table>

Local Data Share



![Figure 1](figures/page_034_fig_01.png)



---


<!-- Page 35 -->



# AMD GCN Instruction Classes




Vector ALU (VALU): 64-wide ALU instruction.




Vector Memory (VMEM): 64-wide memory instruction.




Local Data Share (LDS): 64-wide memory operations to CU scratchpad.




Scalar ALU (SALU): ALU operation if every thread is working on identical data.




Scalar Memory (SMEM): Identical memory operation in all lanes.




Branch: Used if the entire wavefront wants to branch.




Internal: Wavefront bookkeeping. NOPs, workgroup barriers, wait-for-memory, etc.




---


<!-- Page 36 -->



# Inside a Compute Unit – Scalar ALU




# Scalar ALU




# Scalar Register File




- Integer arithmetic and logical operations used when all lanes of a wavefront doing the same thing.




- When using SALU instruction, only one operation is performed (no duplication of computation).




- Especially useful for setting up wavefront-wide control flow.




- Converged branches, function calls, etc.




- 800 SGPRs available for wavefronts in each wave slot group.




- SGPRs can also be read by VALU instructions; all lanes see the same value.




---


<!-- Page 37 -->



# Compute Unit Internals



Compute Unit

<table><tr><td>Wave Slots</td><td>Wave Slots</td><td>Wave Slots</td><td>Wave Slots</td></tr></table>

Vector Memory Unit



<table><tr><td>Vector ALU</td><td>Vector ALU</td><td>Vector ALU</td><td>Vector ALU</td></tr><tr><td></td><td></td><td></td><td></td></tr><tr><td></td><td></td><td></td><td></td></tr><tr><td>Vector Registers</td><td>Vector Registers</td><td>Vector Registers</td><td>Vector Registers</td></tr></table>

Scalar ALU




Scalar Registers




Local Data Share



![Figure 1](figures/page_037_fig_01.png)



---


<!-- Page 38 -->



# AMD GCN Instruction Classes




Vector ALU (VALU): 64-wide ALU instruction.




Vector Memory (VMEM): 64-wide memory instruction.




Local Data Share (LDS): 64-wide memory operations to CU scratchpad.




Scalar ALU (SALU): ALU operation if every thread is working on identical data.




Scalar Memory (SMEM): Identical memory operation in all lanes.




Branch: Used if the entire wavefront wants to branch.




Internal: Wavefront bookkeeping. NOPs, workgroup barriers, wait-for-memory, etc.




---


<!-- Page 39 -->



# Inside a Compute Unit – Scalar Memory




# Scalar Memory Unit




- Scalar memory operations from all 4 wave slot groups are routed to this unit. - Transfers data between global memory and SGPRs.




- Supports reads, writes, and logical/integer atomics.




- Used if you want to do a wavefront-wide access, rather than each lane doing individual accesses.




- Can read or write 16B/cycle to memory system.




- Connects to a 16 KiB scalar L1 data cache, and out to further memory system. - Different cache than the vL1D. But shared with three other CUs.




---


<!-- Page 40 -->



# Compute Unit Internals



<table><tr><td colspan="4">Compute Unit</td></tr><tr><td></td><td>Wave Slots</td><td>Wave Slots</td><td>Wave Slots</td></tr><tr><td></td><td colspan="3">Wave Slots</td></tr><tr><td>Vector Memory Unit</td><td colspan="3"></td></tr><tr><td rowspan="4">Scalar Memory Unit</td><td>Vector ALU</td><td>Vector ALU</td><td>Vector ALU</td></tr><tr><td></td><td></td><td></td></tr><tr><td>Vector Registers</td><td>Vector Registers</td><td>Vector Registers</td></tr><tr><td colspan="3">Vector Registers</td></tr><tr><td colspan="4">Local Data Share</td></tr><tr><td>Scalar ALU</td><td colspan="3"></td></tr><tr><td>Scalar Registers</td><td colspan="3"></td></tr></table>



---


