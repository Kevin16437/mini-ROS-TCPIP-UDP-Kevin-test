#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单启动脚本 - 直接启动所有组件
"""

import subprocess
import time
import os
import sys

def main():
    print("=" * 60)
    print("模拟ROS远程桌面系统 - 简单启动")
    print("=" * 60)
    print()
    
    # 检查依赖
    print("检查依赖...")
    try:
        import cv2
        import numpy
        import pyautogui
        import PIL
        print("✓ 所有依赖已安装")
    except ImportError as e:
        print(f"✗ 缺少依赖: {e}")
        print("请运行: pip install -r requirements.txt")
        input("按回车键退出...")
        return
    
    print()
    print("启动系统组件...")
    print()
    
    try:
        # 启动服务端
        print("1. 启动屏幕捕获服务端...")
        if os.name == 'nt':  # Windows
            subprocess.Popen('start "Screen Capture Server" cmd /k "python screen_capture_node.py"', shell=True)
        else:
            subprocess.Popen(['python', 'screen_capture_node.py'])
        
        # 等待服务端启动
        print("   等待服务端启动...")
        time.sleep(3)
        
        # 启动客户端
        print("2. 启动远程查看器客户端...")
        if os.name == 'nt':  # Windows
            subprocess.Popen('start "Remote Viewer Client" cmd /k "python remote_viewer_node.py"', shell=True)
        else:
            subprocess.Popen(['python', 'remote_viewer_node.py'])
        
        # 等待客户端启动
        print("   等待客户端启动...")
        time.sleep(2)
        
        # 启动监控节点
        print("3. 启动系统监控节点...")
        if os.name == 'nt':  # Windows
            subprocess.Popen('start "System Monitor" cmd /k "python demo.py"', shell=True)
        else:
            subprocess.Popen(['python', 'demo.py'])
        
        print()
        print("=" * 60)
        print("✓ 所有组件启动完成！")
        print()
        print("您应该看到以下窗口：")
        print("1. 服务端控制台 - 显示连接和命令信息")
        print("2. 客户端GUI - 带有视频框的远程控制界面")
        print("3. 监控控制台 - 显示系统运行统计")
        print()
        print("使用说明：")
        print("• 在客户端窗口的黑色视频框中移动鼠标")
        print("• 点击视频框执行远程点击")
        print("• 键盘输入会传输到服务端")
        print()
        print("要停止系统，请关闭各个窗口或按Ctrl+C")
        print("=" * 60)
        
        # 保持脚本运行
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n正在退出...")
            
    except Exception as e:
        print(f"启动失败: {e}")
        input("按回车键退出...")

if __name__ == '__main__':
    main() 