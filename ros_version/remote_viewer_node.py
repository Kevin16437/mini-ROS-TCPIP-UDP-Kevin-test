#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
远程查看器节点 - 简化版
只负责接收和显示屏幕内容
"""

import cv2
import numpy as np
import socket
import struct
import threading
import time
import logging
import tkinter as tk
from PIL import Image, ImageTk

class RemoteViewerNode:
    """远程查看器节点"""
    def __init__(self, server_ip='localhost', tcp_port=8485):
        self.server_ip = server_ip
        self.tcp_port = tcp_port
        self.tcp_socket = None
        self.is_running = False
        self.window = None
        self.canvas = None
        self.photo = None
        
    def setup_gui(self):
        """设置GUI界面"""
        self.window = tk.Tk()
        self.window.title("远程屏幕查看器")
        
        # 创建画布
        self.canvas = tk.Canvas(self.window, width=1280, height=720)
        self.canvas.pack()
        
        # 设置窗口关闭事件处理
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def setup_socket(self):
        """初始化TCP套接字"""
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_socket.connect((self.server_ip, self.tcp_port))
        logging.info(f"已连接到服务器: {self.server_ip}:{self.tcp_port}")
        
    def receive_frame(self):
        """接收并显示视频帧"""
        try:
            while self.is_running:
                # 接收图像大小（4字节）
                size_data = self.tcp_socket.recv(4)
                if not size_data:
                    break
                    
                size = struct.unpack(">L", size_data)[0]
                
                # 接收图像数据
                data = b""
                while len(data) < size:
                    packet = self.tcp_socket.recv(size - len(data))
                    if not packet:
                        break
                    data += packet
                
                if len(data) == size:
                    # 解码图像
                    frame = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
                    
                    # 转换为PIL图像
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    pil_image = Image.fromarray(frame_rgb)
                    
                    # 转换为Tkinter可用的图像
                    self.photo = ImageTk.PhotoImage(image=pil_image)
                    
                    # 更新画布
                    self.canvas.create_image(0, 0, image=self.photo, anchor=tk.NW)
                    self.window.update()
                    
        except Exception as e:
            logging.error(f"接收帧错误: {e}")
        finally:
            self.stop()
            
    def start(self):
        """启动节点"""
        self.is_running = True
        self.setup_gui()
        self.setup_socket()
        
        # 启动接收线程
        receive_thread = threading.Thread(target=self.receive_frame)
        receive_thread.daemon = True
        receive_thread.start()
        
        # 启动GUI主循环
        self.window.mainloop()
        
    def stop(self):
        """停止节点"""
        self.is_running = False
        if self.tcp_socket:
            self.tcp_socket.close()
        if self.window:
            self.window.destroy()
            
    def on_closing(self):
        """窗口关闭事件处理"""
        self.stop()

def main():
    """主函数"""
    # 配置日志
    logging.basicConfig(level=logging.INFO)
    
    # 创建并启动节点
    node = RemoteViewerNode()
    node.start()
        
if __name__ == '__main__':
    main() 