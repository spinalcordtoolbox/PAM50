#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 
# This script labels the spinal cord segmentation using the disc labels. 
# 
# For more context, see: https://github.com/spinalcordtoolbox/PAM50/pull/21
# 
# How to run:
#   cd where this script is located and run:
#   python label_segmentation.py
# 
# Author: Julien Cohen-Adad

import numpy as np
import nibabel as nib


# Open PAM50 spinal cord segmentation
nii_seg = nib.load("../template/PAM50_cord.nii.gz")

# Open disc labels
nii_discs = nib.load("../template/PAM50_label_disc.nii.gz")
data_discs = nii_discs.get_fdata()

# Iterate across z-slices and assign proper vertebral level value
data_seg_labeled = nii_seg.get_fdata()
nx, ny, nz = data_seg_labeled.shape
disc_value = 0
# Note: iteration is from superior (highest slice) to inferior (slice=0)
for iz in range(nz-1, 0, -1):
    data_seg_labeled[..., iz] *= disc_value
    # Check if there is a disc at this slice
    if np.any(data_discs[..., iz]):
        # If so, update disc_value
        disc_value += 1

# Use proper dtype
data_seg_labeled = np.uint8(data_seg_labeled)
# Note: here we assume that PAM50_cord is also UINT8, hence there is no need to modify the header

# Save file
nii_seg_new = nib.Nifti1Image(data_seg_labeled, nii_seg.affine)
fname_out = "PAM50_levels_new.nii.gz"
nib.save(nii_seg_new, fname_out)

print(f"Done! 🎉 \nFile created: {fname_out}")
