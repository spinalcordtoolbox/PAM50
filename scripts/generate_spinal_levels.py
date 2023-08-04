#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 
# This script generates the spinal segments for the PAM50 template. It is based on the article by Frostell et al.
# https://www.frontiersin.org/articles/10.3389/fneur.2016.00238/full
# For more context, see: https://github.com/spinalcordtoolbox/PAM50/issues/16
# 
# How to run:
#   cd where this script is located and run:
#   python generate_spinal_levels.py
#   This will generate the file "PAM50_spinal_levels.nii.gz"
# 
# Author: Julien Cohen-Adad

import numpy as np
import nibabel as nib


# Identification of the slice on the PAM50 template that corresponds to the upper portion of the C1 nerve rootlets
z_top = 984
# Identification of the slice on the PAM50 template that corresponds to the caudal end of the spinal cord
z_bottom = 40

# Compute the length of the spinal cord (in mm), knowing that the pixel size along Z is 0.5mm.
length_spinalcord = 984 - 40
length_spinalcord_mm = 0.5 * (984 - 40)

# Build dictionary of spinal segment location based on Table 3 of Frostell et al. article
# TODO: continue with all levels
percent_length_segment = [
    {"C1": 1.6},
    {"C2": 2.2},
    {"C3": 3.5},
    {"C4": 3.5},
    {"C5": 3.5},
    {"C6": 3.3},
    {"C7": 3.2},
    {"C8": 3.4},
    {"T1": 3.6},
    {"T2": 3.9},
    {"T3": 4.4},
    {"T4": 5},
    {"T5": 5.1},
    {"T6": 5.6},
    {"T7": 5.6},
    {"T8": 5.4},
    {"T9": 5.1},
    {"T10": 4.7},
    {"T11": 4.3},
    {"T12": 3.9},
    {"L1": 3.6},
    {"L2": 2.8},
    {"L3": 2.4},
    {"L4": 2.2},
    {"L5": 1.7},
    {"S1": 1.5},
    {"S2": 1.6},
    {"S3": 1.4},
    {"S4": 1.3},
    {"S5": 0.9},
]

print(f"Number of segments: {len(percent_length_segment)}")

# Create a DataFrame from the table data
# df = pd.DataFrame(table_data, columns=["label", "value"])

# Set the 'label' column as the index for quick access
# df.set_index("label", inplace=True)

# Now you can access the value corresponding to a label using loc:
# encoded_data = df.loc["label1", "value"]

# Verify that the sum of all relative length segment is 100
total_sum = 0.0
for item in percent_length_segment:
    value = list(item.values())[0]
    total_sum += value
print(f"Sum across percent segments: {total_sum}")

# Open PAM50 spinal cord segmentation
nii_spinalcord = nib.load("../template/PAM50_cord.nii.gz")

# Create spinal segments
data_spinalsegments = np.uint8(nii_spinalcord.get_fdata())

# TODO: zero values above z_top

z_segment_top = z_top
i_level = 1
for level_info in percent_length_segment:
    level_name, level_percent = list(level_info.items())[0]
    # Compute lenght of the spinal segment
    length_segment = np.uint8(length_spinalcord * level_percent / 100)
    # Get the top and bottom coordinates of that segment
    z_segment_bottom = z_segment_top - length_segment
    # Modify spinal cord mask with spinal segment value
    data_spinalsegments[:, :, z_segment_bottom:z_segment_top] *= i_level
    # Update location of the top of the next segment
    z_segment_top = z_segment_bottom
    # Update level
    i_level += 1

# Save file
nii_spinalsegments = nib.Nifti1Image(data_spinalsegments, nii_spinalcord.affine)
fname_out = "PAM50_spinal_levels.nii.gz"
nib.save(nii_spinalsegments, fname_out)

print(f"Done! 🎉 \nFile created: {fname_out}")
