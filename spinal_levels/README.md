### PAM50 Levels

These level files are a slightly modified copy of the [level files](https://github.com/PhillipsLab/pam50/tree/main/Spinal%20Cord%20Levels%20NIfTI) produced by the [Phillips Lab](https://github.com/PhillipsLab): 

Modifications include:

- Change data type from float64 to float32
- Copy header from current PAM50/spinal_levels 
- Rename files

To reproduce the modified files, please run `git checkout e854bbad9ab550fd93acabeaf43c97cf66b3a4e5`, then run the following script in your terminal:

```bash
#!/bin/bash
#
# Process Phillips Lab PAM50 spinal levels to match existing PAM50 conventions.
#
# Usage:
#   ./process_spinal_levels.sh
# 1. Clone https://github.com/spinalcordtoolbox/PAM50
# 2. Checkout commit e854bbad9ab550fd93acabeaf43c97cf66b3a4e5
# 3. Run inside /PAM50/spinal_levels_PhillipsLab/
# Authors: Sandrine Bédard, Joshua Newton

set -x
# Immediately exit if error
set -e -o pipefail

# Exit if user presses CTRL+C (Linux) or CMD+C (OSX)
trap "echo Caught Keyboard Interrupt within script. Exiting now.; exit" INT

start=`date +%s`

# Add missing info to the `info_label.txt` file to account for newly-added levels
file_info_label=$(realpath "../spinal_levels/info_label.txt")
extra_spinal_levels="20, Spinal level L1, spinal_level_21.nii.gz
21, Spinal level L2, spinal_level_22.nii.gz
22, Spinal level L3, spinal_level_23.nii.gz
23, Spinal level L4, spinal_level_24.nii.gz
24, Spinal level L5, spinal_level_25.nii.gz"
if [[ $(tail -c 23 "$file_info_label") == "spinal_level_20.nii.gz" ]]
then
    echo "$extra_spinal_levels" >> "$file_info_label"
fi

# Retrieve input params
PATH_IN=$PWD
PATH_OUT="$PATH_IN/spinal_levels_processed"
for FILE in *.nii.gz; do
    file=${FILE/%".nii.gz"}
    echo $file
    mkdir -p $PATH_OUT/${file}_processed
    rsync -avzh $FILE $PATH_OUT/${file}_processed
    cd $PATH_OUT/${file}_processed
    # Change file type 
    sct_image -i ${file}.nii.gz -type float32 -o ${file}_float32.nii.gz
    file="${file}_float32"
    # Copy header of SCT PAM50 template
    sct_image -i $SCT_DIR/data/PAM50/spinal_levels/spinal_level_02.nii.gz -copy-header $file.nii.gz -o ${file}_header.nii.gz
    file="${file}_header"
    # Rename the file to the filename corresponding to the level (specified by `info_label.txt`)
    level=$(echo "$file" | cut -d '_' -f 3) 
    file_out=$(grep -F "$level," $file_info_label | cut -d "," -f 3)
    cp $file.nii.gz $file_out
    cd "$PATH_IN"
    echo $PATH_IN
done

# Display useful info for the log
end=`date +%s`
runtime=$((end-start))
echo
echo "~~~"
echo "SCT version: `sct_version`"
echo "Ran on:      `uname -nsr`"
echo "Duration:    $(($runtime / 3600))hrs $((($runtime / 60) % 60))min $(($runtime % 60))sec"
echo "~~~"
```
