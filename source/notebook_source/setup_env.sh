#!/bin/bash

# Creates a conda environment and installs project dependencies

# PARAMETERS
PYTHON_VERSION=3.9
ENVIRONMENT=demo_environment

echo "Creating new environment: $ENVIRONMENT..."
source activate
conda create --yes --name "$ENVIRONMENT" python="$PYTHON_VERSION"
conda activate "$ENVIRONMENT"
conda install --yes ipykernel
echo "Environment creation complete"

echo "Installing dependencies..."
pip install --quiet -r requirements.txt
pip install --quiet -e .
echo "Dependency installation complete"
