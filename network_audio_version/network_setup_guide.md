# 网络远程连接设置指南

## 🌐 真实网络环境设置

### 1. 确定服务端IP地址

在服务端机器上运行：
```bash
# 查看所有网络接口
ifconfig

# 或者只查看主要IP
ifconfig | grep "inet " | grep -v 127.0.0.1
```

### 2. 网络连通性测试

在客户端机器上测试：
```bash
# 测试网络连通性
ping [服务端IP地址]

# 测试端口连通性
telnet [服务端IP地址] 8485
```

### 3. 防火墙设置

#### macOS 服务端：
```bash
# 检查防火墙状态
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate

# 临时关闭防火墙（测试用）
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setglobalstate off

# 或者添加端口规则
sudo pfctl -f /etc/pf.conf
```

#### Windows 服务端：
1. 打开 Windows Defender 防火墙
2. 点击"高级设置"
3. 新建入站规则，允许端口 8485, 8486, 8487

### 4. 路由器设置（如果需要）

如果服务端在路由器后面，可能需要：
1. 端口转发设置
2. DMZ设置
3. UPnP启用

### 5. 常见网络问题

| 错误信息 | 可能原因 | 解决方案 |
|---------|---------|---------|
| No route to host | IP不存在/网络不通 | 检查IP地址和网络连接 |
| Connection refused | 服务未启动/端口被阻止 | 检查服务状态和防火墙 |
| Connection timeout | 网络延迟/防火墙阻止 | 检查网络质量和防火墙 |

### 6. 推荐的测试步骤

1. **同一台机器测试**：使用 127.0.0.1
2. **同一局域网测试**：使用局域网IP
3. **跨网络测试**：配置端口转发和防火墙

### 7. 安全注意事项

⚠️ **重要**：此程序未加密，仅适用于：
- 学习和测试环境
- 可信的内部网络
- 不包含敏感信息的场景

生产环境请考虑：
- 添加身份验证
- 使用SSL/TLS加密
- 限制访问IP范围 