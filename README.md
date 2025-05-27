# 远程桌面控制系统集合

这个项目包含三个不同版本的远程桌面控制系统，基于Python实现，使用TCP/IP和UDP协议在局域网内进行通信。

## 项目结构

- **[ros_version](./ros_version)**: 模拟ROS架构的远程桌面控制系统
  - 实现了类似ROS的节点管理和话题机制
  - 包含完整的远程控制功能

- **[simple_version](./simple_version)**: 简化版远程桌面控制系统
  - 不包含ROS架构的复杂性
  - 轻量级实现，适合快速部署

- **[network_audio_version](./network_audio_version)**: 集成音频功能的远程桌面控制系统
  - 在简化版的基础上添加了双向语音通信
  - 支持屏幕共享、鼠标控制和语音传输

## 选择指南

- 如果你希望学习类似ROS的架构设计，选择 `ros_version`
- 如果你需要一个简单易用的远程控制工具，选择 `simple_version`
- 如果你需要远程协作时进行语音通话，选择 `network_audio_version`

## 通用故障排除

1. **端口占用问题**
   ```
   [WinError 10048] 通常每个套接字地址(协议/网络地址/端口)只允许使用一次
   ```
   解决方法：
   - 确保没有其他远程桌面程序正在运行
   - 使用任务管理器结束所有Python进程：`taskkill /f /im python.exe`
   - 重启计算机

2. **PyAutoGUI安全机制触发**
   ```
   PyAutoGUI fail-safe triggered from mouse moving to a corner of the screen
   ```
   解决方法：
   - 最新版本已在代码中禁用了这一安全机制
   - 如果问题依然存在，请检查代码中的`pyautogui.FAILSAFE = False`设置

## 系统要求

- Python 3.6+
- 所需依赖：opencv-python, numpy, pyautogui, pyaudio, pillow
- 建议在同一局域网内使用

## 许可协议

MIT许可证 