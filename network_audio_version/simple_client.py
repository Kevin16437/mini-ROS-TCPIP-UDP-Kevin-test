#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的远程桌面客户端
用于测试连接，不需要GUI
"""

import socket
import cv2
import numpy as np
import struct
import time
import argparse

class SimpleClient:
    def __init__(self, host='192.168.1.4', screen_port=8485):
        self.host = host
        self.screen_port = screen_port
        self.running = False
        self.screen_socket = None
        
    def connect(self):
        """连接到服务器"""
        try:
            print(f"正在连接到服务器 {self.host}:{self.screen_port}...")
            self.screen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.screen_socket.connect((self.host, self.screen_port))
            print("连接成功！")
            self.running = True
            return True
        except Exception as e:
            print(f"连接失败: {e}")
            return False
            
    def receive_frames(self):
        """接收并显示帧数"""
        data = b""
        payload_size = struct.calcsize("!L")
        frame_count = 0
        start_time = time.time()
        
        print("开始接收屏幕数据...")
        
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
                
                # 解码图像（仅用于验证）
                frame = cv2.imdecode(np.frombuffer(frame_data, dtype=np.uint8), cv2.IMREAD_COLOR)
                
                if frame is not None:
                    frame_count += 1
                    current_time = time.time()
                    elapsed = current_time - start_time
                    
                    if elapsed >= 1.0:  # 每秒显示一次统计
                        fps = frame_count / elapsed
                        print(f"接收帧数: {frame_count}, FPS: {fps:.2f}, 图像尺寸: {frame.shape}")
                        frame_count = 0
                        start_time = current_time
                        
            except KeyboardInterrupt:
                print("\n用户中断连接")
                break
            except Exception as e:
                print(f"接收数据错误: {e}")
                break
                
        print("连接断开")
        
    def stop(self):
        """停止客户端"""
        self.running = False
        if self.screen_socket:
            self.screen_socket.close()
            
    def run(self):
        """运行客户端"""
        if self.connect():
            try:
                self.receive_frames()
            finally:
                self.stop()

def main():
    parser = argparse.ArgumentParser(description='简化的远程桌面客户端')
    parser.add_argument('--host', default='192.168.1.4', help='服务器IP地址')
    parser.add_argument('--port', type=int, default=8485, help='服务器端口')
    args = parser.parse_args()
    
    client = SimpleClient(host=args.host, screen_port=args.port)
    client.run()

if __name__ == "__main__":
    main() 