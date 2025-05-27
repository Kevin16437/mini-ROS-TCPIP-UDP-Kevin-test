#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的屏幕共享服务端
支持鼠标控制功能
"""

import socket
import cv2
import numpy as np
import pyautogui
import threading
import struct
import time
import json

class SimpleScreenServer:
    def __init__(self, host='0.0.0.0', tcp_port=8485, udp_port=8486):
        self.host = host
        self.tcp_port = tcp_port
        self.udp_port = udp_port
        self.running = False
        self.clients = []
        self.tcp_socket = None
        self.udp_socket = None
        self.screen_size = pyautogui.size()
        print(f"屏幕尺寸: {self.screen_size[0]}x{self.screen_size[1]}")
        
    def start(self):
        """启动服务器"""
        # 初始化TCP服务器（用于屏幕传输）
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.tcp_socket.bind((self.host, self.tcp_port))
        self.tcp_socket.listen(5)
        
        # 初始化UDP服务器（用于控制命令）
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.bind((self.host, self.udp_port))
        
        self.running = True
        
        print(f"TCP服务器已启动，监听 {self.host}:{self.tcp_port}")
        print(f"UDP服务器已启动，监听 {self.host}:{self.udp_port}")
        
        # 启动接受TCP客户端线程
        tcp_thread = threading.Thread(target=self.accept_clients)
        tcp_thread.daemon = True
        tcp_thread.start()
        
        # 启动UDP控制命令处理线程
        udp_thread = threading.Thread(target=self.handle_control_commands)
        udp_thread.daemon = True
        udp_thread.start()
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()
            
    def stop(self):
        """停止服务器"""
        self.running = False
        if self.tcp_socket:
            self.tcp_socket.close()
        
        if self.udp_socket:
            self.udp_socket.close()
        
        for client in self.clients:
            client.close()
            
        print("服务器已停止")
        
    def accept_clients(self):
        """接受TCP客户端连接"""
        while self.running:
            try:
                client_socket, addr = self.tcp_socket.accept()
                print(f"新TCP客户端连接: {addr}")
                
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket,)
                )
                client_thread.daemon = True
                client_thread.start()
                
                self.clients.append(client_socket)
            except Exception as e:
                print(f"接受客户端连接错误: {e}")
                break
                
    def handle_control_commands(self):
        """处理UDP控制命令"""
        self.udp_socket.settimeout(0.5)
        buffer_size = 1024
        
        print("开始监听鼠标控制命令...")
        
        while self.running:
            try:
                data, addr = self.udp_socket.recvfrom(buffer_size)
                command = json.loads(data.decode('utf-8'))
                
                command_type = command.get('type')
                x = command.get('x', 0)
                y = command.get('y', 0)
                
                # 从客户端坐标转换到实际屏幕坐标
                screen_x = int(x * self.screen_size[0] / 1024)
                screen_y = int(y * self.screen_size[1] / 576)
                
                print(f"收到控制命令: {command_type} 坐标: ({x}, {y}) -> 屏幕: ({screen_x}, {screen_y})")
                
                # 执行鼠标操作
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
                
            except socket.timeout:
                continue
            except Exception as e:
                print(f"处理控制命令错误: {e}")
                
    def handle_client(self, client_socket):
        """处理客户端连接"""
        try:
            while self.running:
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
                
                # 控制帧率
                time.sleep(0.05)  # 约20FPS
                
        except Exception as e:
            print(f"客户端处理错误: {e}")
        finally:
            if client_socket in self.clients:
                self.clients.remove(client_socket)
            client_socket.close()
            print("客户端连接已关闭")

if __name__ == "__main__":
    server = SimpleScreenServer()
    server.start() 