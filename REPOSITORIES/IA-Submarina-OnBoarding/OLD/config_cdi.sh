#!/bin/bash

MF_HOME="/projetos/$(whoami)"

DEFAULT_ENV_NAME="meu-ambiente"
DEFAULT_PYTHON_VERSION="3.10"
DEFAULT_DISPLAY_NAME="Ambiente Python"

read -p "Nome do ambiente conda (padrão: $DEFAULT_ENV_NAME): " ENV_NAME
ENV_NAME=${ENV_NAME:=$DEFAULT_ENV_NAME}

read -p "Versão do Python (padrão: $DEFAULT_PYTHON_VERSION): " PYTHON_VERSION
PYTHON_VERSION=${PYTHON_VERSION:=$DEFAULT_PYTHON_VERSION}

read -p "Nome para exibição no Jupyter (padrão: ${DEFAULT_DISPLAY_NAME} ${PYTHON_VERSION}): " DISPLAY_NAME
DISPLAY_NAME=${DISPLAY_NAME:="$DEFAULT_DISPLAY_NAME $PYTHON_VERSION"}

echo ""
echo "Configuração escolhida:"
echo "- Nome do ambiente: $ENV_NAME"
echo "- Versão do Python: $PYTHON_VERSION"
echo "- Nome de exibição: $DISPLAY_NAME"

echo ""
read -p "Confirmar configuração? (s/n): " CONFIRM

if [[ ! "$CONFIRM" =~ ^[Ss]$ ]]; then
    echo "Instalação cancelada pelo usuário."
    exit 0
fi

echo "Verificando instalações anteriores..."

clean_previous_installation() {
    jupyter kernelspec list 2>/dev/null | grep -q "$ENV_NAME" && {
        echo "Removendo kernel Jupyter anterior..."
        jupyter kernelspec uninstall -y "$ENV_NAME" 2>/dev/null || true
    }
    if conda env list | grep -q "$ENV_NAME"; then
        echo "Removendo ambiente conda anterior..."
        conda deactivate 2>/dev/null || true
        conda env remove -n "$ENV_NAME" -y
    fi
}

if [ -d "$MF_HOME/.miniforge3" ]; then
    echo "Miniforge já instalado, usando a instalação existente."
    export PATH="$MF_HOME/.miniforge3/bin:$PATH"
    clean_previous_installation
else
    echo "Iniciando instalação do Miniforge..."
    wget "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-$(uname)-$(uname -m).sh"
    bash Miniforge3-$(uname)-$(uname -m).sh -b -p $MF_HOME/.miniforge3
    export PATH="$MF_HOME/.miniforge3/bin:$PATH"
fi

echo "Configurando conda/mamba..."
conda config --system --remove-key channels 2>/dev/null || true
conda config --system --append channels http://nexus.petrobras.com.br/nexus/repository/conda-pytorch/
conda config --system --append channels http://nexus.petrobras.com.br/nexus/repository/conda-nvidia/
conda config --system --append channels http://nexus.petrobras.com.br/nexus/repository/conda-forge/
conda config --system --remove channels defaults 2>/dev/null || true
conda config --system --remove-key default_channels 2>/dev/null || true
conda config --system --append default_channels http://nexus.petrobras.com.br/nexus/repository/conda-forge/
conda config --system --set remote_read_timeout_secs 60

echo "Configurando pip..."
pip config set global.index-url http://nexus.petrobras.com.br/nexus/repository/pypi-all/simple
pip config set global.timeout 60
pip config set global.trusted-host nexus.petrobras.com.br

export PIP_REQUIRE_VIRTUALENV=false
grep -q "export PIP_REQUIRE_VIRTUALENV=false" ~/.bashrc || echo 'export PIP_REQUIRE_VIRTUALENV=false' >> ~/.bashrc

echo "Criando ambiente virtual $ENV_NAME com Python $PYTHON_VERSION..."
conda create -y -n "$ENV_NAME" python="$PYTHON_VERSION"
source $MF_HOME/.miniforge3/bin/activate "$ENV_NAME"

if [ -f requirements.txt ]; then
    echo "Instalando pacotes do requirements.txt..."
    pip install -r requirements.txt
    pip install ipykernel
    python -m ipykernel install --user --name "$ENV_NAME" --display-name "$DISPLAY_NAME"
else
    echo "AVISO: Arquivo requirements.txt não encontrado."
    echo "Instalando pacotes padrão..."
    pip install numpy pandas matplotlib scikit-learn tensorflow
    pip install ipykernel
    python -m ipykernel install --user --name "$ENV_NAME" --display-name "$DISPLAY_NAME"
fi

echo ""
echo "========================================================================"
echo "Instalação completa! Ambiente '$ENV_NAME' está ativo."
echo "Para ativar este ambiente no futuro, use: conda activate $ENV_NAME"
echo "O kernel Jupyter '$DISPLAY_NAME' está disponível."
echo "========================================================================"
