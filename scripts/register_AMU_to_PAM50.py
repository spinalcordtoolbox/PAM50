
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reproducible registration script (no CLI args).
Pipeline:
  1) Step-0 (label-based, Tx_Ty_Tz) AMU -> PAM50 to get initial rigid/translation alignment.
  2) Apply step-0 warp to AMU images to bring them into PAM50 space.
  3) Extend AMU volumes in PAM50 space by copying top/bottom slices to match PAM50 cord extent.
  4) Global slicewise registration (SCT) on extended volumes:
       sct_register_multimodal step=1, type=seg, algo=slicereg, poly=2 (standard coarse alignment)
  5) Apply global warp (warp1 ∘ warp0) to produce baseline registered AMU_T2* and AMU_GM.
  6) Detect extended Z-slices and run **per-slice isct_antsRegistration** ONLY on those slices
     "de proche en proche", initializing each slice with previous transform.
     Overwrite the corresponding slices in the baseline outputs.
  7) Symmetrize and threshold (T2*).

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
# Per-slice ants params
ANTS_RIGID = [
    "-d", "2",
    "-t", "Rigid[0.1]",
    "-m", "MeanSquares[{fixed},{moving},1,4]",
    "-c", "50x20",
    "-s", "1x0",
    "-f", "2x1",
]

HERE = Path(__file__).resolve().parent
SYM_SCRIPT = HERE / "symmetrize_cord_segmentation.py"

def run(cmd, check=True):
    print("+", " ".join(map(str, cmd)), flush=True)
    res = subprocess.run(list(map(str, cmd)), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    print(res.stdout)
    if check and res.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(map(str, cmd))}")
    return res

