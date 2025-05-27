#!/bin/bash
echo "激活conda环境..."
conda activate remote_desktop
echo "请输入Windows服务器的IP地址："
read SERVER_IP
echo "正在连接到服务器 $SERVER_IP ..."
python client_fallback.py --host $SERVER_IP 