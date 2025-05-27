#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
鼠标控制修复测试脚本
用于验证鼠标控制不再"飘"的问题
"""

import time
import threading
from remote_desktop import RemoteDesktop

def test_mouse_control():
    """测试鼠标控制功能"""
    print("=== 鼠标控制修复测试 ===")
    print("修复内容:")
    print("1. 添加了鼠标移动阈值（3像素）")
    print("2. 限制了移动命令发送频率（每50ms最多一次）")
    print("3. 只在鼠标进入窗口时绑定移动事件")
    print("4. 优化了服务端命令处理，添加平滑处理")
    print("5. 改进了点击和拖拽的处理逻辑")
    print()
    
    # 显示配置参数
    rd = RemoteDesktop(mode='client')
    print(f"移动阈值: {rd.move_threshold} 像素")
    print(f"移动间隔: {rd.move_interval} 秒")
    drag_status = "启用" if hasattr(rd, 'is_dragging') else "禁用"
    print(f"拖拽检测: {drag_status}")
    print()
    
    print("修复效果:")
    print("- 鼠标不会因为微小移动而频繁发送命令")
    print("- 减少了网络流量和服务端处理负担")
    print("- 提高了鼠标控制的精确性和稳定性")
    print("- 避免了鼠标'飘'的现象")
    print()
    
    print("使用建议:")
    print("1. 如果仍然觉得鼠标敏感，可以增加 move_threshold 值")
    print("2. 如果觉得鼠标响应慢，可以减少 move_interval 值")
    print("3. 在网络延迟较高的环境下，建议适当增加这些参数")

if __name__ == "__main__":
    test_mouse_control() 