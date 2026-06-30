#!/bin/bash

set -euo pipefail

# ================================
# Default values
# ================================
DEFAULT_ENV_NAME="my-environment"
DEFAULT_PYTHON_VERSION="3.10"
DEFAULT_DISPLAY_NAME="Python Environment"

ENV_NAME=""
PYTHON_VERSION=""
DISPLAY_NAME=""
AUTO_YES=0

# ================================
# Function for heredoc printing
# ================================
print_block() {
cat <<EOF
$1
EOF
}

# ================================
# Parse flags
# ================================
while [[ $# -gt 0 ]]; do
    case "$1" in
        --env)
            ENV_NAME="$2"
            shift 2
            ;;
        --python)
            PYTHON_VERSION="$2"
            shift 2
            ;;
        --display)
            DISPLAY_NAME="$2"
            shift 2
            ;;
        --yes|-y)
            AUTO_YES=1
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# ================================
# Interactive fallback
# ================================
if [[ -z "$ENV_NAME" ]]; then
    read -p "Conda environment name (default: $DEFAULT_ENV_NAME): " ENV_NAME
    ENV_NAME=${ENV_NAME:-$DEFAULT_ENV_NAME}
fi

if [[ -z "$PYTHON_VERSION" ]]; then
    read -p "Python version (default: $DEFAULT_PYTHON_VERSION): " PYTHON_VERSION
    PYTHON_VERSION=${PYTHON_VERSION:-$DEFAULT_PYTHON_VERSION}
fi

if [[ -z "$DISPLAY_NAME" ]]; then
    read -p "Jupyter display name (default: $DEFAULT_DISPLAY_NAME $DEFAULT_PYTHON_VERSION): " DISPLAY_NAME
    DISPLAY_NAME=${DISPLAY_NAME:-"$DEFAULT_DISPLAY_NAME $PYTHON_VERSION"}
fi

print_block "Selected Configuration:
- Environment name: $ENV_NAME
- Python version: $PYTHON_VERSION
- Display name: $DISPLAY_NAME
"

if [[ "$AUTO_YES" -eq 0 ]]; then
    read -p "Confirm configuration? (y/n): " CONFIRM
    if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
        echo "Installation cancelled."
        exit 0
    fi
fi

# ================================
# Cleanup function
# ================================
clean_previous_installation() {
  if jupyter kernelspec list 2>/dev/null | grep -q "$ENV_NAME"; then
        echo "Removing previous Jupyter kernel..."
        jupyter kernelspec uninstall -y "$ENV_NAME" 2>/dev/null || true
    fi
  if conda env list | grep -q "$ENV_NAME"; then
        echo "Removing previous conda environment..."
        conda deactivate 2>/dev/null || true
        conda env remove -n "$ENV_NAME" -y
    fi
}

# ================================
# Miniforge installation
# ================================
if [ -d "$HOME/miniforge3" ]; then
    echo "Miniforge already installed."
else
    print_block "Installing Miniforge..."
  FILE="Miniforge3-$(uname)-$(uname -m).sh"
    URL="https://github.com/conda-forge/miniforge/releases/latest/download/${FILE}"
  wget -q --show-progress "$URL" || { echo "Download failed."; exit 1; }
    bash "$FILE" -b -p "$HOME/miniforge3"
    rm "$FILE"
fi

export PATH="$HOME/miniforge3/bin:$PATH"

clean_previous_installation

# ================================
# Conda configuration
# ================================
print_block "Configuring conda..."

conda config --remove-key channels 2>/dev/null || true
conda config --append channels http://nexus.petrobras.com.br/nexus/repository/conda-pytorch/
conda config --append channels http://nexus.petrobras.com.br/nexus/repository/conda-nvidia/
conda config --append channels http://nexus.petrobras.com.br/nexus/repository/conda-forge/
conda config --remove channels defaults 2>/dev/null || true
conda config --remove-key default_channels 2>/dev/null || true
conda config --append default_channels http://nexus.petrobras.com.br/nexus/repository/conda-forge/
conda config --set remote_read_timeout_secs 60

# ================================
# Pip configuration
# ================================
print_block "Configuring pip..."

pip config set global.index-url http://nexus.petrobras.com.br/nexus/repository/pypi-all/simple
pip config set global.timeout 60
pip config set global.trusted-host nexus.petrobras.com.br

export PIP_REQUIRE_VIRTUALENV=false
grep -q "export PIP_REQUIRE_VIRTUALENV=false" ~/.bashrc || echo 'export PIP_REQUIRE_VIRTUALENV=false' >> ~/.bashrc

# ================================
# Activate base env
# ================================
source "$HOME/miniforge3/bin/activate"
conda activate base

# ================================
# Create environment with conda
# ================================
print_block "Creating environment '$ENV_NAME' with Python $PYTHON_VERSION..."

conda create -y -n "$ENV_NAME" python="$PYTHON_VERSION"
conda activate "$ENV_NAME"

# ================================
# Package installation
# ================================
if [ -f "requirements.txt" ]; then
    print_block "Installing packages from requirements.txt..."
    pip install -r requirements.txt
else
    print_block "requirements.txt not found. Installing default packages..."
    pip install numpy pandas matplotlib scikit-learn tensorflow
fi

pip install ipykernel

print_block "Registering Jupyter kernel..."
python -m ipykernel install --user --name "$ENV_NAME" --display-name "$DISPLAY_NAME"

# ================================
# Done
# ================================
print_block "Installation complete!
Environment '$ENV_NAME' is ready.

Activate it anytime with:
  conda activate $ENV_NAME

The Jupyter kernel '$DISPLAY_NAME' is now available.
"