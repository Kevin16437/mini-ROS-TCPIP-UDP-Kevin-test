# 远程屏幕共享系统

这是一个简单的远程屏幕共享系统，使用TCP/IP协议实现屏幕内容的传输和显示。

## 功能特点

- 实时屏幕捕获和传输
- 高效的图像压缩
- 简单的GUI界面
- 支持多客户端连接

## 系统要求

- Python 3.8+
- 依赖包：
  - opencv-python
  - numpy
  - pyautogui
  - pillow
  - tkinter

## 安装

1. 安装Python依赖：
```bash
pip install opencv-python numpy pyautogui pillow
```

## 使用方法

1. 运行服务端（屏幕捕获）：
```bash
python screen_capture_node.py
```

2. 运行客户端（屏幕查看）：
```bash
python remote_viewer_node.py
```

或者直接运行 `start_ros.bat` 启动整个系统。

## 配置说明

- 服务端默认监听端口：8485
- 图像质量：50%（可调整）
- 目标帧率：30 FPS
- 最大分辨率：1280x720

## 注意事项

1. 确保防火墙允许程序网络访问
2. 建议在局域网内使用
3. 需要管理员权限运行 