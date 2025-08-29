# TODO: Download AMU-Poly-MNI zip files provided by Virginie Callot
cd $SCT_DIR/data/PAM50/template
# Create label on MNI-Poly-AMU to identify the z (top part of the visible template). The XY coordinate does not matter too much since pipeline will be followed by centermass registration.
sct_label_utils -i ~/Desktop/MNI-POLY-AMU/AMU15_T2star_sym.nii.gz -create 75,75,965,1 -o ~/Desktop/MNI-POLY-AMU/label_AMU15.nii.gz
# Create associated label in the PAM50
sct_label_utils -i PAM50_t2.nii.gz -create 70,70,959,1 -o label_PAM50.nii.gz
# Register AMU15 --> PAM50
sct_register_multimodal -i ~/Desktop/MNI-POLY-AMU/AMU15_T2star_sym.nii.gz -iseg ~/Desktop/MNI-POLY-AMU/AMU15_GW_sym.nii.gz -ilabel ~/Desktop/MNI-POLY-AMU/label_AMU15.nii.gz -d PAM50_t2.nii.gz -dseg PAM50_t2_seg.nii.gz -dlabel label_PAM50.nii.gz -param step=0,type=label,dof=Tx_Ty_Tz:step=1,type=seg,algo=slicereg,poly=2 -qc qc

