#!/bin/bash
echo "请输入Windows服务器的IP地址："
read SERVER_IP
echo "正在连接到服务器 $SERVER_IP ..."
python3 remote_desktop.py --mode client --host $SERVER_IP 