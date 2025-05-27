#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
远程桌面程序
整合屏幕共享、音频传输和控制功能
支持服务端和客户端模式
"""

import socket
import cv2
import numpy as np
import pyaudio
import pyautogui
import threading
import struct
import json
import time
import argparse
import sys

class RemoteDesktop:
    def __init__(self, mode='server', host='0.0.0.0', screen_port=8485, control_port=8486, audio_port=8487):
        self.mode = mode  # 'server' 或 'client'
        self.host = host
        self.screen_port = screen_port
        self.control_port = control_port
        self.audio_port = audio_port
        
        self.running = False
        self.screen_socket = None
        self.control_socket = None
        self.audio_socket = None
        self.clients = []
        
        # GUI相关（仅客户端模式）
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
        self.last_mouse_pos = (0, 0)  # 上次鼠标位置
        self.last_move_time = 0  # 上次移动命令发送时间
        self.move_threshold = 3  # 鼠标移动阈值（像素）
        self.move_interval = 0.05  # 移动命令发送间隔（秒）
        self.is_dragging = False  # 是否正在拖拽
        
        # 音频相关
        self.chunk_size = 1024
        self.audio_format = pyaudio.paInt16
        self.channels = 1
        self.rate = 44100
        self.audio = pyaudio.PyAudio()
        self.input_stream = None
        self.output_stream = None
        self.muted = False
        
        # 服务端特有
        if self.mode == 'server':
            self.screen_size = pyautogui.size()
            print(f"屏幕尺寸: {self.screen_size[0]}x{self.screen_size[1]}")
            pyautogui.FAILSAFE = False
            
    def start(self):
        """启动程序"""
        if self.mode == 'server':
            self.start_server()
        else:
            self.start_client()
            
    def start_server(self):
        """启动服务端"""
        try:
            # 初始化屏幕传输服务器 (TCP)
            self.screen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.screen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.screen_socket.bind((self.host, self.screen_port))
            self.screen_socket.listen(5)
            
            # 初始化控制命令服务器 (UDP)
            self.control_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.control_socket.bind((self.host, self.control_port))
            
            # 初始化音频服务器 (TCP)
            self.audio_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.audio_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.audio_socket.bind((self.host, self.audio_port))
            self.audio_socket.listen(5)
            
            self.running = True
            
            print(f"屏幕传输服务启动，监听 {self.host}:{self.screen_port}")
            print(f"控制命令服务启动，监听 {self.host}:{self.control_port}")
            print(f"音频传输服务启动，监听 {self.host}:{self.audio_port}")
            
            # 初始化音频流
            self.setup_audio_streams()
            
            # 启动各个线程
            screen_thread = threading.Thread(target=self.accept_screen_clients)
            control_thread = threading.Thread(target=self.handle_control_commands)
            audio_thread = threading.Thread(target=self.accept_audio_clients)
            
            screen_thread.daemon = True
            control_thread.daemon = True
            audio_thread.daemon = True
            
            screen_thread.start()
            control_thread.start()
            audio_thread.start()
            
            # 保持运行
            try:
                while self.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                self.stop()
                
        except Exception as e:
            print(f"启动服务器错误: {e}")
            self.stop()
            
    def start_client(self):
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
        
    def setup_gui(self):
        """设置GUI界面（仅客户端模式）"""
        import tkinter as tk
        from tkinter import ttk
        from PIL import Image, ImageTk
        
        # 将tkinter模块保存为实例变量，以便其他方法使用
        self.tk = tk
        self.ttk = ttk
        self.ImageTk = ImageTk
        
        self.root = tk.Tk()
        self.root.title(f"远程桌面客户端 - 连接到: {self.host}")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 窗口大小
        width, height = 1024, 576
        self.root.geometry(f"{width}x{height+100}")
        
        # 主框架
        main_frame = self.ttk.Frame(self.root)
        main_frame.pack(fill=self.tk.BOTH, expand=True, padx=10, pady=10)
        
        # 视频显示区域
        self.video_label = self.tk.Label(main_frame, bg="black")
        self.video_label.pack(fill=self.tk.BOTH, expand=True)
        
        # 绑定鼠标事件
        # 只在按下鼠标时才跟踪移动，避免无意义的移动命令
        self.video_label.bind('<Button-1>', self.on_mouse_press)
        self.video_label.bind('<ButtonRelease-1>', self.on_mouse_release)
        self.video_label.bind('<Double-Button-1>', self.on_mouse_double_click)
        self.video_label.bind('<Button-3>', lambda e: self.on_mouse_click(e, 'right'))
        self.video_label.bind('<B1-Motion>', self.on_mouse_drag)
        # 只在需要时处理移动事件
        self.video_label.bind('<Enter>', self.on_mouse_enter)
        self.video_label.bind('<Leave>', self.on_mouse_leave)
        
        # 控制面板
        control_frame = self.ttk.Frame(self.root)
        control_frame.pack(fill=self.tk.X, padx=10, pady=5)
        
        # 鼠标控制开关
        self.control_var = self.tk.BooleanVar(value=True)
        control_check = self.ttk.Checkbutton(
            control_frame, 
            text="鼠标控制", 
            variable=self.control_var,
            command=self.toggle_control
        )
        control_check.pack(side=self.tk.LEFT, padx=5)
        
        # 麦克风控制
        self.mute_var = self.tk.BooleanVar(value=False)
        self.mute_button = self.ttk.Checkbutton(
            control_frame,
            text="静音麦克风",
            variable=self.mute_var,
            command=self.toggle_mute
        )
        self.mute_button.pack(side=self.tk.LEFT, padx=5)
        
        # 状态栏
        status_frame = self.ttk.Frame(self.root)
        status_frame.pack(fill=self.tk.X, padx=10, pady=5)
        
        self.status_label = self.ttk.Label(status_frame, text="未连接")
        self.status_label.pack(side=self.tk.LEFT)
        
        self.fps_label = self.ttk.Label(status_frame, text="FPS: 0")
        self.fps_label.pack(side=self.tk.RIGHT)
        
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
            if self.mode == 'client':
                self.update_status(f"音频初始化失败: {e}")
                
    def stop(self):
        """停止程序"""
        self.running = False
        
        # 关闭网络连接
        if self.screen_socket:
            self.screen_socket.close()
            
        if self.control_socket:
            self.control_socket.close()
            
        if self.audio_socket:
            self.audio_socket.close()
            
        for client in self.clients:
            try:
                client.close()
            except:
                pass
                
        # 关闭音频流
        if self.input_stream:
            self.input_stream.stop_stream()
            self.input_stream.close()
            
        if self.output_stream:
            self.output_stream.stop_stream()
            self.output_stream.close()
            
        if self.audio:
            self.audio.terminate()
            
        print("程序已停止")
        
    def accept_screen_clients(self):
        """接受屏幕传输客户端连接（服务端模式）"""
        while self.running:
            try:
                client_socket, addr = self.screen_socket.accept()
                print(f"新的屏幕传输客户端连接: {addr}")
                
                client_thread = threading.Thread(
                    target=self.handle_screen_client,
                    args=(client_socket,)
                )
                client_thread.daemon = True
                client_thread.start()
                
                self.clients.append(client_socket)
                
            except Exception as e:
                print(f"接受屏幕客户端连接错误: {e}")
                if not self.running:
                    break
                    
    def accept_audio_clients(self):
        """接受音频客户端连接（服务端模式）"""
        while self.running:
            try:
                client_socket, addr = self.audio_socket.accept()
                print(f"新的音频客户端连接: {addr}")
                
                # 为每个客户端创建两个线程
                send_thread = threading.Thread(
                    target=self.send_audio_to_client,
                    args=(client_socket,)
                )
                receive_thread = threading.Thread(
                    target=self.receive_audio_from_client,
                    args=(client_socket,)
                )
                
                send_thread.daemon = True
                receive_thread.daemon = True
                
                send_thread.start()
                receive_thread.start()
                
                self.clients.append(client_socket)
                
            except Exception as e:
                print(f"接受音频客户端连接错误: {e}")
                if not self.running:
                    break
                    
    def handle_screen_client(self, client_socket):
        """处理屏幕传输客户端（服务端模式）"""
        try:
            frame_interval = 1.0 / 20  # 约20FPS
            last_frame_time = 0
            
            while self.running:
                current_time = time.time()
                
                # 控制帧率
                if current_time - last_frame_time < frame_interval:
                    time.sleep(0.001)
                    continue
                    
                # 捕获屏幕
                screen = pyautogui.screenshot()
                frame = np.array(screen)
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                
                # 缩放到较小尺寸
                frame = cv2.resize(frame, (1024, 576))
                
                # 压缩质量
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 50])
                data = buffer.tobytes()
                
                # 发送大小
                size = len(data)
                size_data = struct.pack("!L", size)
                client_socket.sendall(size_data)
                
                # 发送数据
                client_socket.sendall(data)
                
                last_frame_time = current_time
                
        except Exception as e:
            print(f"屏幕传输错误: {e}")
        finally:
            if client_socket in self.clients:
                self.clients.remove(client_socket)
            try:
                client_socket.close()
            except:
                pass
            print("屏幕传输客户端连接已关闭")
            
    def handle_control_commands(self):
        """处理控制命令（服务端模式）"""
        self.control_socket.settimeout(0.1)  # 减少超时时间，提高响应性
        buffer_size = 1024
        last_move_time = 0
        last_move_pos = (0, 0)
        move_smoothing = 0.02  # 移动平滑间隔
        
        print("开始监听鼠标控制命令...")
        
        while self.running:
            try:
                data, addr = self.control_socket.recvfrom(buffer_size)
                command = json.loads(data.decode('utf-8'))
                
                command_type = command.get('type')
                x = command.get('x', 0)
                y = command.get('y', 0)
                
                # 从客户端坐标转换到实际屏幕坐标
                screen_x = int(x * self.screen_size[0] / 1024)
                screen_y = int(y * self.screen_size[1] / 576)
                
                # 限制坐标范围
                screen_x = max(0, min(screen_x, self.screen_size[0] - 1))
                screen_y = max(0, min(screen_y, self.screen_size[1] - 1))
                
                current_time = time.time()
                
                # 执行鼠标操作
                try:
                    if command_type == 'move':
                        # 对移动命令进行平滑处理，避免过于频繁的移动
                        if (current_time - last_move_time >= move_smoothing or
                            abs(screen_x - last_move_pos[0]) > 10 or
                            abs(screen_y - last_move_pos[1]) > 10):
                            
                            pyautogui.moveTo(screen_x, screen_y, duration=0)
                            last_move_time = current_time
                            last_move_pos = (screen_x, screen_y)
                            
                    elif command_type == 'click':
                        button = command.get('button', 'left')
                        # 确保鼠标在正确位置后再点击
                        pyautogui.moveTo(screen_x, screen_y, duration=0)
                        time.sleep(0.01)  # 短暂延迟确保移动完成
                        pyautogui.click(screen_x, screen_y, button=button)
                        print(f"点击: ({screen_x}, {screen_y}) 按钮: {button}")
                        
                    elif command_type == 'double_click':
                        pyautogui.moveTo(screen_x, screen_y, duration=0)
                        time.sleep(0.01)
                        pyautogui.doubleClick(screen_x, screen_y)
                        print(f"双击: ({screen_x}, {screen_y})")
                        
                    elif command_type == 'drag':
                        end_x = command.get('end_x', x)
                        end_y = command.get('end_y', y)
                        screen_end_x = int(end_x * self.screen_size[0] / 1024)
                        screen_end_y = int(end_y * self.screen_size[1] / 576)
                        
                        # 限制坐标范围
                        screen_end_x = max(0, min(screen_end_x, self.screen_size[0] - 1))
                        screen_end_y = max(0, min(screen_end_y, self.screen_size[1] - 1))
                        
                        pyautogui.dragTo(screen_end_x, screen_end_y, duration=0.05)
                        print(f"拖拽: ({screen_x}, {screen_y}) -> ({screen_end_x}, {screen_end_y})")
                        
                except Exception as e:
                    print(f"执行控制命令错误: {e}")
                
            except socket.timeout:
                continue
            except Exception as e:
                print(f"处理控制命令错误: {e}")
                if not self.running:
                    break
                    
    def send_audio_to_client(self, client_socket):
        """发送麦克风音频到客户端（服务端模式）"""
        try:
            while self.running:
                # 从麦克风读取数据
                data = self.input_stream.read(self.chunk_size, exception_on_overflow=False)
                
                # 发送数据大小
                size = len(data)
                size_data = struct.pack("!L", size)
                client_socket.sendall(size_data)
                
                # 发送音频数据
                client_socket.sendall(data)
                
        except Exception as e:
            print(f"发送音频错误: {e}")
        finally:
            if client_socket in self.clients:
                self.clients.remove(client_socket)
            try:
                client_socket.close()
            except:
                pass
            
    def receive_audio_from_client(self, client_socket):
        """从客户端接收音频并播放（服务端模式）"""
        data = b""
        payload_size = struct.calcsize("!L")
        
        try:
            while self.running:
                # 接收数据大小
                while len(data) < payload_size:
                    packet = client_socket.recv(4096)
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
                    packet = client_socket.recv(4096)
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
            
    def update_status(self, status):
        """更新状态显示（客户端模式）"""
        if self.status_label:
            self.status_label.config(text=status)
            
    def update_fps(self):
        """更新FPS显示（客户端模式）"""
        self.frame_count += 1
        current_time = time.time()
        
        if current_time - self.last_time >= 1.0:
            self.fps = self.frame_count
            self.frame_count = 0
            self.last_time = current_time
            
            if self.fps_label:
                self.fps_label.config(text=f"FPS: {self.fps}")
                
    def toggle_control(self):
        """切换鼠标控制开关（客户端模式）"""
        self.control_enabled = self.control_var.get()
        
    def toggle_mute(self):
        """切换麦克风静音（客户端模式）"""
        self.muted = self.mute_var.get()
        status = "静音" if self.muted else "开启"
        print(f"麦克风: {status}")
        
    def send_command(self, command):
        """发送控制命令（客户端模式）"""
        if not self.control_enabled or not self.control_socket:
            return
            
        try:
            data = json.dumps(command).encode('utf-8')
            # 使用非阻塞发送，避免网络延迟影响界面响应
            self.control_socket.sendto(data, (self.host, self.control_port))
        except Exception as e:
            print(f"发送控制命令错误: {e}")
            # 如果发送失败，更新状态
            if hasattr(self, 'update_status'):
                self.update_status(f"控制命令发送失败: {e}")
            
    def on_mouse_move(self, event):
        """处理鼠标移动事件（客户端模式）"""
        current_time = time.time()
        current_pos = (event.x, event.y)
        
        # 计算移动距离
        dx = abs(current_pos[0] - self.last_mouse_pos[0])
        dy = abs(current_pos[1] - self.last_mouse_pos[1])
        distance = (dx * dx + dy * dy) ** 0.5
        
        # 只有移动距离超过阈值且时间间隔足够时才发送命令
        if (distance >= self.move_threshold and 
            current_time - self.last_move_time >= self.move_interval):
            
            self.mouse_pos = current_pos
            self.last_mouse_pos = current_pos
            self.last_move_time = current_time
            
            command = {
                'type': 'move',
                'x': event.x,
                'y': event.y
            }
            self.send_command(command)
        
    def on_mouse_press(self, event):
        """处理鼠标按下事件（客户端模式）"""
        self.is_dragging = False
        self.mouse_pos = (event.x, event.y)
        self.last_mouse_pos = (event.x, event.y)
        
        # 先移动到点击位置，然后点击
        move_command = {
            'type': 'move',
            'x': event.x,
            'y': event.y
        }
        self.send_command(move_command)
        
        # 稍微延迟后发送点击命令
        self.root.after(10, lambda: self.send_click_command(event.x, event.y))
        
    def on_mouse_release(self, event):
        """处理鼠标释放事件（客户端模式）"""
        if not self.is_dragging:
            # 如果不是拖拽，这是一个普通点击的释放
            pass
        self.is_dragging = False
        
    def send_click_command(self, x, y):
        """发送点击命令"""
        command = {
            'type': 'click',
            'x': x,
            'y': y,
            'button': 'left'
        }
        self.send_command(command)
        
    def on_mouse_click(self, event, button='left'):
        """处理鼠标点击事件（客户端模式）"""
        # 先移动到点击位置
        move_command = {
            'type': 'move',
            'x': event.x,
            'y': event.y
        }
        self.send_command(move_command)
        
        # 稍微延迟后发送点击命令
        self.root.after(10, lambda: self.send_command({
            'type': 'click',
            'x': event.x,
            'y': event.y,
            'button': button
        }))
        
    def on_mouse_double_click(self, event):
        """处理鼠标双击事件（客户端模式）"""
        # 先移动到双击位置
        move_command = {
            'type': 'move',
            'x': event.x,
            'y': event.y
        }
        self.send_command(move_command)
        
        # 稍微延迟后发送双击命令
        self.root.after(10, lambda: self.send_command({
            'type': 'double_click',
            'x': event.x,
            'y': event.y
        }))
        
    def on_mouse_drag(self, event):
        """处理鼠标拖动事件（客户端模式）"""
        self.is_dragging = True
        current_time = time.time()
        
        # 限制拖拽命令的发送频率
        if current_time - self.last_move_time >= self.move_interval:
            command = {
                'type': 'drag',
                'x': self.mouse_pos[0],
                'y': self.mouse_pos[1],
                'end_x': event.x,
                'end_y': event.y
            }
            self.send_command(command)
            self.mouse_pos = (event.x, event.y)
            self.last_move_time = current_time
            
    def on_mouse_enter(self, event):
        """鼠标进入窗口事件"""
        # 绑定移动事件
        self.video_label.bind('<Motion>', self.on_mouse_move)
        
    def on_mouse_leave(self, event):
        """鼠标离开窗口事件"""
        # 解绑移动事件，避免不必要的命令
        self.video_label.unbind('<Motion>')
        
    def receive_screen(self):
        """接收屏幕图像（客户端模式）"""
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
        """更新显示的图像（客户端模式）"""
        try:
            from PIL import Image
            
            # 转换颜色空间
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # 转换为PIL图像
            image = Image.fromarray(frame)
            photo = self.ImageTk.PhotoImage(image=image)
            
            # 更新标签
            if self.video_label:
                self.video_label.config(image=photo)
                self.video_label.image = photo  # 保持引用
                
        except Exception as e:
            print(f"显示错误: {e}")
            
    def send_audio(self):
        """发送麦克风音频到服务器（客户端模式）"""
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
        """从服务器接收音频并播放（客户端模式）"""
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
        """窗口关闭事件（客户端模式）"""
        self.stop()
        if self.root:
            self.root.destroy()

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='远程桌面程序')
    parser.add_argument('--mode', choices=['server', 'client'], required=True, help='运行模式：server或client')
    parser.add_argument('--host', default='0.0.0.0', help='服务器IP地址（客户端模式）或监听地址（服务端模式）')
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
        import pyautogui
        
        # 只在客户端模式下检查GUI依赖
        if args.mode == 'client':
            from PIL import Image, ImageTk
            import tkinter
            
    except ImportError as e:
        print(f"缺少必要的依赖: {e}")
        if args.mode == 'client':
            print("请安装所需的依赖:")
            print("  pip install opencv-python numpy pyaudio pyautogui pillow")
            print("  brew install python-tk  # 用于GUI支持")
        else:
            print("请安装所需的依赖:")
            print("  pip install opencv-python numpy pyaudio pyautogui")
        sys.exit(1)
    
    if args.mode == 'server':
        print(f"服务端IP地址: {socket.gethostbyname(socket.gethostname())}")
        print("启动远程桌面服务端...")
    else:
        print(f"连接到服务器: {args.host}")
    
    remote = RemoteDesktop(
        mode=args.mode,
        host=args.host,
        screen_port=args.screen_port,
        control_port=args.control_port,
        audio_port=args.audio_port
    )
    
    remote.start() 