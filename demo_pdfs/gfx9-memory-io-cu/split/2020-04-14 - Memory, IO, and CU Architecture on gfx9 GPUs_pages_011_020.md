# 2020-04-14 - Memory, IO, and CU Architecture on gfx9 GPUs - Pages 11-20

<!-- Page 11 -->



An Example SIMT Kernel with Branching




---


<!-- Page 12 -->



SIMT Shifted Copy Kernel in HIP




Conditionally copy some values from array in[] to array out[]




```code
__global__ void conditional_copy (double *in, double *out) {
    size_t gid = blockDim.x * blockIdx.x + threadIdx.x
    if (in[gid] > 0)
        out[gid] = in[gid];
}
```




Each HIP Thread can read a different value, some will go into the conditional statement




---


<!-- Page 13 -->



[AMD Official Use Only - Internal Distribution Only]




SIMT Copy Kernel in AMD GCN Assembly




```code
__global__ void conditional_copy (double *in, double *out) {
    size_t gid = blockDim.x * blockIdx.x + threadIdx.x
    if (in[gid] > 0.)
        out[gid] = in[gid];
}
```




- Skipping some function prologue. Starting state:




- Scalar registers SGPR5 and SGPR4 concatenate together to hold pointer to kernel argument structure.




- Vector registers VGPR3 and VGPR2 concatenated together hold the per-thread global ID variable “gid”




s_load_dwordx4 s[0:3], s[4:5], 0 ; Load in[] to SGPR1:SGPR0 and out[] into SGPR3:SGPR2.




v_lshlrev_b64 v[2:3], 3, v[2:3] ; GID*=8 for double array offset.




s_waitcnt lgmcnt(0) ; Wavefront does not proceed until previous SMEM access completes.




v_add_co_u32 v0, s0, v2 ; Add low GID*8 to low in[]. Store in VGPR0.




v_addc_co_u32 v1, s1, v3 ; Add high GID*8 to high in[] with carry-in. Store in VGPR1.




global_load_dwordx2 v[4:5], v[0:1] ; Read 64 doubles from 64 locations from VGPR1:VGPR0 into VGPR5:VGPR4.




s_waitcnt vmcnt(0) ; Wavefront does not proceed until all previous VMEM accesses complete.




v_cmp_lt_f64 vcc, 0, v[4:5] ; Set this thread’s bit in VCC if 0 < VGPR[4:5] (0. < in[gid]).




s_and_saveexec_b64 s[4:5], vcc ; Save old EXEC into S[4:5]. AND VCC into the EXEC mask.




s_cbranch_execz BB0_2 ; If EXEC mask is all 0, branch to BB0_2 label.




v_add_co_u32 v0, s2, v2 ; Add low GID*8 to low out[] if this thread’s EXEC bit == 1.




v_addc_co_u32 v1, s3, v3 ; Add high GID*8 to high out[] with carry-in if EXEC bit == 1.




global_store_dword v[0:1], v[4:5] ; Store to output address if this thread’s EXEC bit == 1.




BB0_2:




s_or_b64 exec, exec, s[4:5] ; OR saved-off EXEC mask back into the current EXEC mask.




s_endpgm ; This wavefront is done. Exit when the store completes.




---


<!-- Page 14 -->



SIMT Branching Mechanisms




```code
v_cmp_lt_f64 vcc, 0, v[4:5] ; Set this thread’s bit in VCC if 0 < VGPR[4:5] (0. < in[gid]).
s_and_saveexec_b64 s[4:5], vcc ; Save old EXEC into S[4:5]. AND VCC into the EXEC mask.
s_cbranch_execz BB0_2 ; If EXEC mask is all 0, branch to BB0_2 label.
v_add_co_u32 v0, s2, v2 ; Add low GID*8 to low out[] if this thread’s EXEC bit == 1.
v_addc_co_u32 v1, s3, v3 ; Add high GID*8 to high out[] with carry-in if EXEC bit == 1.
global_store_dwordx2 v[0:1], v[4:5] ; Store to output address if this thread’s EXEC bit == 1.
BB0_2:
s_or_b64 exec, exec, s[4:5] ; OR saved-off EXEC mask back into the current EXEC mask.
```

