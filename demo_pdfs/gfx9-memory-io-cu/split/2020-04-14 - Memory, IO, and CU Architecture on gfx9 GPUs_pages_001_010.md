# 2020-04-14 - Memory, IO, and CU Architecture on gfx9 GPUs - Pages 1-10

<!-- Page 1 -->



# AMD GCN/CDNA Architecture Training Memory, IO, and CU Architecture on gfx9 GPUs




Joseph Greathouse




Machine Learning Software Engineering (MLSE)




RTG, AMD




Apr. 14, 2020




---


<!-- Page 2 -->



# AGENDA




GCN Assembly AMD GCN Assembly Instruction Classes




SIMT Program Example




Branching in a SIMT Program




Hardware Internals Compute Units




Memory System




Input/Output Efficiency Arbiters




SDMAs




---


<!-- Page 3 -->



# AMD GCN Assembly Instruction Classes




---


<!-- Page 4 -->



# Reminder of GPU Kernel Layout



<table><tr><td colspan="5">GPU Kernel</td></tr><tr><td colspan="5">Workgroup 0</td></tr><tr><td>Wavefront 0</td><td>64 work items (threads)</td><td>Wavefront 1</td><td>...</td><td>Wavefront 15</td></tr><tr><td>Workgroup 1</td><td colspan="4">Wavefront<br/>Collection of resources that execute in lockstep, run the same instructions, and follow the same control-flow path. Individual lanes can be masked off. Can think of this as a vector thread, or a thread running SIMD instructions.</td></tr><tr><td>Workgroup 2</td><td colspan="4"></td></tr><tr><td>Workgroup 3</td><td colspan="4"></td></tr><tr><td>Workgroup 4</td><td colspan="4"></td></tr><tr><td>...</td><td colspan="4"></td></tr><tr><td>Workgroup n</td><td colspan="4"></td></tr></table>



---


<!-- Page 5 -->



# Wavefronts on AMD GCN GPUs




Wavefront 64 work items (threads)




AMD GCN Compute Units execute wavefronts, not work items.




Each wavefront has instructions in various classes:




- Vector ALU (VALU): 64-wide ALU instruction.




- FP16, FP32, FP64, integer, bitwise operators can all be VALU.




- Each lane can operate on a different value. Individual lanes can be masked off.




- Vector Memory (VMEM): 64-wide memory instruction.




- Each lane can touch a different location. Individual lanes can be masked off.




- Local Data Share (LDS): 64-wide memory operations to per-CU scratchpad.




- Each lane can touch a different location. Individual lanes can be masked off.




- Scalar ALU (SALU): ALU operation if every thread is working on identical data. Has its own registers.




- Scalar Memory (SMEM): Identical memory operation in all lanes. Uses scalar register file.




- Branch: Used if the entire wavefront wants to branch.




- Per-thread branching will run both sides of the branch with different lane masks.




- Internal: Wavefront bookkeeping. NOPs, workgroup barriers, wait-for-memory, etc.




---


<!-- Page 6 -->



# An Example SIMT Kernel




---


<!-- Page 7 -->



SIMT Shifted Copy Kernel in HIP




Every thread copies a float from array in[] to array out[]




```code
__global__ void shifted_copy (float *in, float *out) {
    size_t gid = blockDim.x * blockIdx.x + threadIdx.x
    out[gid] = in[gid+4];
}
```




SIMT programming model implies parallelism between threads.




Every HIP Thread reads one value and writes one value, based on its global thread ID




---


<!-- Page 8 -->



SIMT Copy Kernel in AMD GCN Assembly




```code
__global__ void shifted_copy (float *in, float *out) {
    size_t gid = blockDim.x * blockIdx.x + threadIdx.x
    out[gid] = in[gid + 4];
}
```




- Skipping some function prologue. Starting state:




- Scalar registers SGPR5 and SGPR4 concatenate together to hold pointer to kernel argument structure.
- Vector registers VGPR3 and VGPR2 concatenated together hold the per-thread global ID variable “gid”




```code
s_load_dwordx4 s[0:3], s[4:5], 0 ; Load in[] to SGPR1:SGPR0 and out[] into SGPR3:SGPR2.
v_lshlrev_b64 v[2:3], 2, v[2:3] ; GID*=4 for float array offset.
s_waitcnt lgkmcnt(0) ; Wavefront does not proceed until previous SMEM access completes.
s_add_u32 s0, 16, s0 ; Add 16 to SGPR0 to shift in[] four floats over. May cause carry-out.
s_addc_u32 s1, 0, s1 ; Add any carry from the previous instruction into SGPR1.
v_add_co_u32 v0, s0, v2 ; Add low GID*4 to low in[]. Store in VGPR0.
v_addc_co_u32 v1, s1, v3 ; Add high GID*4 to high in[] with carry-in. Store in VGPR1.
global_load_dword v4, v[0:1] ; Read 64 floats from 64 locations from VGPR1:VGPR0 into VGPR4.
v_add_co_u32 v0, s2, v2 ; Add low GID*4 to low out[]. Store in VGPR0.
v_addc_co_u32 v1, s3, v3 ; Add high GID*4 to high out[] with carry-in. Store in VGPR1.
s_waitcnt vmcnt(0) ; Wavefront does not proceed until all previous VMEM accesses complete.
global_store_dword v[0:1], v4 ; Store 64 floats from VGR4 into 64 locations from VGPR1:VGPR0.
s_endpgm ; This wavefront is done. Exit when the store completes.
```




---


<!-- Page 9 -->



SIMT Copy Kernel in AMD GCN Assembly




```code
__global__ void shifted_copy (float *in, float *out) {
    size_t gid = blockDim.x * blockIdx.x + threadIdx.x
    out[gid] = in[gid + 4];
}
```




- Skipping some function prologue. Starting state:




- Scalar registers SGPR5 and SGPR4 concatenate together to hold pointer to kernel argument structure.
- Vector registers VGPR3 and VGPR2 concatenated together hold the per-thread GID variable







---


<!-- Page 10 -->



[AMD Official Use Only - Internal Distribution Only]




---


