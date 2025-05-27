@echo off
echo 检查端口占用情况...

:: 检查端口是否被占用
netstat -ano | findstr :8485 >nul
if %errorlevel% equ 0 (
    echo 端口8485被占用，正在释放...
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8485') do (
        taskkill /F /PID %%a
    )
)

netstat -ano | findstr :8486 >nul
if %errorlevel% equ 0 (
    echo 端口8486被占用，正在释放...
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8486') do (
        taskkill /F /PID %%a
    )
)

netstat -ano | findstr :8487 >nul
if %errorlevel% equ 0 (
    echo 端口8487被占用，正在释放...
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8487') do (
        taskkill /F /PID %%a
    )
)

echo 启动远程桌面服务端...
python remote_desktop.py --mode server
pause 