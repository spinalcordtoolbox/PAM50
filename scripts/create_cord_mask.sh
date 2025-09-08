#!/bin/bash
# Script to create spinal cord mask using sct_deepseg
# Usage: ./create_cord_mask.sh

# Save the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

cd $SCT_DIR/data/PAM50/template

# Create spinal cord segmentation using contrast-agnostic model (model_contrast_agnostic_20250123)
sct_deepseg spinalcord -i PAM50_t2.nii.gz -o PAM50_cord.nii.gz

# Symmetrize the segmentation
python3 ~/code/PAM50/scripts/symmetrize_cord_segmentation.py -i PAM50_cord.nii.gz --dtype uint8 --mode majority
mv PAM50_cord_sym.nii.gz PAM50_cord.nii.gz
