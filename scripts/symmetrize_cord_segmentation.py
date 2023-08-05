#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 
# This script creates a symmetrical image by copying the information from the right side of the image
# to the left side.
# 
# It is particularly useful when manually correcting a spinal cord segmentation, because only the right
# part needs to be corrected, and then this script is run to correct the left part. 
# 
# For more context, see: https://github.com/spinalcordtoolbox/PAM50/issues/19
# 
# How to run:
#   cd where this script is located and run:
#   python symmetrize_cord_segmentation.py
#   This will generate the file "PAM50_cord.nii.gz"
# 
# Author: Julien Cohen-Adad

import numpy as np
import nibabel as nib


# Open PAM50 spinal cord segmentation
nii_seg = nib.load("../template/PAM50_cord.nii.gz")
data_seg = nii_seg.get_fdata()

# Symmetrize image by copying the right to the left
data_seg[71:, ...] = np.flip(data_seg[:70, ...], axis=0)

# Save file
# TODO: use proper dtype
nii_seg_new = nib.Nifti1Image(np.uint8(data_seg), nii_seg.affine)
fname_out = "PAM50_cord_new.nii.gz"
nib.save(nii_seg_new, fname_out)

print(f"Done! 🎉 \nFile created: {fname_out}")
