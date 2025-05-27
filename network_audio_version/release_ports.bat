@echo off
echo 正在检查并释放远程桌面程序使用的端口...

:: 检查并释放8485端口
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8485') do (
    echo 发现占用8485端口的进程: %%a
    taskkill /F /PID %%a
    echo 已终止进程: %%a
)

:: 检查并释放8486端口
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8486') do (
    echo 发现占用8486端口的进程: %%a
    taskkill /F /PID %%a
    echo 已终止进程: %%a
)

:: 检查并释放8487端口
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8487') do (
    echo 发现占用8487端口的进程: %%a
    taskkill /F /PID %%a
    echo 已终止进程: %%a
)

echo.
echo 端口释放完成！
echo 如果显示"未找到进程"，说明端口未被占用
echo.
pause 