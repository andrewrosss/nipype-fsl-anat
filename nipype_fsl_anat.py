"""An interface for the fsl_anat command line tool

This package exists due to the nature of how fsl_anat handles it's
options/outputs.

Specifically, given a target directory (`fsl_anat -o <dir> ...`), say
`fsl_anat -o foo ...`, fsl_anat will instead write the results to `foo.anat/`,
this is strange, but perhaps there's a runtime check for whether or not the
target directory is of the form `*.anat/`? However, specifying
`fsl_anat -o foo.anat ...` ends up producing results in the folder
`foo.anat.anat/`.

So basically, no matter where you tell `fsl_anat` to write to, it will
write somewhere else.

Since nipype workflows uses traits to define the various interface parameters,
and because each workflow node (at its given execution time) requires its input
files/directories to exist, this minor shift in target directory makes lining
up other, downstream, workflow nodes with the results of fsl_anat diffcult.

This package tries to simplify this complication by exporting an
`FSLAnat` interface whose parameters mirror that of the
underlying `fsl_anat` command line tool, and whose `out_dir` (-o) parameter
correctly points at the fsl_anat-generated output directory.
"""
from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any

from nipype.interfaces import base
from nipype.interfaces import fsl
from nipype.interfaces.base import isdefined
from nipype.interfaces.base.core import RuntimeContext


__version__ = "1.0.0"

NII_FILE_REGEXP = re.compile(r".*\.nii(\.gz)?$")
FSL_ANAT_DIR_REGEXP = re.compile(r".*\.anat$")
FSL_ANAT_OUTPUT_FILENAMES = {
    "mni152_t1_2mm_brain_mask_dil1": "MNI152_T1_2mm_brain_mask_dil1.nii.gz",
    "mni_to_t1_nonlin_field": "MNI_to_T1_nonlin_field.nii.gz",
    "t1": "T1.nii.gz",
    "t12std_skullcon_mat": "T12std_skullcon.mat",
    "t1_biascorr": "T1_biascorr.nii.gz",
    "t1_biascorr_bet_skull": "T1_biascorr_bet_skull.nii.gz",
    "t1_biascorr_brain": "T1_biascorr_brain.nii.gz",
    "t1_biascorr_brain_mask": "T1_biascorr_brain_mask.nii.gz",
    "t1_biascorr_to_std_sub_mat": "T1_biascorr_to_std_sub.mat",
    "t1_fast_bias": "T1_fast_bias.nii.gz",
    "t1_fast_mixeltype": "T1_fast_mixeltype.nii.gz",
    "t1_fast_pve_0": "T1_fast_pve_0.nii.gz",
    "t1_fast_pve_1": "T1_fast_pve_1.nii.gz",
    "t1_fast_pve_2": "T1_fast_pve_2.nii.gz",
    "t1_fast_pveseg": "T1_fast_pveseg.nii.gz",
    "t1_fast_restore": "T1_fast_restore.nii.gz",
    "t1_fast_seg": "T1_fast_seg.nii.gz",
    "t1_fullfov": "T1_fullfov.nii.gz",
    "t1_nonroi2roi_mat": "T1_nonroi2roi.mat",
    "t1_orig": "T1_orig.nii.gz",
    "t1_orig2roi_mat": "T1_orig2roi.mat",
    "t1_orig2std_mat": "T1_orig2std.mat",
    "t1_roi_log": "T1_roi.log",
    "t1_roi2nonroi_mat": "T1_roi2nonroi.mat",
    "t1_roi2orig_mat": "T1_roi2orig.mat",
    "t1_std2orig_mat": "T1_std2orig.mat",
    "t1_subcort_seg": "T1_subcort_seg.nii.gz",
    "t1_to_mni_lin_mat": "T1_to_MNI_lin.mat",
    "t1_to_mni_lin": "T1_to_MNI_lin.nii.gz",
    "t1_to_mni_nonlin": "T1_to_MNI_nonlin.nii.gz",
    "t1_to_mni_nonlin_txt": "T1_to_MNI_nonlin.txt",
    "t1_to_mni_nonlin_coeff": "T1_to_MNI_nonlin_coeff.nii.gz",
    "t1_to_mni_nonlin_field": "T1_to_MNI_nonlin_field.nii.gz",
    "t1_to_mni_nonlin_jac": "T1_to_MNI_nonlin_jac.nii.gz",
    "t1_vols_txt": "T1_vols.txt",
    "lesionmask": "lesionmask.nii.gz",
    "lesionmaskinv": "lesionmaskinv.nii.gz",
    "log_txt": "log.txt",
}


