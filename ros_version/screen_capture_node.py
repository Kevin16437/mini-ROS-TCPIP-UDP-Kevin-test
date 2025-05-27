#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
屏幕捕获节点 - 简化版
只负责捕获屏幕内容并通过TCP发送
"""

import cv2
import numpy as np
import pyautogui
import socket
import threading
import struct
import time
import logging

class ScreenCaptureNode:
    """屏幕捕获节点"""
    def __init__(self, tcp_port=8485):
        self.tcp_port = tcp_port
        self.tcp_socket = None
        self.is_running = False
        self.fps = 30  # 目标帧率
        self.jpeg_quality = 50  # JPEG压缩质量
        
    def setup_socket(self):
        """初始化TCP套接字"""
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.tcp_socket.bind(('0.0.0.0', self.tcp_port))
        self.tcp_socket.listen(5)
        self.tcp_socket.settimeout(1.0)
        logging.info(f"TCP服务器监听端口: {self.tcp_port}")
        
    def capture_screen(self):
        """捕获屏幕内容"""
        try:
            # 截取屏幕
            screenshot = pyautogui.screenshot()
            # 转换为numpy数组
            frame = np.array(screenshot)
            # 转换颜色空间从RGB到BGR
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            
            # 缩放图像以减少传输数据量
            original_height, original_width = frame.shape[:2]
            target_width = 1280  # 目标宽度
            target_height = int(original_height * target_width / original_width)
            
            # 确保高度不超过720
            if target_height > 720:
                target_height = 720
                target_width = int(original_width * target_height / original_height)
            
            frame = cv2.resize(frame, (target_width, target_height))
            return frame
        except Exception as e:
            logging.error(f"屏幕捕获失败: {e}")
            return None
            
    def handle_client(self, client_socket, address):
        """处理客户端连接"""
        logging.info(f"新的客户端连接: {address}")
        
        try:
            frame_interval = 1.0 / self.fps
            last_frame_time = 0
            
            while self.is_running:
                current_time = time.time()
                
                # 控制帧率
                if current_time - last_frame_time < frame_interval:
                    time.sleep(0.001)
                    continue
                    
                # 捕获屏幕
                frame = self.capture_screen()
                if frame is None:
                    continue
                    
                # 压缩图像
                encode_param = [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality]
                success, buffer = cv2.imencode('.jpg', frame, encode_param)
                
                if not success:
                    continue
                
                # 发送图像大小（4字节）
                size = len(buffer)
                size_data = struct.pack(">L", size)
                client_socket.sendall(size_data)
                
                # 发送图像数据
                client_socket.sendall(buffer.tobytes())
                
                last_frame_time = current_time
                
        except Exception as e:
            logging.error(f"客户端处理错误: {e}")
        finally:
            client_socket.close()
            logging.info(f"客户端断开连接: {address}")
            
    def start(self):
        """启动节点"""
        self.is_running = True
        self.setup_socket()
        
        # 主循环：接受TCP连接
        while self.is_running:
            try:
                client_socket, address = self.tcp_socket.accept()
                # 为每个客户端创建一个线程
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, address)
                )
                client_thread.daemon = True
                client_thread.start()
                
            except socket.timeout:
                continue
            except Exception as e:
                if self.is_running:
                    logging.error(f"接受连接错误: {e}")
                    
    def stop(self):
        """停止节点"""
        self.is_running = False
        if self.tcp_socket:
            self.tcp_socket.close()

def main():
    """主函数"""
    # 配置日志
    logging.basicConfig(level=logging.INFO)
    
    # 创建并启动节点
    node = ScreenCaptureNode()
    
    try:
        node.start()
    except KeyboardInterrupt:
        logging.info("正在关闭屏幕捕获节点...")
        node.stop()
        
if __name__ == '__main__':
    main() 