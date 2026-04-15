# 2020-04-14 - Memory, IO, and CU Architecture on gfx9 GPUs - Pages 61-70

<!-- Page 61 -->



# On-chip Memory System



<table><tr><td>Graphics Core</td><td></td><td></td><td></td><td></td><td></td></tr><tr><td>Read/Write L2 Cache</td><td>DMA Engine</td><td>DMA Engine</td><td>DMA Engine</td><td>DMA Engine</td><td>DMA Engine</td></tr><tr><td></td><td colspan="2"><= Vega 20: 2 DMA Engines<br/>MI100: 8 DMA Engines<br/>MI200: 5 DMA Engines</td><td colspan="3">Vega 10: 2 queue slots / engine<br/>>= Vega 20: 8 queue slots/engine</td></tr><tr><td></td><td colspan="5">SoC Routing Network</td></tr><tr><td>PCIe® Controllers</td><td colspan="2">Memory Controllers</td><td colspan="3">xGMI Controller</td></tr><tr><td>PCIe® Links</td><td colspan="2">HBM/GDDR Memory</td><td colspan="3">xGMI Interconnect</td></tr></table>



---


<!-- Page 62 -->



[AMD Official Use Only - Internal Distribution Only]




# AMD




---


<!-- Page 63 -->



# Comparing AMD GPUs




---


<!-- Page 64 -->



# AMD "Graphics Core Next" GPU Generations




Multiple "GCN" generations released since then




- 2012: "Southern Islands"




- 2013: "Sea Islands"




- 2015: "Volcanic Islands"




- 2017: "Vega"




Some things stay the same across these generations:




- Compute Unit (CU) parallelism




- 64-wide hardware vector processors




- Mostly in-order execution




- Fine-grained multithreading for latency hiding




Some things change:




- Opcodes added & removed




- Changes to how GPU interacts with compilers & drivers




- FP64 execution rate, packed FP16 math, GEMM & dot product acceleration, inter-lane communication mechanisms




---


<!-- Page 65 -->



# GCN Generations – Compiler and Driver View




The AMDGPU LLVM compiler backend defines GCN generations numerically, rather than with code names.




Major ISA versions are covered in new ISA manuals.




Different minor ISA versions tell the compiler how to work around bugs, how to generate more optimal code for a device class, how to enable specific features, etc.




For example:




801 vs. 802: Former allows precise page faults




802 vs. 803: Former uses SW workarounds for HW bugs




900→906: New instructions for dot products




906→908: SGEMM and HGEMM Acceleration




gfx6 ("Southern Islands")




- gfx600 – "Tahiti" dGPU




- gfx601 – "Pitcairn" dGPU




gfx7 ("Sea Islands")




- gfx701 – "Hawaii" dGPU




gfx8 ("Volcanic Islands" / GCN3 ISA)




- gfx801 – "Carrizo" iGPU




- gfx802 – "Tonga" dGPU




- gfx803 – "Fiji" and "Polaris" dGPUs




gfx9 ("Vega" ISA)




- gfx900 – "Vega 10" dGPU




- gfx902 – "Raven Ridge" iGPU




- gfx904 – "Vega 12" dGPU




- gfx906 – "Vega 20" dGPU




- gfx908 – "MI100" dGPU




- gfx90a – "MI200" dGPU




---


<!-- Page 66 -->



# AMD GPU Speeds Comparison



![Figure 1](figures/page_066_fig_01.png)



![Figure 2](figures/page_066_fig_02.png)