class FSLAnatInputSpecBase(fsl.base.FSLCommandInputSpec):
    clobber = base.traits.Bool(
        default_value=False,
        argstr="--clobber",
        desc="if .anat directory exist (as specified by -o or default from -i) "
        "then delete it and make a new one",
    )
    strongbias = base.traits.Bool(
        default_value=False,
        argstr="--strongbias",
        desc="used for images with very strong bias fields",
        xor=["weakbias"],
    )
    weakbias = base.traits.Bool(
        default_value=True,
        argstr="--weakbias",
        desc="used for images with smoother, more typical, bias fields (default "
        "setting)",
        xor=["strongbias"],
    )
    noreorient = base.traits.Bool(
        default_value=False,
        argstr="--noreorient",
        desc="turn off step that does reorientation 2 standard (fslreorient2std)",
    )
    nocrop = base.traits.Bool(
        default_value=False,
        argstr="--nocrop",
        desc="turn off step that does automated cropping (robustfov)",
    )
    nobias = base.traits.Bool(
        default_value=False,
        argstr="--nobias",
        desc="turn off steps that do bias field correction (via FAST)",
    )
    noreg = base.traits.Bool(
        default_value=False,
        argstr="--noreg",
        desc="turn off steps that do registration to standard (FLIRT and FNIRT)",
    )
    nononlinreg = base.traits.Bool(
        default_value=False,
        argstr="--nononlinreg",
        desc="turn off step that does non-linear registration (FNIRT)",
    )
    noseg = base.traits.Bool(
        default_value=False,
        argstr="--noseg",
        desc="turn off step that does tissue-type segmentation (FAST)",
    )
    nosubcortseg = base.traits.Bool(
        default_value=False,
        argstr="--nosubcortseg",
        desc="turn off step that does sub-cortical segmentation (FIRST)",
    )
    smoothing = base.traits.Float(
        argstr="-s %.2f",
        desc="specify the value for bias field smoothing (the -l option in FAST)",
    )
    image_type = base.traits.Enum(
        "T1",
        "T2",
        "PD",
        argstr="-t %s",
        desc="specify the type of image (choose one of T1 T2 PD - default is T1)",
    )
    nosearch = base.traits.Bool(
        default_value=False,
        argstr="--nosearch",
        desc="specify that linear registration uses the -nosearch option (FLIRT)",
    )
    betfparam = base.traits.Bool(
        default_value=False,
        argstr="--betfparam",
        desc="specify f parameter for BET (only used if not running non-linear "
        "reg and also wanting brain extraction done)",
    )
    nocleanup = base.traits.Bool(
        default_value=False,
        argstr="--nocleanup",
        desc="do not remove intermediate files",
    )


class FSLAnatInputSpec(FSLAnatInputSpecBase):
    in_file = base.traits.File(
        argstr="-i %s",
        exists=True,
        mandatory=True,
        desc="filename of input image (for one image only)",
        xor=["in_dir"],
    )
    in_dir = base.traits.Directory(
        argstr="-d %s",
        exists=True,
        mandatory=True,
        desc="directory name for existing .anat directory where this "
        "script will be run in place",
        xor=["in_file"],
    )
    out_dir_basename = base.traits.Directory(
        argstr="-o %s",
        genfile=True,
        desc="basename of directory for output (default is input image "
        "basename followed by .anat)",
        requires=["in_file"],
    )


class FSLAnatOutputSpecMeta(base.traits.MetaHasTraits):
    def __new__(cls, name, bases, dct):
        for outputname in FSL_ANAT_OUTPUT_FILENAMES.keys():
            dct[outputname] = base.traits.File()
        return super().__new__(cls, name, bases, dct)


class FSLAnatOutputSpec(base.TraitedSpec, metaclass=FSLAnatOutputSpecMeta):
    """See the dict `FSL_ANAT_OUTPUT_FILENAMES` for which traits/files are
    available as outputs from this interface.

    The traits are injected into this class programmatically via
    the metaclass `FSLAnatOutputSpecMeta`
    """

    out_dir = base.traits.Directory(
        desc="basename of directory for output (default is input image "
        "basename followed by .anat)",
    )