<table><tr><td colspan="4">EXEC</td><td colspan="4">VCC</td><td>EXECZ</td></tr><tr><td>1</td><td>0</td><td>1</td><td>0</td><td>AND</td><td>1</td><td>0</td><td>1</td><td>0</td></tr><tr><td colspan="4">2 EXEC bits == 1: Two stores</td><td></td><td></td><td></td><td></td><td></td></tr><tr><td colspan="4">VGPR[4:5]</td><td colspan="4">SGPR[4:5]</td><td></td></tr><tr><td>3.14</td><td>-1</td><td>1.2</td><td>0</td><td colspan="4">0xf</td><td></td></tr></table>



---


<!-- Page 15 -->



SIMT Branching Mechanisms




```code
v_cmp_lt_f64 vcc, 0, v[4:5] ; Set this thread’s bit in VCC if 0 < VGPR[4:5] (0. < in[gid]).
s_and_saveexec_b64 s[4:5], vcc ; Save old EXEC into S[4:5]. AND VCC into the EXEC mask.
s_cbranch_execz BB0_2     ; If EXEC mask is all 0, branch to BB0_2 label.
v_add_co_u32 v0, s2, v2   ; Add low GID*8 to low out[] if this thread’s EXEC bit == 1.
v_addc_co_u32 v1, s3, v3  ; Add high GID*8 to high out[] with carry-in if EXEC bit == 1.
global_store_dwordx2 v[0:1], v[4:5] ; Store to output address if this thread’s EXEC bit == 1.
BB0_2:
s_or_b64 exec, exec, s[4:5] ; OR saved-off EXEC mask back into the current EXEC mask.
```





---


<!-- Page 16 -->



SIMT Branching Mechanisms




```code
v_cmp_lt_f64 vcc, 0, v[4:5] ← Vector ALU
s_and_saveexec_b64 s[4:5], vcc ← Scalar ALU
s_cbranch_execz BB0_2 ← Branch
v_add_co_u32 v0, s2, v2
v_addc_co_u32 v1, s3, v3
global_store_dwordx2 v[0:1], v[4:5]
BB0_2:
s_or_b64 exec, exec, s[4:5]
```




---


<!-- Page 17 -->



# GCN Compute Unit Internals




---


<!-- Page 18 -->



# Wavefronts in a Sea of Compute Units




HSA Queue




HSA Queue




Command Processor



<table><tr><td></td><td>CU</td><td></td><td>CU</td><td></td></tr><tr><td></td><td>CU</td><td></td><td>CU</td><td></td></tr><tr><td></td><td>CU</td><td></td><td>CU</td><td></td></tr><tr><td></td><td>CU</td><td></td><td>CU</td><td></td></tr><tr><td></td><td>CU</td><td></td><td>CU</td><td></td></tr><tr><td></td><td>CU</td><td></td><td>CU</td><td></td></tr><tr><td></td><td>CU</td><td></td><td>CU</td><td></td></tr><tr><td></td><td>CU</td><td></td><td>CU</td><td></td></tr></table>

SPI (SE0)



<table><tr><td></td><td>CU</td><td></td><td>CU</td><td></td></tr><tr><td></td><td>CU</td><td></td><td>CU</td><td></td></tr><tr><td></td><td>CU</td><td></td><td>CU</td><td></td></tr><tr><td></td><td>CU</td><td></td><td>CU</td><td></td></tr><tr><td></td><td>CU</td><td></td><td>CU</td><td></td></tr><tr><td></td><td>CU</td><td></td><td>CU</td><td></td></tr><tr><td></td><td>CU</td><td></td><td>CU</td><td></td></tr><tr><td></td><td>CU</td><td></td><td>CU</td><td></td></tr></table>

