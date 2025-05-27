#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的屏幕共享客户端
支持鼠标控制功能
"""

import socket
import cv2
import numpy as np
import threading
import struct
import time
import json
import tkinter as tk
from PIL import Image, ImageTk

class SimpleScreenClient:
    def __init__(self, host='localhost', tcp_port=8485, udp_port=8486, audio_port=8487):
        self.host = host
        self.tcp_port = tcp_port
        self.udp_port = udp_port
        self.audio_port = audio_port
        self.running = False
        self.tcp_socket = None
        self.udp_socket = None
        self.fps = 0
        self.frame_count = 0
        self.last_time = time.time()
        
        # GUI相关
        self.root = None
        self.video_label = None
        self.status_label = None
        self.control_enabled = True  # 默认启用鼠标控制
        
    def start(self):
        """启动客户端"""
        self.setup_gui()
        
        # 连接TCP服务器
        try:
            # TCP连接（接收屏幕图像）
            self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_socket.connect((self.host, self.tcp_port))
            
            # UDP连接（发送控制命令）
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            self.running = True
            self.update_status(f"已连接到 {self.host}:{self.tcp_port}")
            
            # 启动接收线程
            receive_thread = threading.Thread(target=self.receive_screen)
            receive_thread.daemon = True
            receive_thread.start()
            
        except Exception as e:
            self.update_status(f"连接失败: {e}")
        
        # 运行GUI主循环
        self.root.mainloop()
        
    def stop(self):
        """停止客户端"""
        self.running = False
        if self.tcp_socket:
            self.tcp_socket.close()
            
        if self.udp_socket:
            self.udp_socket.close()
        
    def setup_gui(self):
        """设置GUI界面"""
        self.root = tk.Tk()
        self.root.title("简单屏幕共享客户端 - 支持鼠标控制")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 窗口大小
        width, height = 1024, 576
        self.root.geometry(f"{width}x{height+70}")
        
        # 视频显示区域 - 注意：不使用width和height属性，让图像自然调整标签大小
        self.video_label = tk.Label(self.root, bg="black")
        self.video_label.pack(pady=5)
        
        # 绑定鼠标事件
        self.video_label.bind('<Motion>', self.on_mouse_move)
        self.video_label.bind('<Button-1>', self.on_mouse_click)
        self.video_label.bind('<Double-Button-1>', self.on_mouse_double_click)
        self.video_label.bind('<Button-3>', lambda e: self.on_mouse_click(e, 'right'))
        self.video_label.bind('<B1-Motion>', self.on_mouse_drag)
        
        # 控制面板
        control_frame = tk.Frame(self.root)
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 鼠标控制开关
        self.control_var = tk.BooleanVar(value=True)
        self.control_checkbox = tk.Checkbutton(
            control_frame, 
            text="启用鼠标控制", 
            variable=self.control_var,
            command=self.toggle_control
        )
        self.control_checkbox.pack(side=tk.LEFT)
        
        # 状态栏
        status_frame = tk.Frame(self.root)
        status_frame.pack(fill=tk.X, padx=10)
        
        self.status_label = tk.Label(status_frame, text="未连接")
        self.status_label.pack(side=tk.LEFT)
        
        self.fps_label = tk.Label(status_frame, text="FPS: 0")
        self.fps_label.pack(side=tk.RIGHT)
        
    def update_status(self, status):
        """更新状态显示"""
        if self.status_label:
            self.status_label.config(text=status)
            
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
        
    def toggle_control(self):
        """切换鼠标控制开关"""
        self.control_enabled = self.control_var.get()
        status = "启用" if self.control_enabled else "禁用"
        print(f"鼠标控制已{status}")
        
    def send_command(self, command):
        """发送控制命令"""
        if not self.control_enabled or not self.udp_socket:
            return
            
        try:
            data = json.dumps(command).encode('utf-8')
            self.udp_socket.sendto(data, (self.host, self.udp_port))
        except Exception as e:
            print(f"发送控制命令错误: {e}")
            
    def on_mouse_move(self, event):
        """处理鼠标移动事件"""
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
        
    def on_mouse_double_click(self, event):
        """处理鼠标双击事件"""
        command = {
            'type': 'double_click',
            'x': event.x,
            'y': event.y
        }
        self.send_command(command)
        
    def on_mouse_drag(self, event):
        """处理鼠标拖动事件"""
        command = {
            'type': 'drag',
            'x': event.x,
            'y': event.y,
            'end_x': event.x,
            'end_y': event.y
        }
        self.send_command(command)
        
    def receive_screen(self):
        """接收屏幕图像"""
        data = b""
        payload_size = struct.calcsize("!L")
        
        while self.running:
            try:
                # 接收图像大小
                while len(data) < payload_size:
                    packet = self.tcp_socket.recv(4096)
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
                    packet = self.tcp_socket.recv(4096)
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
                print(f"接收错误: {e}")
                self.update_status(f"接收错误: {e}")
                break
                
        self.update_status("连接断开")
        
    def update_display(self, frame):
        """更新显示的图像"""
        try:
            # 转换颜色空间
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # 转换为PIL图像
            image = Image.fromarray(frame)
            photo = ImageTk.PhotoImage(image=image)
            
            # 更新标签
            if self.video_label:
                self.video_label.config(image=photo)
                self.video_label.image = photo  # 保持引用
                
        except Exception as e:
            print(f"显示错误: {e}")
            
    def on_closing(self):
        """窗口关闭事件"""
        self.stop()
        if self.root:
            self.root.destroy()

if __name__ == "__main__":
    client = SimpleScreenClient()
    client.start() 