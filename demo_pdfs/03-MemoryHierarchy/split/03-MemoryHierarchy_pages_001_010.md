# 03-MemoryHierarchy - Pages 1-10

<!-- Page 1 -->



# CDNA2 Memory Hierarchy




Alessandro Fanfarillo




---


<!-- Page 2 -->



# A Team Effort




Thanks to all former contributors to this presentation:




Paul Bauman




Noel Chalmers




Nicholas Curtis




Chip Freitag




Joseph Greathouse




Nicholas Malaya




Damon McDougall




Scott Moe




René van Oostrum




Noah Wolfe




---


<!-- Page 3 -->



# Agenda




- Introduction to CDNA2 Compute Unit architecture




- Memory hierarchy in CDNA2 Compute Units




- Occupancy considerations with examples




---


<!-- Page 4 -->



# AMD CDNA2 GPU Hardware Layout




Command Queue




Queues reside in user-visible DRAM




Command Queue




Command Processor




Shader Engine (SE0)




Shader Engine (SE1)




Shader Engine (SE3)




Shader Engine (SE2)




---


<!-- Page 5 -->



# AMD CDNA2 GPU Hardware Layout




Command Queue




Queues reside in user-visible DRAM




Command Queue



Command Processor

<table><tr><td>CU</td><td>CU</td></tr><tr><td>CU</td><td>CU</td></tr><tr><td>CU</td><td>CU</td></tr><tr><td>CU</td><td>CU</td></tr><tr><td>CU</td><td>CU</td></tr><tr><td>CU</td><td>CU</td></tr><tr><td>CU</td><td>CU</td></tr><tr><td>CU</td><td>CU</td></tr></table>

workload manager



<table><tr><td>CU</td><td>CU</td></tr><tr><td>CU</td><td>CU</td></tr><tr><td>CU</td><td>CU</td></tr><tr><td>CU</td><td>CU</td></tr><tr><td>CU</td><td>CU</td></tr><tr><td>CU</td><td>CU</td></tr><tr><td>CU</td><td>CU</td></tr><tr><td>CU</td><td>CU</td></tr></table>

L2



<table><tr><td>CU</td><td>CU</td></tr><tr><td>CU</td><td>CU</td></tr><tr><td>CU</td><td>CU</td></tr><tr><td>CU</td><td>CU</td></tr><tr><td>CU</td><td>CU</td></tr><tr><td>CU</td><td>CU</td></tr><tr><td>CU</td><td>CU</td></tr><tr><td>CU</td><td>CU</td></tr></table>

workload manager



<table><tr><td>CU</td><td>CU</td></tr><tr><td>CU</td><td>CU</td></tr><tr><td>CU</td><td>CU</td></tr><tr><td>CU</td><td>CU</td></tr><tr><td>CU</td><td>CU</td></tr><tr><td>CU</td><td>CU</td></tr><tr><td>CU</td><td>CU</td></tr><tr><td>CU</td><td>CU</td></tr></table>

workload manager




---


<!-- Page 6 -->



[Public]




GPU Memory, I/O, and Connectivity



![Figure 1](figures/page_006_fig_01.png)



---


<!-- Page 7 -->



# The CDNA2 Compute Unit (CU)




# Compute Unit (CU)




- The command processor sends work packages (i.e. workgroups of work-items in HIP) to the Compute Units (CUs)




Workgroups are executed in wavefronts (groups of 64 work-items on a SIMD)




All wavefronts in a workgroup reside on the same CU




The CU's scheduler can hold wavefronts from many workgroups




At most 32 wavefronts total per CU (8 per SIMD)




---


<!-- Page 8 -->



# The CDNA2 Compute Unit (CU) – Scalar Unit




sL1d Cache




Scalar Unit




SGPR




- Scalar Unit (SU)




- Shared by all work-items in each wavefront, accessed on a per-wavefront level




- Work-items in a wavefront performing the exact same operation can offload this instruction to the SU




- Used for control flow, pointer arithmetic, dispatch a common constant value, etc. Only INT32 capability, no FP




- SU connected to read/write sL1d cache of 16 KiB (not really into the CU but directly attached)




- Has its own pool of Scalar General-Purpose Register (SGPR) file, 12.5KiB per CU, 800 per SIMD




- Maximum of 102 SGPRs / wavefront allocated in groups of 16




---


<!-- Page 9 -->



# The CDNA2 Compute Unit (CU) – Vector ALU



<table><tr><td>sL1d Cache</td><td>SIMD0</td><td>SIMD1</td><td>SIMD2</td><td>SIMD3</td></tr><tr><td>Scalar Unit</td><td>VGPR</td><td>VGPR</td><td>VGPR</td><td>VGPR</td></tr><tr><td>SGPR</td><td></td><td></td><td></td><td></td></tr></table>

- SIMD Units / Execution Units (EU) / VALU




4x SIMD vector units (each 16 lanes wide)




- Each SIMD performs vector logical, integer, FP16, FP32, FP64 operations. FMAs for FP16, FP32, FP64. MFMAAs for FP16, BF16, FP32, FP64. Packed FP16 and FP32.




- Two pools of Vector General-Purpose Registers (VGPRs): regular VGPRs and Accumulation VGPRs (AccVGPRs)




- Maximum of 512 registers per SIMD – each register is 64x 4-byte entries. For 64 bits operations 2 contiguous registers need to be used.




- A wavefront can use up to 256 VGPRs (and 256 AccVGPRs)




- Instruction buffer for 8 wavefronts on each SIMD unit. Each wavefront is local to a single SIMD unit, not spread among the four




---


<!-- Page 10 -->



# The CDNA2 Compute Unit (CU) – Matrix Cores




- Matrix Fused Multiply Add (MFMA) instructions operate on a per-wavefront basis rather than on a per-thread basis




- For more info about MFMA instructions and register usage check out the AMD Matrix Instruction Calculator: https://github.com/RadeonOpenCompute/amd_matrix_instruction_calculator




- Matrix Cores leveraged is several ways:




Libraries: rocBLAS, rocWMMA




- Use compiler intrinsics




- HIP kernels with inline assembly




- Write kernels completely in assembly…




- More details on how to use MFMA instructions: https://gpuopen.com/learn/amd-lab-notes/amd-lab-notes-matrix-cores-readme



![Figure 1](figures/page_010_fig_01.png)



---


