#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网络远程桌面客户端
整合屏幕共享和音频功能
"""

import socket
import cv2
import numpy as np
import pyaudio
import threading
import struct
import json
import time
import argparse
import sys
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk

class RemoteDesktopClient:
    def __init__(self, host='localhost', screen_port=8485, control_port=8486, audio_port=8487):
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
        self.mute_button = None
        
        # 性能统计
        self.fps = 0
        self.frame_count = 0
        self.last_time = time.time()
        
        # 控制相关
        self.control_enabled = True
        self.mouse_pos = (0, 0)
        
        # 音频相关
        self.chunk_size = 1024
        self.audio_format = pyaudio.paInt16
        self.channels = 1
        self.rate = 44100
        self.audio = pyaudio.PyAudio()
        self.input_stream = None
        self.output_stream = None
        self.muted = False
        
    def start(self):
        """启动客户端"""
        # 设置GUI
        self.setup_gui()
        
        try:
            # 连接屏幕传输服务器 (TCP)
            self.screen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.screen_socket.connect((self.host, self.screen_port))
            
            # 初始化控制命令连接 (UDP)
            self.control_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            # 连接音频服务器 (TCP)
            self.audio_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.audio_socket.connect((self.host, self.audio_port))
            
            self.running = True
            self.update_status(f"已连接到 {self.host}")
            
            # 初始化音频流
            self.setup_audio_streams()
            
            # 启动线程
            screen_thread = threading.Thread(target=self.receive_screen)
            audio_send_thread = threading.Thread(target=self.send_audio)
            audio_receive_thread = threading.Thread(target=self.receive_audio)
            
            screen_thread.daemon = True
            audio_send_thread.daemon = True
            audio_receive_thread.daemon = True
            
            screen_thread.start()
            audio_send_thread.start()
            audio_receive_thread.start()
            
        except Exception as e:
            self.update_status(f"连接失败: {e}")
            
        # 运行GUI主循环
        self.root.mainloop()
        
    def stop(self):
        """停止客户端"""
        self.running = False
        
        # 关闭网络连接
        if self.screen_socket:
            self.screen_socket.close()
            
        if self.control_socket:
            self.control_socket.close()
            
        if self.audio_socket:
            self.audio_socket.close()
            
        # 关闭音频流
        if self.input_stream:
            self.input_stream.stop_stream()
            self.input_stream.close()
            
        if self.output_stream:
            self.output_stream.stop_stream()
            self.output_stream.close()
            
        if self.audio:
            self.audio.terminate()
            
    def setup_gui(self):
        """设置GUI界面"""
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
        self.video_label.bind('<B1-Motion>', self.on_mouse_drag)
        
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
        
        # 麦克风控制
        self.mute_var = tk.BooleanVar(value=False)
        self.mute_button = ttk.Checkbutton(
            control_frame,
            text="静音麦克风",
            variable=self.mute_var,
            command=self.toggle_mute
        )
        self.mute_button.pack(side=tk.LEFT, padx=5)
        
        # 状态栏
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.status_label = ttk.Label(status_frame, text="未连接")
        self.status_label.pack(side=tk.LEFT)
        
        self.fps_label = ttk.Label(status_frame, text="FPS: 0")
        self.fps_label.pack(side=tk.RIGHT)
        
        # 设置样式
        style = ttk.Style()
        style.configure('TButton', font=('Arial', 10))
        style.configure('TCheckbutton', font=('Arial', 10))
        style.configure('TLabel', font=('Arial', 10))
        
    def setup_audio_streams(self):
        """设置音频流"""
        try:
            # 麦克风输入流
            self.input_stream = self.audio.open(
                format=self.audio_format,
                channels=self.channels,
                rate=self.rate,
                input=True,
                frames_per_buffer=self.chunk_size
            )
            
            # 扬声器输出流
            self.output_stream = self.audio.open(
                format=self.audio_format,
                channels=self.channels,
                rate=self.rate,
                output=True
            )
            
            print("音频流已初始化")
        except Exception as e:
            print(f"初始化音频流错误: {e}")
            self.update_status(f"音频初始化失败: {e}")
            
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
        
    def toggle_mute(self):
        """切换麦克风静音"""
        self.muted = self.mute_var.get()
        status = "静音" if self.muted else "开启"
        print(f"麦克风: {status}")
        
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
            'x': self.mouse_pos[0],
            'y': self.mouse_pos[1],
            'end_x': event.x,
            'end_y': event.y
        }
        self.send_command(command)
        self.mouse_pos = (event.x, event.y)
        
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
            
    def send_audio(self):
        """发送麦克风音频到服务器"""
        try:
            while self.running:
                # 从麦克风读取数据
                data = self.input_stream.read(self.chunk_size, exception_on_overflow=False)
                
                # 如果静音，发送静音数据
                if self.muted:
                    data = b'\x00' * len(data)
                
                # 发送数据大小
                size = len(data)
                size_data = struct.pack("!L", size)
                self.audio_socket.sendall(size_data)
                
                # 发送音频数据
                self.audio_socket.sendall(data)
                
        except Exception as e:
            print(f"发送音频错误: {e}")
            
    def receive_audio(self):
        """从服务器接收音频并播放"""
        data = b""
        payload_size = struct.calcsize("!L")
        
        try:
            while self.running:
                # 接收数据大小
                while len(data) < payload_size:
                    packet = self.audio_socket.recv(4096)
                    if not packet:
                        break
                    data += packet
                    
                if len(data) < payload_size:
                    break
                    
                packed_msg_size = data[:payload_size]
                data = data[payload_size:]
                msg_size = struct.unpack("!L", packed_msg_size)[0]
                
                # 接收音频数据
                while len(data) < msg_size:
                    packet = self.audio_socket.recv(4096)
                    if not packet:
                        break
                    data += packet
                    
                if len(data) < msg_size:
                    break
                    
                audio_data = data[:msg_size]
                data = data[msg_size:]
                
                # 播放音频
                self.output_stream.write(audio_data)
                
        except Exception as e:
            print(f"接收音频错误: {e}")
            
    def on_closing(self):
        """窗口关闭事件"""
        self.stop()
        if self.root:
            self.root.destroy()

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='远程桌面客户端')
    parser.add_argument('--host', default='localhost', help='服务器IP地址')
    parser.add_argument('--screen-port', type=int, default=8485, help='屏幕传输端口')
    parser.add_argument('--control-port', type=int, default=8486, help='控制命令端口')
    parser.add_argument('--audio-port', type=int, default=8487, help='音频传输端口')
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_arguments()
    
    # 安装依赖检查
    try:
        import cv2
        import numpy
        import pyaudio
        from PIL import Image, ImageTk
    except ImportError as e:
        print(f"缺少必要的依赖: {e}")
        print("请安装所需的依赖:")
        print("  pip install opencv-python numpy pyaudio pillow")
        sys.exit(1)
    
    print(f"连接到服务器: {args.host}")
    
    client = RemoteDesktopClient(
        host=args.host,
        screen_port=args.screen_port,
        control_port=args.control_port,
        audio_port=args.audio_port
    )
    
    client.start() 