#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音频客户端
负责捕获和传输麦克风音频，同时接收和播放服务端的音频
"""

import socket
import threading
import time
import pyaudio
import struct

class AudioClient:
    def __init__(self, host='localhost', port=8487):
        self.host = host
        self.port = port
        self.running = False
        self.socket = None
        
        # 音频参数
        self.chunk_size = 1024
        self.audio_format = pyaudio.paInt16
        self.channels = 1
        self.rate = 44100
        
        # PyAudio实例
        self.audio = pyaudio.PyAudio()
        self.input_stream = None
        self.output_stream = None
        
        # 静音控制
        self.muted = False
        
    def start(self):
        """启动音频客户端"""
        try:
            # 初始化音频流
            self.setup_audio_streams()
            
            # 连接到服务器
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.running = True
            
            print(f"已连接到音频服务器 {self.host}:{self.port}")
            
            # 启动发送和接收线程
            send_thread = threading.Thread(target=self.send_audio)
            receive_thread = threading.Thread(target=self.receive_audio)
            
            send_thread.daemon = True
            receive_thread.daemon = True
            
            send_thread.start()
            receive_thread.start()
            
            # 保持运行
            try:
                while self.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                self.stop()
                
        except Exception as e:
            print(f"启动音频客户端错误: {e}")
            self.stop()
            
    def setup_audio_streams(self):
        """设置音频流"""
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
        
    def stop(self):
        """停止音频客户端"""
        self.running = False
        
        # 关闭音频流
        if self.input_stream:
            self.input_stream.stop_stream()
            self.input_stream.close()
            
        if self.output_stream:
            self.output_stream.stop_stream()
            self.output_stream.close()
            
        self.audio.terminate()
        
        # 关闭网络连接
        if self.socket:
            self.socket.close()
            
        print("音频客户端已停止")
        
    def toggle_mute(self):
        """切换静音状态"""
        self.muted = not self.muted
        print(f"麦克风: {'静音' if self.muted else '开启'}")
        
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
                self.socket.sendall(size_data)
                
                # 发送音频数据
                self.socket.sendall(data)
                
        except Exception as e:
            print(f"发送音频错误: {e}")
            self.running = False
            
    def receive_audio(self):
        """从服务器接收音频并播放"""
        data = b""
        payload_size = struct.calcsize("!L")
        
        try:
            while self.running:
                # 接收数据大小
                while len(data) < payload_size:
                    packet = self.socket.recv(4096)
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
                    packet = self.socket.recv(4096)
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
            self.running = False

if __name__ == "__main__":
    client = AudioClient()
    client.start() 