SPI (SE1)



<table><tr><td></td><td>CU</td><td></td><td>CU</td><td></td></tr><tr><td></td><td>CU</td><td></td><td>CU</td><td></td></tr><tr><td></td><td>CU</td><td></td><td>CU</td><td></td></tr><tr><td></td><td>CU</td><td></td><td>CU</td><td></td></tr><tr><td></td><td>CU</td><td></td><td>CU</td><td></td></tr><tr><td></td><td>CU</td><td></td><td>CU</td><td></td></tr><tr><td></td><td>CU</td><td></td><td>CU</td><td></td></tr><tr><td></td><td>CU</td><td></td><td>CU</td><td></td></tr></table>

SPI (SE3)



<table><tr><td></td><td>CU</td><td></td><td>CU</td><td></td></tr><tr><td></td><td>CU</td><td></td><td>CU</td><td></td></tr><tr><td></td><td>CU</td><td></td><td>CU</td><td></td></tr><tr><td></td><td>CU</td><td></td><td>CU</td><td></td></tr><tr><td></td><td>CU</td><td></td><td>CU</td><td></td></tr><tr><td></td><td>CU</td><td></td><td>CU</td><td></td></tr><tr><td></td><td>CU</td><td></td><td>CU</td><td></td></tr><tr><td></td><td>CU</td><td></td><td>CU</td><td></td></tr></table>

SPI (SE2)




---


<!-- Page 19 -->



# Inside a Compute Unit – Wavefront Slots



Compute Unit

<table><tr><td>VMID 1, K0, WG0, WF0</td><td>VMID 1, K0, WG0, WF1</td><td>VMID 1, K0, WG0, WF2</td><td>VMID 1, K0, WG0, WF3</td></tr><tr><td>VMID 2, K0, WG0, WF0</td><td>VMID 2, K0, WG0, WF1</td><td>VMID 2, K0, WG0, WF2</td><td>VMID 2, K0, WG0, WF3</td></tr><tr><td>VMID 3, K0, WG0, WF0</td><td>VMID 3, K0, WG0, WF1</td><td>VMID 3, K0, WG0, WF2</td><td>VMID 3, K0, WG0, WF3</td></tr><tr><td>VMID 4, K0, WG0, WF0</td><td>VMID 4, K0, WG0, WF1</td><td>VMID 5, K0, WG0, WF0</td><td>VMID 5, K0, WG0, WF1</td></tr><tr><td>VMID 5, K0, WG0, WF2</td><td>VMID 5, K0, WG0, WF3</td><td>VMID 5, K0, WG0, WF4</td><td>VMID 5, K0, WG0, WF5</td></tr><tr><td>VMID 5, K0, WG0, WF6</td><td>VMID 5, K1, WG0, WF7</td><td>VMID 5, K1, WG0, WF8</td><td>VMID 5, K1, WG0, WF9</td></tr><tr><td>VMID 1, K1, WG0, WF0</td><td>VMID 1, K1, WG0, WF1</td><td>VMID 1, K1, WG0, WF2</td><td>VMID 1, K1, WG0, WF3</td></tr><tr><td>VMID 1, K1, WG1, WF0</td><td>VMID 1, K1, WG1, WF1</td><td>VMID 1, K1, WG1, WF2</td><td>VMID 1, K1, WG1, WF3</td></tr></table>

Four (4) sets of wavefront slots per CU




Up to eight (8) wavefronts in each set: VMID, PC, workgroup, pointers into register file, etc.




Up to 16 VMIDs in a CU simultaneously.




Any wavefront can be from a different process, kernel, workgroup.




Filled by SPI when launching the wavefront, emptied by shader running s_endpgm instruction.




None




---


<!-- Page 20 -->



# Compute Unit Internals



Compute Unit

<table><tr><td>Wave Slots</td><td>Wave Slots</td><td>Wave Slots</td><td>Wave Slots</td></tr></table>



---


