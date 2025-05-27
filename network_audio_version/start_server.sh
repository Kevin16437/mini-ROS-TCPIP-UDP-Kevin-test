#!/bin/bash
echo "启动远程桌面服务端..."
echo "激活conda环境..."
conda activate remote_desktop
python remote_desktop.py --mode server 