class FSLAnat(fsl.base.FSLCommand):
    _cmd = str(Path(os.environ["FSLDIR"]) / "bin" / "fsl_anat")
    input_spec = FSLAnatInputSpec
    output_spec = FSLAnatOutputSpec

    def _list_outputs(self):
        outputs = self.output_spec().get()

        out_dir = self._get_out_dir()
        outputs["out_dir"] = out_dir

        for outputname, filename in FSL_ANAT_OUTPUT_FILENAMES.items():
            outputs[outputname] = out_dir / filename

        return outputs

    def _gen_filename(self, name: str) -> Path | None:
        if name == "out_dir_basename":
            return Path.cwd() / "struct"

    def _get_out_dir(self) -> Path:
        in_dir = self.inputs.in_dir
        if isdefined(in_dir):
            # fsl_anat was run in-place
            return Path(in_dir)

        out_dir_basename = self.inputs.out_dir_basename
        if isdefined(out_dir_basename):
            # fsl_anat was run with a user-specified directory basename
            out = Path(out_dir_basename)
            if not out.is_absolute():
                out = Path.cwd() / out
            return out.with_name(f"{out.name}.anat")

        generated_basename = self._gen_filename("out_dir_basename")
        if generated_basename:
            # no output directory was specified so the we must have
            # used the generated one
            return generated_basename.with_name(f"{generated_basename.name}.anat")

        raise AssertionError("Unreachable")


class OptionalFSLAnatInputSpec(FSLAnatInputSpecBase):
    in_data = base.traits.Either(
        base.traits.File(
            exists=True,
            desc="filename of input image (for one image only)",
        ),
        base.traits.Directory(
            exists=True,
            desc="directory name for existing .anat directory where this "
            "script will be run in place",
        ),
        mandatory=True,
    )
    # out_dir_basename is "duplicated" because we need to override the 'xor' argument
    out_dir_basename = base.traits.Directory(
        argstr="-o %s",
        genfile=True,
        desc="basename of directory for output (default is input image "
        "basename followed by .anat)",
    )


class OptionalFSLAnatOutputSpec(FSLAnatOutputSpec):
    pass


class OptionalFSLAnat(base.BaseInterface):
    input_spec = OptionalFSLAnatInputSpec
    output_spec = OptionalFSLAnatOutputSpec

    _fsl_anat_outputs: dict[str, Any]

    def _run_interface(self, runtime: RuntimeContext) -> RuntimeContext:

        inputs = self.inputs.get()
        in_data = Path(inputs.pop("in_data"))
        clobber = inputs["clobber"]

        is_nii_file = in_data.is_file() and NII_FILE_REGEXP.match(in_data.name)
        is_fsl_anat_dir = in_data.is_dir() and FSL_ANAT_DIR_REGEXP.match(in_data.name)

        # check if we're given an fsl_anat output directory + clober is either
        # undefined or is falsey, in this case bail early and "mock" the outputs
        if is_fsl_anat_dir and not (isdefined(clobber) and clobber):
            self._log_skipping_fsl_anat_execution()
            self._fsl_anat_outputs = {"out_dir": in_data}
            for outputname, filename in FSL_ANAT_OUTPUT_FILENAMES.items():
                self._fsl_anat_outputs[outputname] = in_data / filename
            return runtime

        # at this point we know we should execute fsl_anat (the interface), we
        # just need to know if it's of the form 'fsl_anat -i ...' or 'fsl_anat -d ...'
        if is_nii_file:
            inputs["in_file"] = in_data
        elif is_fsl_anat_dir:
            inputs["in_dir"] = in_data
        else:
            msg = (
                f"Unprocessable input data. {self.__class__.__name__} expected "
                "as input data either: an NIfTI file or an existing FSL ANAT "
                f"results directory of the form *.anat/. Found [{in_data}]"
            )
            raise ValueError(msg)

        fsl_anat = FSLAnat(**inputs)
        result = fsl_anat.run()
        self._fsl_anat_outputs = result.outputs.get()  # type: ignore

        return runtime

    def _list_outputs(self):
        return self._fsl_anat_outputs  # type: ignore

    def _log_skipping_fsl_anat_execution(self):
        iflogger = logging.getLogger("nipype.interface")
        msg = (
            f"Input data [{self.inputs.in_data}] appears to be an "
            "fsl_anat output directory and the clobber parameter is either "
            f"undefined or set to False. {self.__class__.__name__} is a "
            "no-op (pass-through) in this case."
        )
        iflogger.info(msg)
