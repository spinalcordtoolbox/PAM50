# TODO: Download AMU-Poly-MNI zip files provided by Virginie Callot
cd $SCT_DIR/data/PAM50/template
# Create label on MNI-Poly-AMU to identify the z (top part of the visible template). The XY coordinate does not matter too much since pipeline will be followed by centermass registration.
# TODO: remove hardcoding of paths
sct_label_utils -i ~/Desktop/MNI-POLY-AMU/AMU15_T2star_sym.nii.gz -create 75,75,965,1 -o ~/Desktop/MNI-POLY-AMU/label_AMU15.nii.gz
# Create associated label in the PAM50
sct_label_utils -i PAM50_t2.nii.gz -create 70,70,959,1 -o label_PAM50.nii.gz
# Register AMU15 --> PAM50
sct_register_multimodal -i ~/Desktop/MNI-POLY-AMU/AMU15_T2star_sym.nii.gz -iseg ~/Desktop/MNI-POLY-AMU/AMU15_GW_sym.nii.gz -ilabel ~/Desktop/MNI-POLY-AMU/label_AMU15.nii.gz -d PAM50_t2.nii.gz -dseg PAM50_t2_seg.nii.gz -dlabel label_PAM50.nii.gz -param step=0,type=label,dof=Tx_Ty_Tz:step=1,type=seg,algo=slicereg,poly=2 -qc qc
# Apply the warping to the AMU15 template and its segmentation
sct_apply_transfo -i ~/Desktop/MNI-POLY-AMU/AMU15_T2star_sym.nii.gz -d PAM50_t2.nii.gz -w warp_AMU15_T2star_sym2PAM50_t2.nii.gz -x linear
sct_apply_transfo -i ~/Desktop/MNI-POLY-AMU/AMU15_G_sym.nii.gz -d PAM50_t2.nii.gz -w warp_AMU15_T2star_sym2PAM50_t2.nii.gz -x linear
# Symmetrize the warped objects
# TODO: remove hardcoding of paths
python3 ~/code/PAM50/scripts/symmetrize_cord_segmentation.py -i AMU15_G_sym_reg.nii.gz --dtype float32 --mode average
python3 ~/code/PAM50/scripts/symmetrize_cord_segmentation.py -i AMU15_T2star_sym_reg.nii.gz --dtype float32 --mode average
# Remove negatives values on the T2*-weighted image by thresholding, and output as UINT16 type (like for PAM50_t2)
sct_maths -i AMU15_T2star_sym_reg_sym.nii.gz -thr 0 -type uint16 -o AMU15_T2star_sym_reg_sym_thr.nii.gz
