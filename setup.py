"""Build the pinned cuRobo CUDA extensions into the RoboTwin runtime wheel."""

from __future__ import annotations

from pathlib import Path

from setuptools import setup
from torch.utils.cpp_extension import BuildExtension, CUDAExtension

CUROBO_ROOT = Path("vendor") / "curobo"

if not CUROBO_ROOT.is_dir():
    raise RuntimeError("run prepare_curobo.py before building the runtime wheel")

CUDA_ARGS = {
    "nvcc": [
        "--threads=8",
        "-O3",
        "--ftz=true",
        "--fmad=true",
        "--prec-div=false",
        "--prec-sqrt=false",
    ]
}

KERNELS = {
    "lbfgs_step": ["lbfgs_step_cuda.cpp", "lbfgs_step_kernel.cu"],
    "kinematics_fused": ["kinematics_fused_cuda.cpp", "kinematics_fused_kernel.cu"],
    "line_search": [
        "line_search_cuda.cpp",
        "line_search_kernel.cu",
        "update_best_kernel.cu",
    ],
    "tensor_step": ["tensor_step_cuda.cpp", "tensor_step_kernel.cu"],
    "geom": [
        "geom_cuda.cpp",
        "sphere_obb_kernel.cu",
        "pose_distance_kernel.cu",
        "self_collision_kernel.cu",
    ],
}

kernel_root = CUROBO_ROOT / "src" / "curobo" / "curobolib" / "cpp"
extensions = [
    CUDAExtension(
        f"curobo.curobolib.{name}_cu",
        [(kernel_root / source).as_posix() for source in sources],
        extra_compile_args=CUDA_ARGS,
    )
    for name, sources in KERNELS.items()
]

setup(ext_modules=extensions, cmdclass={"build_ext": BuildExtension})
