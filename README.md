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

## Contributing

1. Have or install a recent version of `poetry` (version >= 1.1)
1. Fork the repo
1. Setup a virtual environment (however you prefer)
1. Run `poetry install`
1. Run `pre-commit install`
1. Add your changes
1. Commit your changes + push to your fork
1. Open a PR