<table><tr><td></td><td>“Vega 10”</td><td>“Vega 20”</td><td>“MI100”</td><td>“MI200”</td></tr><tr><td></td><td>gfx900</td><td>gfx906</td><td>gfx908</td><td>gfx90a</td></tr><tr><td>Compute Units</td><td>64</td><td>64</td><td>128 (120)</td><td>112 (110 or 96) per die</td></tr><tr><td>Peak Frequency (GHz)</td><td>1.5 @ 220W TGP</td><td>1.8 @ 225 W TGP</td><td>(Estimate) 1.55 @ 255 W TGP</td><td>(Estimate) 1.3 @ 215 W TGP</td></tr><tr><td>Trad. FP32 FLOP/CU/cycle</td><td>128</td><td>128</td><td>128</td><td>128</td></tr><tr><td>Trad. FP64 FLOP/CU/cycle</td><td>8</td><td>64</td><td>64</td><td>128</td></tr><tr><td>Packed FP16 FLOP/CU/cycle</td><td>256</td><td>256</td><td>256</td><td>256</td></tr><tr><td>FP16/int16 dot Op/CU/cycle</td><td>-</td><td>256</td><td>256</td><td>256</td></tr><tr><td>int8 dot Op/CU/cycle</td><td>-</td><td>512</td><td>512</td><td>512</td></tr><tr><td>int4 dot Op/CU/cycle</td><td>-</td><td>1024</td><td>1024</td><td>1024</td></tr><tr><td>FP32 GEMM FLOP/CU/cycle</td><td>-</td><td>-</td><td>256</td><td>256</td></tr><tr><td>FP16/int8 GEMM Op/CU/cycle</td><td>-</td><td>-</td><td>1024</td><td>1024</td></tr><tr><td>BF16 GEMM FLOP/CU/cycle</td><td>-</td><td>-</td><td>512</td><td>1024</td></tr><tr><td>FP64 GEMM FLOP/CU/cycle</td><td>-</td><td>-</td><td>-</td><td>256</td></tr><tr><td>Packed FP32 FLOP/CU/cycle</td><td>-</td><td>-</td><td>-</td><td>256</td></tr></table>



---


<!-- Page 67 -->



# AMD GPU Feeds Comparison



![Figure 1](figures/page_067_fig_01.png)



![Figure 2](figures/page_067_fig_02.png)

<table><tr><td></td><td>“Vega 10”</td><td>“Vega 20”</td><td>“MI100”</td><td>“MI200”</td></tr><tr><td>Peak HBM DRAM BW</td><td>484 GB/s</td><td>1 TB/s</td><td>1.2 TB/s (Est.)</td><td>1.6 TB/s per die (Est.)</td></tr><tr><td>Max HBM Memory Size</td><td>16 GiB</td><td>32 GiB</td><td>32 GiB</td><td>64 GiB per die</td></tr><tr><td>Bidirectional PCIe® Speed</td><td>30 GB/s</td><td>60 GB/s (100 with ESM)</td><td>60 GB/s (100 with ESM)</td><td>60 GB/s (100 with ESM)</td></tr><tr><td>Infinity Fabric™ Links</td><td>-</td><td>2</td><td>6</td><td>8 (out of module)</td></tr><tr><td>Bidirectional xGMI Speed</td><td>-</td><td>100 GB/s</td><td>100 GB/s</td><td>128 GB/s</td></tr><tr><td>Virtual / Physical Address Bits</td><td>48 / 40</td><td>48 / 44</td><td>48 / 44</td><td>48 / 48</td></tr><tr><td>Vector Register Space / CU</td><td>256 KiB</td><td>256 KiB</td><td>256 KiB + 256 KiB GEMM Regs</td><td>512 KiB</td></tr><tr><td>L2 Cache Size</td><td>4 MiB</td><td>4 MiB</td><td>8 MiB</td><td>8 MiB per die</td></tr><tr><td>L2 Cache Line Size</td><td>64 bytes</td><td>64 bytes</td><td>64 bytes</td><td>128 bytes</td></tr><tr><td>L2 Bandwidth</td><td>1 KiB/cycle read<br/>1 KiB/cycle write</td><td>1 KiB/cycle read<br/>1 KiB/cycle write</td><td>2 KiB/cycle read<br/>2 KiB/cycle write</td><td>4 KiB/cycle read<br/>2 KiB/cycle write</td></tr><tr><td>L2 Atomic Math Ops</td><td>Integer</td><td>Integer</td><td>+FP32, FP16</td><td>+FP64</td></tr><tr><td>L2 TLB Reach (2 MiB pages)</td><td>64 GiB</td><td>64 GiB</td><td>64 GiB</td><td>64 GiB</td></tr><tr><td>L2 TLB Translation BW</td><td>4 lookups / cycle</td><td>4 lookups / cycle</td><td>4 lookups / cycle</td><td>8 lookups / cycle</td></tr></table>



