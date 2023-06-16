#!/bin/bash

# set -e

# OVERVIEW
# Creates a conda environment for a specific version of python

# sudo -u ec2-user -i <<'EOF'
# PARAMETERS
PYTHON_VERSION=3.9
ENVIRONMENT=demo_environment

echo "Creating new environment: $ENVIRONMENT..."
# source /home/ec2-user/anaconda3/etc/profile.d/conda.sh
source activate
conda create --yes --name "$ENVIRONMENT" python="$PYTHON_VERSION"
conda activate "$ENVIRONMENT"
conda install --yes ipykernel
echo "Environment creation complete"

# The following installs the project dependencies during the
# lifecycle configuration, but it may exceed the 5 min limit
# Your notebook will fail to start if you exceed the limit

# cd ~/SageMaker/carbon-assessment-with-ml
echo "Installing dependencies..."
pip install --quiet -r requirements.txt
pip install --quiet -e .
echo "Dependency installation complete"
