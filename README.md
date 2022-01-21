# nipype-fsl-anat

Nipype interface(s) wrapping the `fsl_anat` command line tool

## Installation

```bash
pip install nipype-fsl-anat
```

## Usage

### `FSLAnat` (Interface)

```python
from nipype import Node, Workflow
from nipype_fsl_anat import FSLAnat

wf = Workflow(...)  # defined elsewhere

# ... snip ...

# input is file:
fsl_anat = Node(FSLAnat(), name='fsl_anat')
wf.connect(some_node, 't1_file', fsl_anat, 'in_file')

# input is directory (existing fsl_anat run):
fsl_anat = Node(FSLAnat(), name='fsl_anat')
wf.connect(inputnode, 'existing_fsl_anat_dir', fsl_anat, 'in_dir')

# ... snip ...

other_node = Node(..., name='...')
wf.connect(fsl_anat, 'out_dir', other_node, 'fsl_anat_results')
```

### `OptionalFSLAnat` (Interface)

This interface enables connecting either a nii image or an existing fsl_anat results directory to the `in_data` parameter. The intended use-case is so that a workflow will run `fsl_anat` if a T1 image is supplied as `in_data`, but will skip running `fsl_anat` if an existing results directory is supplied as `in_data`, for example, consider the following workflow:

```python
from nipype import IdentityInterface, Node, Workflow
from nipype_fsl_anat import OptionalFSLAnat

def create_workflow() -> Workflow:
    wf = Workflow(name='my_workflow')

    inputnode = Node(IdentityInterface(field=['anat_data']), name='inputnode')

    fsl_anat = Node(OptionalFSLAnat(), name='fsl_anat')
    wf.connect(inputnode, 'anat_data', fsl_anat, 'in_data')

    outputnode = Node(IdentityInterface(field=['anat_results']), name='outputnode')
    wf.connect(fsl_anat, 'out_dir', other_node, 'anat_results')

    return wf
```

While the workflow is trivially wrapping `OptionalFSLAnat`, it demonstrates the following. One can now pass either:

- A T1 nii image to `wf.inputs.inputnode.anat_data`, in which case the workflow will run `fsl_anat`, or
- An existing `fsl_anat` results directory to `wf.inputs.inputnode.anat_data` (the same input field!) in which case (unless `clobber == True`) the workflow will pass the inputs through the node without running `fsl_anat` and instead will forward the results that were passed to it.

## Details

This package exports two interfaces:

1. The `FSLAnat` interface. This interface's parameters mirror that of the underlying `fsl_anat` command line tool, and has been wired so that the `out_dir` (-o) parameter correctly points to the `fsl_anat`-generated output directory.

2. The `OptionalFSLAnat` interface. This interface is, in most aspects, exactly the same as `FSLAnat` with the following difference:

   `OptionalFSLAnat` has a single input source, `in_data` (cf. `FSLAnat` which has `in_file` (`-i`) and `in_dir` (`-d`)), where `in_data` can either be a file (`.nii.gz`) or a directory. Depending on the type of input data (file/directory) and the value of `clobber` (True/False/undefined) we have the following behaviours:

   - **`in_data = file` + `clobber = False | undefined`**

     Equivalent to `fsl_anat -i <in_data> ...`.

   - **`in_data = file` + `clobber = True`**

     Equivalent to `fsl_anat -i <in_data> --clobber ...`

   - **`in_data = directory` + `clobber = False | undefined`**

     `fsl_anat` execution is **SKIPPED**! Furthermore, if (in python) we have `fslanat = FSLAnat(...)`, then this interface will have `fslanat.outputs.out_dir == in_data`, i.e. `out_dir_basename` is ignored (if specified) and in this case **this node/interface becomes a no-op/pass-through node**.

   - **`in_data = directory` + `clobber = True`**

     Equivalent to `fsl_anat -d <in_data> --clobber ...`. Furthermore, if (in python) we have `fslanat = FSLAnat(...)`, then this interface will have `fslanat.outputs.out_dir == in_data`, i.e. `out_dir_basename` is ignored (if specified).

## Inputs

- **`FSLAnat`**

  | Interface intput/trait | CLI option             | Description                                                                        |
  | :--------------------- | ---------------------- | ---------------------------------------------------------------------------------- |
  | `in_file`              | `-i <strucural image>` | filename of input image (for one image only)                                       |
  | `in_dir`               | `-d <anat dir>`        | directory name for existing .anat directory where this script will be run in place |

- **`OptionalFSLAnat`**

  | Interface intput/trait | CLI option | Description                                                                                                                              |
  | :--------------------- | ---------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
  | `in_data`              | -          | filename of input image (for one image only) **_OR_** directory name for existing .anat directory where this script will be run in place |

