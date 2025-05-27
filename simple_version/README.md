# 简化版远程桌面控制系统

这是一个简化版的远程桌面控制系统，基于TCP/IP和UDP协议实现，不包含ROS架构的复杂性，更容易上手使用。

## 主要功能

- **屏幕共享**：实时传输远程计算机的屏幕内容
- **鼠标控制**：远程操作目标计算机的鼠标

## 使用方法

### 服务端（被控制方）

1. 运行 `simple_start.bat` 启动服务端
2. 记下显示的IP地址

### 客户端（控制方）

1. 运行 `simple_client.bat` 启动客户端
2. 输入服务端IP地址连接
3. 使用界面上的控制选项开启/关闭鼠标控制

## 故障排除

如果遇到PyAutoGUI安全机制触发的错误：

```
PyAutoGUI fail-safe triggered from mouse moving to a corner of the screen
```

表示鼠标移动到了屏幕边角触发了安全机制。服务端已禁用此功能，如仍有问题，可检查代码中的`pyautogui.FAILSAFE = False`设置是否生效。 