echo "Installing the necessary packages ..."
pip install -r script/requirements.txt

echo "Installing pytorch3d ..."
# cd third_party/pytorch3d_simplified
# pip install -e .
# cd ../..
pip install "git+https://github.com/facebookresearch/pytorch3d.git@stable"

echo "Adjusting code in sapien/wrapper/urdf_loader.py ..."
# location of sapien, like "~/.conda/envs/RoboTwin/lib/python3.10/site-packages/sapien"
SAPIEN_LOCATION=$(pip show sapien | grep 'Location' | awk '{print $2}')/sapien
# Adjust some code in wrapper/urdf_loader.py
URDF_LOADER=$SAPIEN_LOCATION/wrapper/urdf_loader.py
# ----------- before -----------
# 667         with open(urdf_file, "r") as f:
# 668             urdf_string = f.read()
# 669 
# 670         if srdf_file is None:
# 671             srdf_file = urdf_file[:-4] + "srdf"
# 672         if os.path.isfile(srdf_file):
# 673             with open(srdf_file, "r") as f:
# 674                 self.ignore_pairs = self.parse_srdf(f.read())
# ----------- after  -----------
# 667         with open(urdf_file, "r", encoding="utf-8") as f:
# 668             urdf_string = f.read()
# 669 
# 670         if srdf_file is None:
# 671             srdf_file = urdf_file[:-4] + ".srdf"
# 672         if os.path.isfile(srdf_file):
# 673             with open(srdf_file, "r", encoding="utf-8") as f:
# 674                 self.ignore_pairs = self.parse_srdf(f.read())
sed -i -E 's/("r")(\))( as)/\1, encoding="utf-8") as/g' $URDF_LOADER

# Note: the mplib planner.py "drop collide bail" patch is intentionally NOT
# applied here. mplib is a vestigial code path in the RLinf/RPent runtime:
# robots/robotwin/env_server.py hardcodes planner_backend="curobo", and no
# code path sets planner_backend="mplib" (only the default-fallback and the
# unused `elif mplib` branch in robotwin/envs/robot/robot.py exist). The
# MplibWrapperPlanner is therefore never instantiated in production, so
# patching mplib/planner.py has no effect on eval or data collection. The
# patch is dropped to slim the install contract. (MplibWrapperPlanner is left
# in place as an optional backend; mplib==0.2.1 remains a declared dep until
# the inference-only dep review.)

echo "Installing Curobo (pinned @ d64c4b, --no-build-isolation) ..."
# cuRobo is no longer vendored. Install the exact upstream commit (d64c4b)
# that was previously vendored, with --no-build-isolation so its CUDA
# extensions compile against the already-installed torch==2.8.0+cu128
# (curobo's [build-system] requires torch unpinned, which would pull a
# wrong torch under build isolation). See pyproject.toml note.
pip install --no-build-isolation "curobo @ git+https://github.com/NVlabs/curobo.git@d64c4b005459db10c5dd867d8b30a87d5bda9bdb"

echo "Installation basic environment complete!"
echo -e "You need to:"
echo -e "    1. \033[34m\033[1m(Important!)\033[0m Download asserts from huggingface."
echo -e "    2. Install requirements for running baselines. (Optional)"
echo "See INSTALLATION.md for more instructions."