def nz_mask_per_slice(vol_path: Path):
    img = nib.load(str(vol_path))
    data = img.get_fdata()
    if data.ndim != 3:
        raise ValueError("Expected a 3D volume")
    Z = data.shape[2]
    mask = np.zeros(Z, dtype=bool)
    for z in range(Z):
        mask[z] = np.any(data[:, :, z] != 0)
    return mask

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
        amu_t2s_reg = workdir / (AMU_T2S.stem + "_step0_ext.nii.gz")
        amu_g_reg   = workdir / (AMU_GM.stem  + "_step0_ext.nii.gz")
        copy_edge_slices_to_match(amu_t2s_step0, PAM50_SEG, amu_t2s_reg)
        copy_edge_slices_to_match(amu_g_step0,  PAM50_SEG, amu_g_reg)
    else:
        amu_t2s_reg = amu_t2s_step0
        amu_g_reg   = amu_g_step0

    # ---------- Per-slice refinement ONLY on truly extended slices ----------
    def nz_mask_per_slice_data(arr):
        Z = arr.shape[2]
        mask = np.zeros(Z, dtype=bool)
        for z in range(Z):
            mask[z] = np.any(arr[:, :, z] != 0)
        return mask

    # Extended detection via step0 vs step0_ext (GM)
    mask_step0 = nz_mask_per_slice(amu_g_step0)
    mask_ext   = nz_mask_per_slice(amu_g_reg)
    Z = mask_ext.shape[0]
    extended = np.logical_and(~mask_step0, mask_ext)
    nz_indices = np.where(mask_step0)[0]
    if nz_indices.size == 0:
        z_core_min, z_core_max = 0, -1
    else:
        z_core_min, z_core_max = int(nz_indices.min()), int(nz_indices.max())
    bottom_ext = np.where(extended[:z_core_min])[0] if z_core_min >= 1 else np.array([], dtype=int)
    top_ext    = (z_core_max + 1) + np.where(extended[z_core_max + 1:])[0] if z_core_max < Z - 1 else np.array([], dtype=int)

    print(f"Core NZ span: [{z_core_min}, {z_core_max}]")
    print(f"Bottom extended slices: {bottom_ext.tolist()}")
    print(f"Top extended slices: {top_ext.tolist()}")

    # Load baseline registered 3D outputs and the extended volumes for picking slices
    ref_fix_seg = nib.load(str(PAM50_SEG))
    fix_seg_3d = ref_fix_seg.get_fdata()
    gm_ext_3d  = nib.load(str(amu_g_reg)).get_fdata()
    t2s_ext_3d = nib.load(str(amu_t2s_reg)).get_fdata()

    # Helper to run ants on a single slice and overwrite in the baseline outputs
    def ants_slice_refine(z, prev_mat=None):
        # Build 2D (single-slice) fixed/moving files
        fix = workdir / f"fix_seg_z{z:04d}.nii.gz"
        mov_g = workdir / f"mov_g_ext_z{z:04d}.nii.gz"
        mov_t = workdir / f"mov_t2s_ext_z{z:04d}.nii.gz"

        fix_slice = nib.load(str(PAM50_SEG)).get_fdata()[:, :, z]
        gm_ext_3d = nib.load(str(amu_g_step0_ext)).get_fdata()
        t2_ext_3d = nib.load(str(amu_t2s_step0_ext)).get_fdata()
        # write as single-slice 3D (X,Y,1) so ANTs spacing/origin stay consistent
        nib.Nifti1Image(fix_slice[:, :, None], nib.load(str(PAM50_SEG)).affine, nib.load(str(PAM50_SEG)).header).to_filename(str(fix))
        nib.Nifti1Image(gm_ext_3d[:, :, z][:, :, None], nib.load(str(amu_g_step0_ext)).affine, nib.load(str(amu_g_step0_ext)).header).to_filename(str(mov_g))
        nib.Nifti1Image(t2_ext_3d[:, :, z][:, :, None], nib.load(str(amu_t2s_step0_ext)).affine, nib.load(str(amu_t2s_step0_ext)).header).to_filename(str(mov_t))

        # Run 2D rigid ANTs (use previous slice’s affine as init if provided)
        out_prefix = workdir / f"ants_z{z:04d}_"
        cmd = ["isct_antsRegistration",
            "-d", "2",
            "-t", "Rigid[0.1]",
            "-m", f"MeanSquares[{fix},{mov_g},1,4]",
            "-c", "50x20",
            "-s", "1x0",
            "-f", "2x1"]
        if prev_mat is not None:
            cmd += ["-r", str(prev_mat)]
        cmd += ["-o", str(out_prefix)]
        run(cmd)

        mat = Path(str(out_prefix) + "0GenericAffine.mat")
        if not mat.exists():
            raise FileNotFoundError(f"ants transform not found for slice z={z}: {mat}")

        # Apply to GM (NN) and T2* (linear) -- ANTs will write 2-D images
        out_g = workdir / f"amu_g_refined_z{z:04d}.nii.gz"
        out_t = workdir / f"amu_t2s_refined_z{z:04d}.nii.gz"
        run(["isct_antsApplyTransforms", "-d", "2",
            "-i", mov_g, "-r", fix, "-t", mat, "-o", out_g, "-n", "NearestNeighbor"])
        run(["isct_antsApplyTransforms", "-d", "2",
            "-i", mov_t, "-r", fix, "-t", mat, "-o", out_t, "-n", "Linear"])

        # Load refined 2-D outputs robustly (2-D or (X,Y,1))
        def load2d(path):
            arr = nib.load(str(path)).get_fdata()
            return arr[:, :, 0] if arr.ndim == 3 else arr

        g_w = load2d(out_g)  # (X,Y)
        t_w = load2d(out_t)  # (X,Y)

        # Overwrite slice z in the *baseline* registered 3-D outputs
        ref_g_img = nib.load(str(amu_g_reg))
        ref_t_img = nib.load(str(amu_t2s_reg))
        g3d = ref_g_img.get_fdata()
        t3d = ref_t_img.get_fdata()
        g3d[:, :, z] = g_w
        t3d[:, :, z] = t_w
        nib.Nifti1Image(g3d, ref_g_img.affine, ref_g_img.header).to_filename(str(amu_g_reg))
        nib.Nifti1Image(t3d, ref_t_img.affine, ref_t_img.header).to_filename(str(amu_t2s_reg))

        return mat

    # Bottom chain (seed at z_core_min), then go downward on bottom_ext
    prev_mat = None
    if bottom_ext.size > 0 and z_core_min <= z_core_max:
        prev_mat = ants_slice_refine(z_core_min, prev_mat=None)
        for z in range(z_core_min - 1, -1, -1):
            if z in bottom_ext:
                prev_mat = ants_slice_refine(z, prev_mat=prev_mat)

    # Top chain (seed at z_core_max), then go upward on top_ext
    prev_mat = None
    if top_ext.size > 0 and z_core_min <= z_core_max:
        prev_mat = ants_slice_refine(z_core_max, prev_mat=None)
        for z in range(z_core_max + 1, Z):
            if z in top_ext:
                prev_mat = ants_slice_refine(z, prev_mat=prev_mat)

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
