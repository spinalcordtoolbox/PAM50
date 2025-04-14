"""
Keep the largest connected component for each atlas mask.

You can use the SCT venv:
    source ${SCT_DIR}/python/etc/profile.d/conda.sh                                                                                                                                                                                                                                                            (master|…1)
    conda activate venv_sct

Then, you can run the script:
    cd <THIS_REPO>
    python scripts/keep_largest_component.py -path atlas

The modified files are saved to the `atlas_tmp` folder. To compare the original and modified images you can run:
    for f in atlas_tmp/*[0-9][0-9].nii.gz;do fsleyes ${f/_tmp/} -cm green ${f} -cm blue-lightblue ${f/.nii/_diff.nii} -cm red-yellow;done

Finally, you can copy the modified images to the original directory:
    cp atlas_tmp/PAM50_atlas_[0-9][0-9].nii.gz atlas/
    rm -r atlas_tmp

Resolves: https://github.com/spinalcordtoolbox/PAM50/issues/33
"""

import argparse
import shutil
import nibabel as nib
import numpy as np
from scipy import  ndimage
from pathlib import Path


def keep_largest_component(data: np.ndarray) -> np.ndarray:
    """
    Keep only the largest connected 3D component.

    :arg data: 3D numpy array
    :return: 3D numpy array with only the largest connected component
    """
    labels, num = ndimage.label(data > 0)       # connected component labeling
    sizes = ndimage.sum(np.ones_like(data), labels, index=np.arange(1, num+1))      # compute size of each component
    largest_label = (np.argmax(sizes) + 1)      # find the largest component
    return np.where(labels == largest_label, data, 0)   #  to avoid tiny rounding errors during multiplication with a bool mask


def save_nifti(data: np.ndarray, affine: np.ndarray, dtype: np.dtype, out_path: Path) -> None:
    """
    Save the nii file with same datatype as the orig image.

    :arg data: 3D numpy array
    :arg reference_img: Reference nii image
    :arg out_path: Path to save the output nii image
    """
    data = data.astype(dtype, copy=True)
    img = nib.Nifti1Image(data, affine)
    img.set_data_dtype(dtype)
    nib.save(img, out_path)

def main(path: str) -> None:
    """
    Process all .nii.gz files in the specified directory.

    :args path: Directory containing .nii.gz files to process.
    """
    input_dir = Path(path)
    output_dir = input_dir.parent / f"{input_dir.name}_tmp"
    output_dir.mkdir(parents=True, exist_ok=True)

    for fpath in sorted(list(input_dir.glob("*.nii.gz"))):
        img = nib.load(fpath)
        dtype = img.header.get_data_dtype()
        data = np.array(img.dataobj, dtype=dtype)
        masked = keep_largest_component(data)

        # If there is difference between the original and modified image, save the diff image and replace the original
        # image with the modified one
        if not np.allclose(data, masked):
            print(f"Modified: {fpath.name}")
            # Save the modified image into the temp directory; keeping only the largest component
            out_path = output_dir / fpath.name
            save_nifti(masked, img.affine, dtype, out_path)
            diff = data - masked
            diff_path = output_dir / fpath.name.replace(".nii.gz", "_diff.nii.gz")
            save_nifti(diff, img.affine, dtype, diff_path)
            #shutil.copy2(out_path, fpath)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-path", required=False, default="atlas", help="Directory with .nii.gz files")
    args = parser.parse_args()
    main(args.path)