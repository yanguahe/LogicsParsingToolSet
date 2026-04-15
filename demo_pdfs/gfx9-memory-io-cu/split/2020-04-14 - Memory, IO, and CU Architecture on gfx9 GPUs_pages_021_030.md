# 2020-04-14 - Memory, IO, and CU Architecture on gfx9 GPUs - Pages 21-30

<!-- Page 21 -->



# AMD GCN Instruction Classes




Vector ALU (VALU): 64-wide ALU instruction.




Vector Memory (VMEM): 64-wide memory instruction.




Local Data Share (LDS): 64-wide memory operations to CU scratchpad.




Scalar ALU (SALU): ALU operation if every thread is working on identical data.




Scalar Memory (SMEM): Identical memory operation in all lanes.




Branch: Used if the entire wavefront wants to branch.




Internal: Wavefront bookkeeping. NOPs, workgroup barriers, wait-for-memory, etc.




---


<!-- Page 22 -->



# Inside a Compute Unit – Vector ALUs



<table><tr><td colspan="16">GEMM Calculation Unit</td></tr><tr><td>ALU Lane</td><td>ALU Lane</td><td>ALU Lane</td><td>ALU Lane</td><td>ALU Lane</td><td>ALU Lane</td><td>ALU Lane</td><td>ALU Lane</td><td>ALU Lane</td><td>ALU Lane</td><td>ALU Lane</td><td>ALU Lane</td><td>ALU Lane</td><td>ALU Lane</td><td>ALU Lane</td><td>ALU Lane</td></tr></table>

16-wide Vector Arithmetic Logic Unit: SIMD-16




- 4 per CU. Each will only run VALU instructions from its associated set of wave slots.




- Performs vectorized logical, integer, FP16, FP32, and FP64 operations.




- Supports FMA for FP64, FP32, and FP16 (FP16 as of Vega 20).




- Warning: 0.5 ULP accurate division generates reciprocal, multiply, and fixup instructions.




- Configurable denorm and rouding modes; FP32 and FP16/FP64 configured separately.




- $\geq$ MI100: Each VALU unit also contains hardware for BF16, FP16, and FP32 GEMM.




- MI200 adds DGEMM acceleration.




---


<!-- Page 23 -->



# Inside a Compute Unit – Vector ALUs



<table><tr><td colspan="14">GEMM Calculation Unit</td></tr><tr><td>ALU Lane</td><td>ALU Lane</td><td>ALU Lane</td><td>ALU Lane</td><td>ALU Lane</td><td>ALU Lane</td><td>ALU Lane</td><td>ALU Lane</td><td>ALU Lane</td><td>ALU Lane</td><td>ALU Lane</td><td>ALU Lane</td><td>ALU Lane</td><td>ALU Lane</td></tr></table>

<table><tr><td></td><td>“Vega 10”</td><td>“Vega 20”</td><td>“MI100”</td><td>“MI200”</td></tr><tr><td>Trad. FP32 FLOP/cycle</td><td>32</td><td>32</td><td>32</td><td>32</td></tr><tr><td>Trad. FP64 FLOP/cycle</td><td>2</td><td>16</td><td>16</td><td>32</td></tr><tr><td>Packed FP16 FLOP/cycle</td><td>64</td><td>64</td><td>64</td><td>64</td></tr><tr><td>FP16/int16 dot Op/cycle</td><td>-</td><td>64</td><td>64</td><td>64</td></tr><tr><td>int8 dot Op/cycle</td><td>-</td><td>128</td><td>128</td><td>128</td></tr><tr><td>int4 dot Op/cycle</td><td>-</td><td>256</td><td>256</td><td>256</td></tr><tr><td>FP32 GEMM FLOP/cycle</td><td>-</td><td>-</td><td>64</td><td>64</td></tr><tr><td>FP16/int8 GEMM Op/cycle</td><td>-</td><td>-</td><td>256</td><td>256</td></tr><tr><td>BF16 GEMM FLOP/cycle</td><td>-</td><td>-</td><td>128</td><td>256</td></tr><tr><td>FP64 GEMM FLOP/cycle</td><td>-</td><td>-</td><td>-</td><td>64</td></tr><tr><td>Packed FP32 FLOP/cycle</td><td>-</td><td>-</td><td>-</td><td>64</td></tr></table>



