#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音频服务端
负责捕获和传输麦克风音频，同时接收和播放客户端的音频
"""

import socket
import threading
import time
import pyaudio
import wave
import struct

class AudioServer:
    def __init__(self, host='0.0.0.0', port=8487):
        self.host = host
        self.port = port
        self.running = False
        self.socket = None
        self.clients = []
        
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
        """启动音频服务器"""
        # 初始化TCP服务器
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.host, self.port))
        self.socket.listen(5)
        self.running = True
        
        print(f"音频服务器启动，监听 {self.host}:{self.port}")
        
        # 初始化音频输入和输出流
        self.setup_audio_streams()
        
        # 启动接受客户端线程
        accept_thread = threading.Thread(target=self.accept_clients)
        accept_thread.daemon = True
        accept_thread.start()
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
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
        """停止音频服务器"""
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
            
        for client in self.clients:
            client.close()
            
        print("音频服务器已停止")
        
    def accept_clients(self):
        """接受客户端连接"""
        while self.running:
            try:
                client_socket, addr = self.socket.accept()
                print(f"新的音频客户端连接: {addr}")
                
                # 为每个客户端创建两个线程
                # 一个用于发送音频，一个用于接收音频
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
                print(f"接受客户端连接错误: {e}")
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
            client_socket.close()
            
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

if __name__ == "__main__":
    server = AudioServer()
    server.start() 