- **Shared (both `FSLAnat` and `OptionalFSLAnat`)**

  | Interface input/trait | CLI option              | Description                                                                                                  |
  | :-------------------- | ----------------------- | ------------------------------------------------------------------------------------------------------------ |
  | `out_dir_basename`    | `-o <output directory>` | basename of directory for output (default is input image basename followed by .anat)                         |
  | `clobber`             | `--clobber`             | if .anat directory exist (as specified by -o or default from -i) then delete it and make a new one           |
  | `strongbias`          | `--strongbias`          | used for images with very strong bias fields                                                                 |
  | `weakbias`            | `--weakbias`            | used for images with smoother, more typical, bias fields (default setting)                                   |
  | `noreorient`          | `--noreorient`          | turn off step that does reorientation 2 standard (fslreorient2std)                                           |
  | `nocrop`              | `--nocrop`              | turn off step that does automated cropping (robustfov)                                                       |
  | `nobias`              | `--nobias`              | turn off steps that do bias field correction (via FAST)                                                      |
  | `noreg`               | `--noreg`               | turn off steps that do registration to standard (FLIRT and FNIRT)                                            |
  | `nononlinreg`         | `--nononlinreg`         | turn off step that does non-linear registration (FNIRT)                                                      |
  | `noseg`               | `--noseg`               | turn off step that does tissue-type segmentation (FAST)                                                      |
  | `nosubcortseg`        | `--nosubcortseg`        | turn off step that does sub-cortical segmentation (FIRST)                                                    |
  | `smoothing`           | `-s <value>`            | specify the value for bias field smoothing (the -l option in FAST)                                           |
  | `image_type`          | `-t <type>`             | specify the type of image (choose one of T1 T2 PD - default is T1)                                           |
  | `nosearch`            | `--nosearch`            | specify that linear registration uses the -nosearch option (FLIRT)                                           |
  | `betfparam`           | `--betfparam`           | specify f parameter for BET (only used if not running non-linear reg and also wanting brain extraction done) |
  | `nocleanup`           | `--nocleanup`           | do not remove intermediate files                                                                             |

## Outputs

- **Shared (both `FSLAnat` and `OptionalFSLAnat`)**

  | Interface output/trait          | Filename                                                      |
  | :------------------------------ | :------------------------------------------------------------ |
  | `out_dir`                       | _The `.anat` directory into which fsl_anat wrote the outputs_ |
  | `mni152_t1_2mm_brain_mask_dil1` | MNI152_T1_2mm_brain_mask_dil1.nii.gz                          |
  | `mni_to_t1_nonlin_field`        | MNI_to_T1_nonlin_field.nii.gz                                 |
  | `t1`                            | T1.nii.gz                                                     |
  | `t12std_skullcon_mat`           | T12std_skullcon.mat                                           |
  | `t1_biascorr`                   | T1_biascorr.nii.gz                                            |
  | `t1_biascorr_bet_skull`         | T1_biascorr_bet_skull.nii.gz                                  |
  | `t1_biascorr_brain`             | T1_biascorr_brain.nii.gz                                      |
  | `t1_biascorr_brain_mask`        | T1_biascorr_brain_mask.nii.gz                                 |
  | `t1_biascorr_to_std_sub_mat`    | T1_biascorr_to_std_sub.mat                                    |
  | `t1_fast_bias`                  | T1_fast_bias.nii.gz                                           |
  | `t1_fast_mixeltype`             | T1_fast_mixeltype.nii.gz                                      |
  | `t1_fast_pve_0`                 | T1_fast_pve_0.nii.gz                                          |
  | `t1_fast_pve_1`                 | T1_fast_pve_1.nii.gz                                          |
  | `t1_fast_pve_2`                 | T1_fast_pve_2.nii.gz                                          |
  | `t1_fast_pveseg`                | T1_fast_pveseg.nii.gz                                         |
  | `t1_fast_restore`               | T1_fast_restore.nii.gz                                        |
  | `t1_fast_seg`                   | T1_fast_seg.nii.gz                                            |
  | `t1_fullfov`                    | T1_fullfov.nii.gz                                             |
  | `t1_nonroi2roi_mat`             | T1_nonroi2roi.mat                                             |
  | `t1_orig`                       | T1_orig.nii.gz                                                |
  | `t1_orig2roi_mat`               | T1_orig2roi.mat                                               |
  | `t1_orig2std_mat`               | T1_orig2std.mat                                               |
  | `t1_roi_log`                    | T1_roi.log                                                    |
  | `t1_roi2nonroi_mat`             | T1_roi2nonroi.mat                                             |
  | `t1_roi2orig_mat`               | T1_roi2orig.mat                                               |
  | `t1_std2orig_mat`               | T1_std2orig.mat                                               |
  | `t1_subcort_seg`                | T1_subcort_seg.nii.gz                                         |
  | `t1_to_mni_lin_mat`             | T1_to_MNI_lin.mat                                             |
  | `t1_to_mni_lin`                 | T1_to_MNI_lin.nii.gz                                          |
  | `t1_to_mni_nonlin`              | T1_to_MNI_nonlin.nii.gz                                       |
  | `t1_to_mni_nonlin_txt`          | T1_to_MNI_nonlin.txt                                          |
  | `t1_to_mni_nonlin_coeff`        | T1_to_MNI_nonlin_coeff.nii.gz                                 |
  | `t1_to_mni_nonlin_field`        | T1_to_MNI_nonlin_field.nii.gz                                 |
  | `t1_to_mni_nonlin_jac`          | T1_to_MNI_nonlin_jac.nii.gz                                   |
  | `t1_vols_txt`                   | T1_vols.txt                                                   |
  | `lesionmask`                    | lesionmask.nii.gz                                             |
  | `lesionmaskinv`                 | lesionmaskinv.nii.gz                                          |
  | `log_txt`                       | log.txt                                                       |

## Contributing

1. Have or install a recent version of `poetry` (version >= 1.1)
1. Fork the repo
1. Setup a virtual environment (however you prefer)
1. Run `poetry install`
1. Run `pre-commit install`
1. Add your changes
1. Commit your changes + push to your fork
1. Open a PR