---


<!-- Page 24 -->



# Inside a Compute Unit – Vector Register Files



<table><tr><td>Vector Reg</td><td>Vector Reg</td><td>Vector Reg</td><td>Vector Reg</td><td>Vector Reg</td><td>Vector Reg</td><td>Vector Reg</td><td>Vector Reg</td><td>Vector Reg</td><td>Vector Reg</td><td>Vector Reg</td><td>Vector Reg</td><td>Vector Reg</td><td>Vector Reg</td></tr></table>

Each VGPR is 64 registers wide. Each wavefront's VALU lane (thread) accesses one of them.




- Data Parallel Primitive (DPP) instructions allow sourcing from another lane's register.




- All registers are 4 bytes (DWORD) wide. 64-bit values are stored in two contiguous VGPRs.




- Vega 20: 256 VGPRs per VALU.




- MI100: 256 VGPRs for traditional VALU. 256 accVGPRs for GEMM acceleration.




- MI200: Shared 512 VGPRs per VALU.




- Every wavefront can use up to 256 VGPRs (and 256 accVGPRs)



<table><tr><td>VGPRs</td><td>32</td><td>36</td><td>40</td><td>48</td><td>64</td><td>84</td><td>≤ 128</td><td>&gt; 128</td></tr><tr><td>Waves/SIMD-16</td><td>8</td><td>7</td><td>6</td><td>5</td><td>4</td><td>3</td><td>2</td><td>1</td></tr></table>

- Double the above register counts for MI200 if you are not using accVGPRs.




---


<!-- Page 25 -->



# Compute Unit Internals



Compute Unit

<table><tr><td>Wave Slots</td><td>Wave Slots</td><td>Wave Slots</td><td>Wave Slots</td></tr></table>

<table><tr><td>Vector ALU</td><td>Vector ALU</td><td>Vector ALU</td><td>Vector ALU</td></tr><tr><td></td><td></td><td></td><td></td></tr><tr><td></td><td></td><td></td><td></td></tr><tr><td></td><td></td><td></td><td></td></tr><tr><td>Vector Registers</td><td>Vector Registers</td><td>Vector Registers</td><td>Vector Registers</td></tr></table>



---


<!-- Page 26 -->



# AMD GCN Instruction Classes




Vector ALU (VALU): 64-wide ALU instruction.




Vector Memory (VMEM): 64-wide memory instruction.




Local Data Share (LDS): 64-wide memory operations to CU scratchpad.




Scalar ALU (SALU): ALU operation if every thread is working on identical data.




Scalar Memory (SMEM): Identical memory operation in all lanes.




Branch: Used if the entire wavefront wants to branch.




Internal: Wavefront bookkeeping. NOPs, workgroup barriers, wait-for-memory, etc.




---


<!-- Page 27 -->



# Inside a Compute Unit – Vector Memory




# Vector Memory Unit




Vector memory operations from all 4 wave slot groups are routed to this unit.




- Transfers data between global memory and VGPRs




A wavefront issuing a VMEM instruction requires the VMEM unit for 4 cycles to issue addresses.




Can handle uncoalesced addresses (e.g., each lane to a different address).




- Includes request coalescing logic to increase performance / minimize requests out of the CU.




Can write out 64B per cycle, or read in 64B per cycle.




- Connects to a 16 KiB vector L1 data cache, and out to further memory system.




- Includes logic for Buffer memory accesses, which can perform complex offsetting calculations automatically.




---


<!-- Page 28 -->



# Compute Unit Internals



Compute Unit

<table><tr><td>Wave Slots</td><td>Wave Slots</td><td>Wave Slots</td><td>Wave Slots</td></tr></table>

Vector Memory Unit



