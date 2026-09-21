#!/bin/bash
eval "$(conda shell.bash hook)"
source ~/miniforge3/etc/profile.d/mamba.sh
mamba create -n single-cell python=3.11 pip setuptools wheel swig numpy \
 scipy "pandas<2.0.0" "matplotlib<3.9" seaborn=0.11.2 scikit-learn \
 statsmodels traits=6.4.* natsort numexpr bottleneck python-igraph \
 "ipython<8.24" ipykernel numba -y
mamba activate single-cell
pip install --no-deps fcsparser camel
cd ~/cytoflow/.
git checkout 1.2.2 --force
pip install -v --no-deps --no-build-isolation .
cd ~
pip install --no-deps flowkit flowutils
pip install flowio pyarrow==18 bokeh anytree lxml ipympl "seaborn>0.13"

