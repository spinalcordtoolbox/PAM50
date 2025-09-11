#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# This script creates a symmetrical image by copying the information from the right side of the image
# to the left side.
#
# Usage:
#   python symmetrize_cord_segmentation.py -i input.nii.gz [-o output.nii.gz] [-t uint8]
#
# Author: Julien Cohen-Adad (adapted)

import argparse
import os
import numpy as np
import nibabel as nib


def str_to_dtype(dtype_str):
    try:
        return np.dtype(dtype_str)
    except TypeError:
        raise argparse.ArgumentTypeError(f"Unsupported dtype: {dtype_str}")


def make_default_output_name(input_fname: str) -> str:
    base, ext = os.path.splitext(input_fname)
    if ext == ".gz":  # handle .nii.gz
        base, ext2 = os.path.splitext(base)
        ext = ext2 + ext
    return base + "_sym" + ext


def symmetrize(data: np.ndarray, axis: int = 0, mode: str = "copy") -> np.ndarray:
    """
    Symmetrize `data` along `axis`.
    Modes:
      - "copy": mirror the right half to the left AND mirror back to the right → perfectly symmetric.
      - "average": average left & mirrored-right, then write that average to BOTH halves.
    Center slice (when odd size) is preserved as-is.
    """
    n = data.shape[axis]
    mid = n // 2
    out = data.copy()

    # convenient index builders
    def sl(start, stop):
        idx = [slice(None)] * data.ndim
        idx[axis] = slice(start, stop)
        return tuple(idx)

    def flip_along(arr):
        return np.flip(arr, axis=axis)

    if n % 2 == 0:
        left  = data[sl(0, mid)]         # length mid
        right = data[sl(mid, n)]         # length mid

        if mode == "copy":
            # define template as "right" and write both halves symmetrically
            templ = right
            out[sl(0, mid)]  = flip_along(templ)
            out[sl(mid, n)]  = templ
        elif mode == "average":
            avg = np.nanmean(np.stack([left, flip_along(right)], axis=0), axis=0)
            out[sl(0, mid)]  = avg
            out[sl(mid, n)]  = flip_along(avg)
        else:
            raise ValueError("mode must be 'copy' or 'average'")

    else:
        # odd: left [0:mid], center [mid], right [mid+1:n] (left/right length mid)
        left   = data[sl(0, mid)]
        center = data[sl(mid, mid+1)]
        right  = data[sl(mid+1, n)]

        if mode == "copy":
            templ = right
            out[sl(0, mid)]       = flip_along(templ)
            out[sl(mid, mid+1)]   = center  # keep center
            out[sl(mid+1, n)]     = templ
        elif mode == "average":
            avg = np.nanmean(np.stack([left, flip_along(right)], axis=0), axis=0)
            out[sl(0, mid)]       = avg
            out[sl(mid, mid+1)]   = center  # keep center
            out[sl(mid+1, n)]     = flip_along(avg)
        else:
            raise ValueError("mode must be 'copy' or 'average'")

    return out


def main():
    parser = argparse.ArgumentParser(description="Symmetrize a NIfTI image along axis 0.")
    parser.add_argument("-i", "--input", required=True, help="Path to input NIfTI file")
    parser.add_argument("-o", "--output", default=None,
                        help="Path to output NIfTI file (default: input_sym.nii.gz)")
    parser.add_argument("-t", "--dtype", type=str_to_dtype, default=np.uint8,
                        help="Output data type (e.g., uint8, int16, float32). Default: uint8")
    parser.add_argument("--mode", choices=["copy", "average"], default="copy",
                        help="Symmetrization mode. Default: copy")
    # Optional: expose axis if needed later; default stays 0
    parser.add_argument("--axis", type=int, default=0,
                        help="Axis to symmetrize along (0-based). Default: 0")
    args = parser.parse_args()

    # Load input
    nii = nib.load(args.input)
    data = nii.get_fdata()  # work in float; we'll cast later

    # Symmetrize
    data_sym = symmetrize(data, axis=args.axis, mode=args.mode)

    # If integer dtype requested, round to nearest before casting to avoid asymmetry from truncation
    if np.issubdtype(args.dtype, np.integer):
        data_sym = np.rint(data_sym)

    # Cast & preserve header (qform/sform, zooms, slope/intercept, etc.)
    data_sym = data_sym.astype(args.dtype)
    header = nii.header.copy()
    header.set_data_dtype(args.dtype)

    # Output filename
    output_fname = args.output if args.output else make_default_output_name(args.input)

    # Save
    nib.save(nib.Nifti1Image(data_sym, nii.affine, header), output_fname)
    print(f"✅ Done! Saved: {output_fname} | dtype={args.dtype} | mode={args.mode} | axis={args.axis}")


if __name__ == "__main__":
    main()
