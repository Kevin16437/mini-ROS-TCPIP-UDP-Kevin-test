#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
远程桌面客户端 - 带GUI回退机制
如果tkinter不可用，则使用简化模式
"""

import socket
import cv2
import numpy as np
import struct
import time
import argparse
import threading
import json

# 尝试导入GUI相关模块
GUI_AVAILABLE = False
try:
    import tkinter as tk
    from tkinter import ttk
    from PIL import Image, ImageTk
    GUI_AVAILABLE = True
    print("GUI模式可用")
except ImportError as e:
    print(f"GUI模式不可用: {e}")
    print("将使用简化模式")

class RemoteDesktopClient:
    def __init__(self, host='192.168.1.4', screen_port=8485, control_port=8486, audio_port=8487):
        self.host = host
        self.screen_port = screen_port
        self.control_port = control_port
        self.audio_port = audio_port
        
        self.running = False
        self.screen_socket = None
        self.control_socket = None
        self.audio_socket = None
        
        # GUI相关
        self.root = None
        self.video_label = None
        self.status_label = None
        self.fps_label = None
        
        # 性能统计
        self.fps = 0
        self.frame_count = 0
        self.last_time = time.time()
        
        # 控制相关
        self.control_enabled = True
        self.mouse_pos = (0, 0)
        
    def connect(self):
        """连接到服务器"""
        try:
            print(f"正在连接到服务器 {self.host}...")
            
            # 连接屏幕传输服务器
            self.screen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.screen_socket.connect((self.host, self.screen_port))
            print(f"屏幕传输连接成功: {self.host}:{self.screen_port}")
            
            # 初始化控制命令连接
            self.control_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            print(f"控制命令连接初始化: {self.host}:{self.control_port}")
            
            self.running = True
            return True
            
        except Exception as e:
            print(f"连接失败: {e}")
            return False
            
    def setup_gui(self):
        """设置GUI界面"""
        if not GUI_AVAILABLE:
            return False
            
        try:
            self.root = tk.Tk()
            self.root.title(f"远程桌面客户端 - 连接到: {self.host}")
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
            
            # 窗口大小
            width, height = 1024, 576
            self.root.geometry(f"{width}x{height+100}")
            
            # 主框架
            main_frame = ttk.Frame(self.root)
            main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # 视频显示区域
            self.video_label = tk.Label(main_frame, bg="black")
            self.video_label.pack(fill=tk.BOTH, expand=True)
            
            # 绑定鼠标事件
            self.video_label.bind('<Motion>', self.on_mouse_move)
            self.video_label.bind('<Button-1>', self.on_mouse_click)
            self.video_label.bind('<Double-Button-1>', self.on_mouse_double_click)
            self.video_label.bind('<Button-3>', lambda e: self.on_mouse_click(e, 'right'))
            
            # 控制面板
            control_frame = ttk.Frame(self.root)
            control_frame.pack(fill=tk.X, padx=10, pady=5)
            
            # 鼠标控制开关
            self.control_var = tk.BooleanVar(value=True)
            control_check = ttk.Checkbutton(
                control_frame, 
                text="鼠标控制", 
                variable=self.control_var,
                command=self.toggle_control
            )
            control_check.pack(side=tk.LEFT, padx=5)
            
            # 状态栏
            status_frame = ttk.Frame(self.root)
            status_frame.pack(fill=tk.X, padx=10, pady=5)
            
            self.status_label = ttk.Label(status_frame, text="未连接")
            self.status_label.pack(side=tk.LEFT)
            
            self.fps_label = ttk.Label(status_frame, text="FPS: 0")
            self.fps_label.pack(side=tk.RIGHT)
            
            return True
            
        except Exception as e:
            print(f"GUI初始化失败: {e}")
            return False
            
    def update_status(self, status):
        """更新状态显示"""
        if self.status_label:
            self.status_label.config(text=status)
        else:
            print(f"状态: {status}")
            
    def update_fps(self):
        """更新FPS显示"""
        self.frame_count += 1
        current_time = time.time()
        
        if current_time - self.last_time >= 1.0:
            self.fps = self.frame_count
            self.frame_count = 0
            self.last_time = current_time
            
            if self.fps_label:
                self.fps_label.config(text=f"FPS: {self.fps}")
            else:
                print(f"FPS: {self.fps}")
                
    def toggle_control(self):
        """切换鼠标控制开关"""
        if hasattr(self, 'control_var'):
            self.control_enabled = self.control_var.get()
        print(f"鼠标控制: {'开启' if self.control_enabled else '关闭'}")
        
    def send_command(self, command):
        """发送控制命令"""
        if not self.control_enabled or not self.control_socket:
            return
            
        try:
            data = json.dumps(command).encode('utf-8')
            self.control_socket.sendto(data, (self.host, self.control_port))
        except Exception as e:
            print(f"发送控制命令错误: {e}")
            
    def on_mouse_move(self, event):
        """处理鼠标移动事件"""
        self.mouse_pos = (event.x, event.y)
        command = {
            'type': 'move',
            'x': event.x,
            'y': event.y
        }
        self.send_command(command)
        
    def on_mouse_click(self, event, button='left'):
        """处理鼠标点击事件"""
        command = {
            'type': 'click',
            'x': event.x,
            'y': event.y,
            'button': button
        }
        self.send_command(command)
        print(f"鼠标{button}键点击: ({event.x}, {event.y})")
        
    def on_mouse_double_click(self, event):
        """处理鼠标双击事件"""
        command = {
            'type': 'double_click',
            'x': event.x,
            'y': event.y
        }
        self.send_command(command)
        print(f"鼠标双击: ({event.x}, {event.y})")
        
    def receive_screen(self):
        """接收屏幕图像"""
        data = b""
        payload_size = struct.calcsize("!L")
        
        while self.running:
            try:
                # 接收图像大小
                while len(data) < payload_size:
                    packet = self.screen_socket.recv(4096)
                    if not packet:
                        break
                    data += packet
                    
                if len(data) < payload_size:
                    break
                    
                packed_msg_size = data[:payload_size]
                data = data[payload_size:]
                msg_size = struct.unpack("!L", packed_msg_size)[0]
                
                # 接收图像数据
                while len(data) < msg_size:
                    packet = self.screen_socket.recv(4096)
                    if not packet:
                        break
                    data += packet
                    
                if len(data) < msg_size:
                    break
                    
                frame_data = data[:msg_size]
                data = data[msg_size:]
                
                # 解码图像
                frame = cv2.imdecode(np.frombuffer(frame_data, dtype=np.uint8), cv2.IMREAD_COLOR)
                
                # 更新显示
                if frame is not None:
                    self.update_display(frame)
                    self.update_fps()
                    
            except Exception as e:
                print(f"接收屏幕错误: {e}")
                self.update_status(f"接收屏幕错误: {e}")
                break
                
        self.update_status("连接断开")
        
    def update_display(self, frame):
        """更新显示的图像"""
        if GUI_AVAILABLE and self.video_label:
            try:
                # 转换颜色空间
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # 转换为PIL图像
                image = Image.fromarray(frame)
                photo = ImageTk.PhotoImage(image=image)
                
                # 更新标签
                self.video_label.config(image=photo)
                self.video_label.image = photo  # 保持引用
                
            except Exception as e:
                print(f"显示错误: {e}")
        else:
            # 简化模式：只显示统计信息
            pass
            
    def on_closing(self):
        """窗口关闭事件"""
        self.stop()
        if self.root:
            self.root.destroy()
            
    def stop(self):
        """停止客户端"""
        self.running = False
        
        if self.screen_socket:
            self.screen_socket.close()
            
        if self.control_socket:
            self.control_socket.close()
            
        print("客户端已停止")
        
    def run(self):
        """运行客户端"""
        if not self.connect():
            return
            
        # 尝试设置GUI
        gui_success = self.setup_gui()
        
        if gui_success:
            print("使用GUI模式")
            self.update_status(f"已连接到 {self.host}")
            
            # 启动屏幕接收线程
            screen_thread = threading.Thread(target=self.receive_screen)
            screen_thread.daemon = True
            screen_thread.start()
            
            # 运行GUI主循环
            try:
                self.root.mainloop()
            except KeyboardInterrupt:
                self.stop()
        else:
            print("使用简化模式")
            try:
                self.receive_screen()
            except KeyboardInterrupt:
                print("\n用户中断连接")
            finally:
                self.stop()

def main():
    parser = argparse.ArgumentParser(description='远程桌面客户端')
    parser.add_argument('--host', default='192.168.1.4', help='服务器IP地址')
    parser.add_argument('--screen-port', type=int, default=8485, help='屏幕传输端口')
    parser.add_argument('--control-port', type=int, default=8486, help='控制命令端口')
    parser.add_argument('--audio-port', type=int, default=8487, help='音频传输端口')
    args = parser.parse_args()
    
    client = RemoteDesktopClient(
        host=args.host,
        screen_port=args.screen_port,
        control_port=args.control_port,
        audio_port=args.audio_port
    )
    client.run()

if __name__ == "__main__":
    main() 