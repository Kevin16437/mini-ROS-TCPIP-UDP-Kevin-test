#!/bin/bash
echo "=== 本机远程桌面测试 ==="
echo "激活conda环境..."
conda activate remote_desktop

echo ""
echo "1. 启动服务端（后台运行）..."
python remote_desktop.py --mode server &
SERVER_PID=$!
echo "服务端PID: $SERVER_PID"

echo ""
echo "2. 等待服务端启动..."
sleep 3

echo ""
echo "3. 启动客户端连接到本机..."
echo "按 Ctrl+C 可以退出客户端"
python client_fallback.py --host 127.0.0.1

echo ""
echo "4. 清理后台进程..."
kill $SERVER_PID 2>/dev/null
echo "测试完成！" 