#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网络远程桌面服务端
整合屏幕共享和音频功能
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

class RemoteDesktopServer:
    def __init__(self, host='0.0.0.0', screen_port=8485, control_port=8486, audio_port=8487):
        self.host = host
        self.screen_port = screen_port
        self.control_port = control_port
        self.audio_port = audio_port
        
        self.running = False
        self.screen_socket = None
        self.control_socket = None
        self.audio_socket = None
        
        self.clients = []
        self.screen_size = pyautogui.size()
        
        print(f"屏幕尺寸: {self.screen_size[0]}x{self.screen_size[1]}")
        
        # 禁用PyAutoGUI的安全功能
        pyautogui.FAILSAFE = False
        
        # 音频参数
        self.chunk_size = 1024
        self.audio_format = pyaudio.paInt16
        self.channels = 1
        self.rate = 44100
        
        # PyAudio实例
        self.audio = pyaudio.PyAudio()
        self.input_stream = None
        self.output_stream = None
        
    def start(self):
        """启动服务器"""
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
            
    def stop(self):
        """停止服务器"""
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
            
        print("服务器已停止")
        
    def accept_screen_clients(self):
        """接受屏幕传输客户端连接"""
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
        """接受音频客户端连接"""
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
        """处理屏幕传输客户端"""
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
        """处理控制命令"""
        self.control_socket.settimeout(0.5)
        buffer_size = 1024
        
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
                
                print(f"收到控制命令: {command_type} 坐标: ({x}, {y}) -> 屏幕: ({screen_x}, {screen_y})")
                
                # 执行鼠标操作
                try:
                    if command_type == 'move':
                        pyautogui.moveTo(screen_x, screen_y)
                    elif command_type == 'click':
                        button = command.get('button', 'left')
                        pyautogui.click(screen_x, screen_y, button=button)
                    elif command_type == 'double_click':
                        pyautogui.doubleClick(screen_x, screen_y)
                    elif command_type == 'drag':
                        end_x = command.get('end_x', x)
                        end_y = command.get('end_y', y)
                        screen_end_x = int(end_x * self.screen_size[0] / 1024)
                        screen_end_y = int(end_y * self.screen_size[1] / 576)
                        pyautogui.dragTo(screen_end_x, screen_end_y, duration=0.1)
                except Exception as e:
                    print(f"执行控制命令错误: {e}")
                
            except socket.timeout:
                continue
            except Exception as e:
                print(f"处理控制命令错误: {e}")
                if not self.running:
                    break
                    
    def send_audio_to_client(self, client_socket):
        """发送麦克风音频到客户端"""
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
        """从客户端接收音频并播放"""
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

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='远程桌面服务端')
    parser.add_argument('--host', default='0.0.0.0', help='监听地址')
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
    except ImportError as e:
        print(f"缺少必要的依赖: {e}")
        print("请安装所需的依赖:")
        print("  pip install opencv-python numpy pyaudio pyautogui")
        sys.exit(1)
    
    server = RemoteDesktopServer(
        host=args.host,
        screen_port=args.screen_port,
        control_port=args.control_port,
        audio_port=args.audio_port
    )
    
    print(f"服务端IP地址: {socket.gethostbyname(socket.gethostname())}")
    print("启动远程桌面服务端...")
    server.start() 