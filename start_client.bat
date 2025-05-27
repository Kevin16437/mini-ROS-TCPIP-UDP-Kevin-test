@echo off
set /p SERVER_IP=请输入服务器IP地址: 
echo 连接到服务器 %SERVER_IP% ...
python network_client.py --host %SERVER_IP%
pause 