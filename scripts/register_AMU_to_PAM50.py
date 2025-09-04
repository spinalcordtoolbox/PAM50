
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reproducible registration script (no CLI args).
Pipeline:
  1) Step-0 (label-based, Tx_Ty_Tz) AMU -> PAM50 to get initial rigid/translation alignment.
  2) Apply step-0 warp to AMU images to bring them into PAM50 space.
  3) In PAM50 space, extend AMU volumes by copying top/bottom slices to match PAM50 cord extent.
  4) Step-1 (seg slicereg, poly=2) using the extended PAM50-space AMU seg vs PAM50 seg.
  5) Apply warps sequentially to originals: first step-0, then step-1.
  6) Symmetrize outputs; threshold T2* negatives and cast to uint16.

Assumptions:
- SCT binaries in PATH: sct_label_utils, sct_register_multimodal, sct_apply_transfo, sct_maths
- symmetrize_cord_segmentation.py is located in the SAME directory as this script
- Edit CONFIG below, then just run the script.
"""
import os
import subprocess
from pathlib import Path
import nibabel as nib
import numpy as np

# =========================
# CONFIG (edit once)
# =========================
SCT_DIR = os.environ.get("SCT_DIR", "/opt/sct")  # Adjust if not using env var
AMU_T2S = Path(os.path.expanduser("~/Desktop/MNI-POLY-AMU/AMU15_T2star_sym.nii.gz"))
AMU_GM  = Path(os.path.expanduser("~/Desktop/MNI-POLY-AMU/AMU15_GW_sym.nii.gz"))  # GM+WM segmentation (moving seg)

PAM50_T2  = Path(f"{SCT_DIR}/data/PAM50/template/PAM50_t2.nii.gz")
PAM50_SEG = Path(f"{SCT_DIR}/data/PAM50/template/PAM50_t2_seg.nii.gz")

# Label coordinates (x,y,z,val) for step-0 label-based alignment
LABEL_AMU = (75, 75, 965, 1)
LABEL_PAM = (70, 70, 959, 1)

# I/O
OUTDIR = Path("./out")
QCDIR  = Path("./qc")
EXTEND_TO_CORD = True  # Copy edge slices AFTER step-0, in PAM50 space, before step-1
# =========================

HERE = Path(__file__).resolve().parent
SYM_SCRIPT = HERE / "symmetrize_cord_segmentation.py"

def run(cmd, check=True):
    print("+", " ".join(map(str, cmd)), flush=True)
    res = subprocess.run(list(map(str, cmd)), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    print(res.stdout)
    if check and res.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(map(str, cmd))}")
    return res

def copy_edge_slices_to_match(moving_path: Path, ref_path: Path, out_path: Path):
    """
    Make the moving image's Z dimension match the reference by either:
      - Cropping (if moving is longer in Z)
      - Padding and copying edge slices (if moving is shorter in Z)
    Alignment uses NZ-span centers to preserve the cord region.
    """
    img_m = nib.load(str(moving_path))
    img_r = nib.load(str(ref_path))
    data_m = img_m.get_fdata()
    data_r = img_r.get_fdata()

    if data_m.ndim != 3 or data_r.ndim != 3:
        raise ValueError("Input images must be 3D.")

    def nz_bounds(arr):
        proj = np.sum(np.sum(arr != 0, axis=0), axis=0)
        nz = np.where(proj > 0)[0]
        if nz.size == 0:
            return 0, arr.shape[2] - 1
        return int(nz.min()), int(nz.max())

    zmin_m, zmax_m = nz_bounds(data_m)
    zmin_r, zmax_r = nz_bounds(data_r)
    z_m = data_m.shape[2]
    z_r = data_r.shape[2]

    c_m = 0.5 * (zmin_m + zmax_m)
    c_r = 0.5 * (zmin_r + zmax_r)

    if z_m > z_r:
        # Crop moving to match reference length
        start = int(round(c_m - z_r / 2.0))
        start = max(0, min(start, z_m - z_r))
        data_ext = data_m[:, :, start:start + z_r].copy()
    elif z_m < z_r:
        # Pad moving to match reference length, then copy edges
        data_ext = np.zeros((data_m.shape[0], data_m.shape[1], z_r), dtype=data_m.dtype)
        insert_start = int(round((z_r / 2.0) - (c_m)))
        insert_start = max(0, min(insert_start, z_r - z_m))
        data_ext[:, :, insert_start:insert_start + z_m] = data_m

        proj = np.any(np.any(data_ext != 0, axis=0), axis=0)
        first_nz = np.argmax(proj)
        if first_nz > 0:
            data_ext[:, :, :first_nz] = np.repeat(data_ext[:, :, first_nz:first_nz + 1], first_nz, axis=2)
        proj = np.any(np.any(data_ext != 0, axis=0), axis=0)
        last_nz = len(proj) - 1 - np.argmax(proj[::-1])
        if last_nz < data_ext.shape[2] - 1:
            fill_len = data_ext.shape[2] - 1 - last_nz
            data_ext[:, :, last_nz + 1:] = np.repeat(data_ext[:, :, last_nz:last_nz + 1], fill_len, axis=2)
    else:
        data_ext = data_m.copy()
        proj = np.any(np.any(data_ext != 0, axis=0), axis=0)
        first_nz = np.argmax(proj)
        last_nz = len(proj) - 1 - np.argmax(proj[::-1])
        if first_nz > 0:
            data_ext[:, :, :first_nz] = np.repeat(data_ext[:, :, first_nz:first_nz + 1], first_nz, axis=2)
        if last_nz < data_ext.shape[2] - 1:
            fill_len = data_ext.shape[2] - 1 - last_nz
            data_ext[:, :, last_nz + 1:] = np.repeat(data_ext[:, :, last_nz:last_nz + 1], fill_len, axis=2)

    nib.Nifti1Image(data_ext, img_m.affine, img_m.header).to_filename(str(out_path))
    return out_path

def main():
    OUTDIR.mkdir(parents=True, exist_ok=True)
    QCDIR.mkdir(parents=True, exist_ok=True)
    workdir = OUTDIR / "work"
    workdir.mkdir(parents=True, exist_ok=True)

    # label-based registration (Tx_Ty_Tz) followed by slicereg
    label_amu = (workdir / "label_AMU.nii.gz").resolve()
    label_pam = (workdir / "label_PAM50.nii.gz").resolve()
    run(["sct_label_utils", "-i", AMU_T2S, "-create", ",".join(map(str, LABEL_AMU)), "-o", label_amu])
    run(["sct_label_utils", "-i", PAM50_T2, "-create", ",".join(map(str, LABEL_PAM)), "-o", label_pam])

    # Run only step=0 to get initial warp
    cwd = os.getcwd()
    os.chdir(workdir)
    try:
        run([
            "sct_register_multimodal",
            "-i", AMU_T2S,
            "-iseg", AMU_GM,
            "-ilabel", label_amu,
            "-d", PAM50_T2,
            "-dseg", PAM50_SEG,
            "-dlabel", label_pam,
            "-param", "step=0,type=label,dof=Tx_Ty_Tz:step=1,type=seg,algo=slicereg,poly=2",
            "-qc", QCDIR,
        ])
    finally:
        os.chdir(cwd)

    # Locate warp
    srcbase0 = Path(AMU_T2S).name.replace(".nii.gz","")
    dstbase  = Path(PAM50_T2).name.replace(".nii.gz","")
    warp0 = workdir / f"warp_{srcbase0}2{dstbase}.nii.gz"
    if not warp0.exists():
        candidates = list(workdir.glob(f"warp_*2{dstbase}.nii.gz"))
        if len(candidates) == 1:
            warp0 = candidates[0]
        elif len(candidates) > 1:
            warp0 = max(candidates, key=lambda p: p.stat().st_mtime)
        else:
            raise FileNotFoundError("Could not find step-0 warp")

    # Apply warp to AMU images (now in PAM50 space)
    amu_t2s_step0 = workdir / (AMU_T2S.stem + "_step0.nii.gz")
    amu_g_step0   = workdir / (AMU_GM.stem  + "_step0.nii.gz")
    run(["sct_apply_transfo", "-i", AMU_T2S, "-d", PAM50_T2, "-w", warp0, "-x", "linear", "-o", amu_t2s_step0])
    run(["sct_apply_transfo", "-i", AMU_GM,  "-d", PAM50_T2, "-w", warp0, "-x", "linear", "-o", amu_g_step0])

    # Extend top/bottom mask to cover the full PAM50 space ----
    if EXTEND_TO_CORD:
        print("==> Extending PAM50-space AMU images along Z to match PAM50 cord segmentation extent.")
        amu_t2s_ext = workdir / (AMU_T2S.stem + "_step0_ext.nii.gz")
        amu_g_ext   = workdir / (AMU_GM.stem  + "_step0_ext.nii.gz")
        copy_edge_slices_to_match(amu_t2s_step0, PAM50_SEG, amu_t2s_ext)
        copy_edge_slices_to_match(amu_g_step0,  PAM50_SEG, amu_g_ext)
    else:
        amu_t2s_ext = amu_t2s_step0
        amu_g_ext   = amu_g_step0

    # Finer registration
    os.chdir(workdir)
    try:
        run([
            "sct_register_multimodal",
            "-i", amu_t2s_ext,
            "-iseg", amu_g_ext,
            "-d", PAM50_T2,
            "-dseg", PAM50_SEG,
            "-param", "step=1,type=seg,algo=affine,iter=100,slicewise=1,metric=MeanSquares,smooth=1:step=2,type=im,algo=bsplinesyn,iter=5,slicewise=0,metric=MeanSquares,smooth=0",
            "-qc", QCDIR,
        ])
    finally:
        os.chdir(cwd)

    # Locate step-1 warp (from ext image in PAM50 space to PAM50)
    srcbase1 = amu_t2s_ext.name.replace(".nii.gz","")
    warp1 = workdir / f"warp_{srcbase1}2{dstbase}.nii.gz"
    if not warp1.exists():
        candidates = list(workdir.glob(f"warp_*{srcbase1}*2{dstbase}.nii.gz"))
        if len(candidates) == 1:
            warp1 = candidates[0]
        elif len(candidates) > 1:
            warp1 = max(candidates, key=lambda p: p.stat().st_mtime)
        else:
            # Fallback: any warp from step-1 to PAM50
            candidates = list(workdir.glob(f"warp_*2{dstbase}.nii.gz"))
            if not candidates:
                raise FileNotFoundError("Could not find step-1 warp")
            warp1 = max(candidates, key=lambda p: p.stat().st_mtime)

    # Apply warps sequentially to original AMU images: first warp0, then warp1
    amu_t2s_reg = OUTDIR / (AMU_T2S.stem + "_reg.nii.gz")
    amu_g_reg   = OUTDIR / (AMU_GM.stem  + "_reg.nii.gz")

    # Apply step-0 to get into PAM50, then step-1 refinement
    tmp_t2s = workdir / (AMU_T2S.stem + "_tmp_after_step0.nii.gz")
    tmp_g   = workdir / (AMU_GM.stem  + "_tmp_after_step0.nii.gz")

    run(["sct_apply_transfo", "-i", AMU_T2S, "-d", PAM50_T2, "-w", warp0, "-x", "linear", "-o", tmp_t2s])
    run(["sct_apply_transfo", "-i", AMU_GM,  "-d", PAM50_T2, "-w", warp0, "-x", "linear", "-o", tmp_g])

    run(["sct_apply_transfo", "-i", tmp_t2s, "-d", PAM50_T2, "-w", warp1, "-x", "linear", "-o", amu_t2s_reg])
    run(["sct_apply_transfo", "-i", tmp_g,   "-d", PAM50_T2, "-w", warp1, "-x", "linear", "-o", amu_g_reg])

    # Symmetrize and threshold
    amu_g_sym   = OUTDIR / (amu_g_reg.stem + "_sym.nii.gz")
    amu_t2s_sym = OUTDIR / (amu_t2s_reg.stem + "_sym.nii.gz")
    run(["python3", SYM_SCRIPT, "-i", amu_g_reg,   "--dtype", "float32", "--mode", "average", "-o", amu_g_sym])
    run(["python3", SYM_SCRIPT, "-i", amu_t2s_reg, "--dtype", "float32", "--mode", "average", "-o", amu_t2s_sym])

    amu_t2s_thr = OUTDIR / (amu_t2s_sym.stem + "_thr.nii.gz")
    run(["sct_maths", "-i", amu_t2s_sym, "-thr", "0", "-type", "uint16", "-o", amu_t2s_thr])

    print("\n=== Outputs ===")
    print(f"QC dir:               {QCDIR}")
    print(f"Step-0 warp:          {warp0}")
    print(f"Step-1 warp:          {warp1}")
    print(f"AMU GM reg:           {amu_g_reg}")
    print(f"AMU GM sym:           {amu_g_sym}")
    print(f"AMU T2* reg:          {amu_t2s_reg}")
    print(f"AMU T2* sym:          {amu_t2s_sym}")
    print(f"AMU T2* sym thr16:    {amu_t2s_thr}")
    print(f"Work dir (intermed.): {workdir}")

if __name__ == "__main__":
    main()