---


<!-- Page 68 -->



Software Terminology and Translation Key

<table><tr><td>Nvidia/CUDA Terminology</td><td>AMD Terminology</td><td>Description</td></tr><tr><td>Kernel</td><td>Kernel</td><td>Functions launched to the GPU that are executed by multiple parallel workers on the GPU. Kernels can work in parallel with CPU.</td></tr><tr><td>Warp</td><td>Wavefront</td><td>Collection of operations that execute in lockstep, run the same instructions, and follow the same control-flow path. Individual lanes can be masked off. Think of this as a vector thread. A 64-wide wavefront is a 64-wide vector op.</td></tr><tr><td>Thread block</td><td>Workgroup</td><td>Group of wavefronts that will be on the GPU at the same time. Can synchronize together and communicate through local memory.</td></tr><tr><td>Shared memory</td><td>Local memory</td><td>Scratchpad that allows communication between wavefronts in a workgroup.</td></tr><tr><td>Thread</td><td>Work item / Thread</td><td>Individual lane in a wavefront. On AMD GPUs, must run in lockstep with other work items in the wavefront. Lanes can be individually masked off.GPU programming models can treat this as a separate thread of execution, though no guarantee of sub-wavefront forward progress.</td></tr><tr><td>Local memory</td><td>Private memory</td><td>Per-thread private memory, often mapped to registers.</td></tr></table>



---


<!-- Page 69 -->



# Hardware Terminology – Translation key if you are familiar with Nvidia GPUs



<table><tr><td>Nvidia/CUDA Terminology</td><td>AMD Terminology</td><td>Description</td></tr><tr><td>Streaming Multiprocessor</td><td>Compute Unit (CU)</td><td>One of many parallel vector processors in a GPU that contain parallel ALUs. All waves in a workgroups are assigned to the same CU.</td></tr><tr><td>Shared Memory</td><td>Local Data Share (LDS)</td><td>Scratchpad RAMs that hold local memory values.</td></tr><tr><td>Global Memory</td><td>Global Memory</td><td>DRAM memory accessible by the GPU that goes through some layers cache</td></tr><tr><td>Special Function Unit</td><td>N/A</td><td>Nvidia GPUs used a special execution pipe for transcendentalss and other special intrinsics. AMD GPUs execute them as regular vector instructions.</td></tr></table>



---


<!-- Page 70 -->



# DISCLAIMER




# DISCLAIMER




The information contained herein is for informational purposes only, and is subject to change without notice. While every precaution has been taken in the preparation of this document, it may contain technical inaccuracies, omissions and typographical errors, and AMD is under no obligation to update or otherwise correct this information. Advanced Micro Devices, Inc. makes no representations or warranties with respect to the accuracy or completeness of the contents of this document, and assumes no liability of any kind, including the implied warranties of noninfringement, merchantability or fitness for particular purposes, with respect to the operation or use of AMD hardware, software or other products described herein. No license, including implied or arising by estoppel, to any intellectual property rights is granted by this document. Terms and limitations applicable to the purchase or use of AMD's products are as set forth in a signed agreement between the parties or in AMD's Standard Terms and Conditions of Sale. GD-18




©2020 Advanced Micro Devices, Inc. All rights reserved. AMD, the AMD Arrow logo, Radeon, Radeon Instinct, and combinations thereof are trademarks of Advanced Micro Devices, Inc. PCIe is a registered trademark of PCI-SIG Corporation. Other product names used in this publication are for identification purposes only and may be trademarks of their respective companies.



