#!/bin/bash

# Caminho para o repositório git
REPO_PATH="/home/pi/data-acquisition-probe"

# Caminho para o script Python
PYTHON_SCRIPT="/home/pi/data-acquisition-probe/stream_server.py"

# Executa git pull
cd $REPO_PATH
git pull

# Executa o script Python
python3 $PYTHON_SCRIPT
