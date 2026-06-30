#/bin/bash

export HOME="/projetos/$(whoami)"
export PATH="$HOME/.miniforge3/bin:$PATH"

conda init
