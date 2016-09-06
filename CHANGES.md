#PAM50 Template

##2016-09-02 (JCA)
- Created new WM atlas using commit: 8a91d5fbdba6cf222de3880d9777cef46d736256

##2016-08-30 (JCA)
- added "8, spine, PAM50_spine.nii.gz" in template/info_label.txt

##2016-08-26 (JCA)
- modified "PAM50_label_disc.nii.gz"
- updated PAM50_levels accordingly
~~~
sct_process_segmentation -i PAM50_cord.nii.gz -p label-vert -discfile PAM50_label_disc.nii.gz
~~~

##2016-08-25 (JCA)
- extended cord segmentation towards caudal end using ITKsnap: only one half, then used a function to copy the other half (see below)
- extended cord segmentation towards rostral end using:
~~~
python $SCT_DIR/dev/atlas/create_atlas/register_AMU_to_PAM.py
~~~

##2016-07-15 (JCA)
- Modified cord segmentation because slightly too large.
- Symmetrized cord segmentation
- Updated CSF + levels
- Improved AMU->PAM50 registration
- Regenerated PAM50_atlas based on new registration
- Regenerated PAM50_cord, PAM50_wm and PAM50_gm as a sum of all tracts
~~~
sct_propseg -i PAM50_t1.nii.gz -c t1
# manual edits
# symmetrized cord then binarized
sct_maths -i PAM50_cord2.nii.gz -symmetrize 0 -o PAM50_cord2_sym.nii.gz
sct_maths -i PAM50_cord2_sym.nii.gz -bin -o PAM50_cord2_sym_bin.nii.gz 
# add old cord to csf
sct_maths -i PAM50_cord.nii.gz -add PAM50_csf.nii.gz -o PAM50_cordcsf.nii.gz
# then substract with new cord segmentation
sct_maths -i PAM50_cordcsf.nii.gz -sub PAM50_cord2_sym_bin.nii.gz -o PAM50_csf2.nii.gz
# update levels
sct_maths -i PAM50_cord2_sym_bin.nii.gz -mul PAM50_levels.nii.gz -o PAM50_levels2.nii.gz
# register AMU->PAM50
sct_maths -i PAM50_cord.nii.gz -laplacian 1 -o PAM50_cord_lapl.nii.gz
sct_maths -i PAM50_wm.nii.gz -add PAM50_gm.nii.gz -o PAM50_wmgm.nii.gz
sct_maths -i PAM50_wmgm.nii.gz -thr 0.5 -o PAM50_wmgm_thr.nii.gz
sct_maths -i PAM50_wmgm_thr.nii.gz -bin -o PAM50_wmgm_thr_bin.nii.gz 
sct_maths -i PAM50_wmgm_thr_bin.nii.gz -laplacian 1 -o PAM50_wmgm_thr_bin_lapl.nii.gz 
sct_register_multimodal -i PAM50_wmgm_thr_bin_lapl.nii.gz -d PAM50_cord_lapl.nii.gz -iseg PAM50_wmgm_thr_bin.nii.gz -dseg PAM50_cord.nii.gz -param step=1,type=seg,algo=slicereg,smooth=3:step=2,type=im,algo=bsplinesyn,iter=5,slicewise=0 -x linear
sct_apply_transfo -i PAM50_wm.nii.gz -d PAM50_cord.nii.gz -w warp_PAM50_wmgm_thr_bin_lapl2PAM50_cord_lapl.nii.gz -x linear
~~~

##2016-07-11 (JCA)
- fixed issue in info_label.txt

##2016-07-11 (JCA)
- added WM atlas + GM parcellation.

##2016-07-10 (JCA)
- added info_label.txt

##2016-07-10 (JCA)
- WM/GM->float32, T2s->uint16, WM/GM/T2s->RPI

##2016-07-10 (BDL)
- Added WM, GM and T2s

##2016-07-05 (CG)
- Added PAM50_spine.nii.gz

##2016-07-01 (JCA):
- Reduced size of C1 vertebrae.

##2016-07-01 (JCA)
- Fixed wrong z-values in PAM50_label_disc.

##2016-07-01 (JCA)
- Changed PAM50_label* to type=uint8 because values were non-integer.

##2016-06-29 (JCA)
- Changed orientation for RPI
- fixed inconsistent sizes
- thresholded at zero
- set type=uint16 for t1,t2 and t2s
- added continuous vertebral levels.
~~~
old_file=PAM50_WM
new_file="/Users/julien/Dropbox/Public/sct/PAM50/template/PAM50_wm"
sct_maths -i ${old_file}.nii.gz -thr 0 -o tmp.file.nii.gz
sct_image -i tmp.file.nii.gz -type float32 -o tmp.file.nii.gz
sct_image -i tmp.file.nii.gz -setorient RPI -o tmp.file.nii.gz
mv tmp.file.nii.gz ${new_file}.nii.gz
~~~

##2016-06-21 (BDL)
- Modified T1-T2 coregistration
- updated T2*

##2016-03-26 (JCA)
- Fixed https://github.com/neuropoly/spinalcordtoolbox/issues/783

##2015-11-04 (BDL)
- Creation

##TODO:
- also adjust size of PAM50_levels_continuous.nii.gz
- 2016-07-15: PAM50_levels is missing some voxels compared to PAM50_cord (due to adjustmen)