<table><tr><td>Vector ALU</td><td>Vector ALU</td><td>Vector ALU</td><td>Vector ALU</td></tr><tr><td></td><td></td><td></td><td></td></tr><tr><td></td><td></td><td></td><td></td></tr><tr><td>Vector Registers</td><td>Vector Registers</td><td>Vector Registers</td><td>Vector Registers</td></tr></table>

![Figure 1](figures/page_028_fig_01.png)



---


<!-- Page 29 -->



# On-chip Memory System



<table><tr><td rowspan="8">SE</td><td>CU</td><td rowspan="8"></td></tr><tr><td>CU</td></tr><tr><td>CU</td></tr><tr><td>CU</td></tr><tr><td>CU</td></tr><tr><td>CU</td></tr><tr><td>CU</td></tr><tr><td>CU</td></tr><tr><td rowspan="8">SE</td><td>CU</td><td rowspan="8"></td></tr><tr><td>CU</td></tr><tr><td>CU</td></tr><tr><td>CU</td></tr><tr><td>CU</td></tr><tr><td>CU</td></tr><tr><td>CU</td></tr><tr><td>CU</td></tr><tr><td colspan="3">GPU</td></tr><tr><td rowspan="8"></td><td>CU</td><td rowspan="8">SE</td></tr><tr><td>CU</td></tr><tr><td>CU</td></tr><tr><td>CU</td></tr><tr><td>CU</td></tr><tr><td>CU</td></tr><tr><td>CU</td></tr><tr><td>CU</td></tr><tr><td colspan="3">Memory Controllers</td></tr><tr><td colspan="3">HBM/GDDR Memory</td></tr></table>



---


<!-- Page 30 -->



# On-chip Memory System



<table><tr><td rowspan="8">SE</td><td>CU</td><td>Vector L1 DCache</td></tr><tr><td>CU</td><td>Vector L1 DCache</td></tr><tr><td>CU</td><td>Vector L1 DCache</td></tr><tr><td>CU</td><td>Vector L1 DCache</td></tr><tr><td>CU</td><td>Vector L1 DCache</td></tr><tr><td>CU</td><td>Vector L1 DCache</td></tr><tr><td>CU</td><td>Vector L1 DCache</td></tr><tr><td>CU</td><td>Vector L1 DCache</td></tr></table>

<table><tr><td>Vector L1 DCache</td><td>CU</td><td rowspan="8">SE</td></tr><tr><td>Vector L1 DCache</td><td>CU</td></tr><tr><td>Vector L1 DCache</td><td>CU</td></tr><tr><td>Vector L1 DCache</td><td>CU</td></tr><tr><td>Vector L1 DCache</td><td>CU</td></tr><tr><td>Vector L1 DCache</td><td>CU</td></tr><tr><td>Vector L1 DCache</td><td>CU</td></tr><tr><td>Vector L1 DCache</td><td>CU</td></tr></table>

<table><tr><td rowspan="8">SE</td><td>CU</td><td>Vector L1 DCache</td></tr><tr><td>CU</td><td>Vector L1 DCache</td></tr><tr><td>CU</td><td>Vector L1 DCache</td></tr><tr><td>CU</td><td>Vector L1 DCache</td></tr><tr><td>CU</td><td>Vector L1 DCache</td></tr><tr><td>CU</td><td>Vector L1 DCache</td></tr><tr><td>CU</td><td>Vector L1 DCache</td></tr><tr><td>CU</td><td>Vector L1 DCache</td></tr></table>

<table><tr><td>Vector L1 DCache</td><td>CU</td><td rowspan="8">SE</td></tr><tr><td>Vector L1 DCache</td><td>CU</td></tr><tr><td>Vector L1 DCache</td><td>CU</td></tr><tr><td>Vector L1 DCache</td><td>CU</td></tr><tr><td>Vector L1 DCache</td><td>CU</td></tr><tr><td>Vector L1 DCache</td><td>CU</td></tr><tr><td>Vector L1 DCache</td><td>CU</td></tr><tr><td>Vector L1 DCache</td><td>CU</td></tr></table>

Memory Controllers




HBM/GDDR Memory




---


