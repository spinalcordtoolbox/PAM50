#PAM50 Template

##2019-10-29 (CG)
- Added template/PAM50_label_spinal_levels.nii.gz
- Clarify label names in template/info_label.txt

##2018-12-11 (BDL)
- Aligned the template with the ICBM152 (more info here: https://github.com/neuropoly/spinalcordtoolbox/issues/2085)
- Cropped the template just above C1 vertebral label
- Updated the file info_label.txt in the folder template/ to take new files into account
- Shifted the labels in the file PAM50_label_discPosterior.nii.gz by one

##2018-08-13 (JCA)
- Swapped ventral-dorsal labels on PAM50/atlas (fixed issue #1995)

##2018-04-10 (BDL)
- Added labels 49 (pontomedullary groove) and 50 (pontomedullary junction) to template/PAM50_label_disc.nii.gz

##2017-01-07 (JCA)
- Fixed typo in atlas info_label.txt (issue #1100)

##2017-01-01 (JCA)
- Atlas now sums to one inside the cord (fixed issue #411)

##2016-11-28 (JCA)
- added spinal levels using $SCT_DIR/dev/spinal_level/sct_extract_spinal_levels.py
- Removed __MACOSX in archive and zip using
~~~
zip -r 20161121_PAM50.zip PAM50/
~~~

##2016-11-21 (JCA)
- Added #Keyword= entries for cleaner code

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
