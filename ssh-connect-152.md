---
name: ssh-connect-152
description: 从 30 服务器(Windows) SSH 连接到 152 服务器(Ubuntu)的可靠方法和最佳实践。解决连接超时、断线、密钥管理等常见问题。
---

# SSH 连接 152 服务器

## 服务器信息

| 服务器 | IP | 用户 | 密钥位置 |
|--------|-----|------|----------|
| 30 (本机) | 122.51.32.30 | Administrator | - |
| 152 (远程) | 124.223.64.152 | ubuntu | `C:\Users\Administrator\Desktop\cherry claw\coze.pem` |

## 基础连接

```bash
ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
  -i "C:/Users/Administrator/Desktop/cherry claw/coze.pem" \
  ubuntu@124.223.64.152
```

## 最佳实践参数

### 稳定连接（防止超时断开）

```bash
ssh -o StrictHostKeyChecking=no \
  -o ConnectTimeout=10 \
  -o ServerAliveInterval=15 \
  -o ServerAliveCountMax=3 \
  -i "C:/Users/Administrator/Desktop/cherry claw/coze.pem" \
  ubuntu@124.223.64.152
```

参数说明：
- `ServerAliveInterval=15`：每 15 秒发一次心跳包
- `ServerAliveCountMax=3`：连续 3 次心跳无响应才断开
- `ConnectTimeout=10`：连接超时 10 秒

### 后台隧道（端口转发）

```bash
# 本地转发：把 152 的 6080 端口映射到本地的 6080
ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=15 -f -N \
  -L 6080:localhost:6080 \
  -i "C:/Users/Administrator/Desktop/cherry claw/coze.pem" \
  ubuntu@124.223.64.152

# SOCKS5 代理：152→30→NAS 隧道
ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=15 -f -N \
  -D 1081 \
  -i "C:/Users/Administrator/Desktop/cherry claw/coze.pem" \
  ubuntu@124.223.64.152
```

### 执行单条命令（不进入交互 shell）

```bash
ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o ServerAliveInterval=10 \
  -i "C:/Users/Administrator/Desktop/cherry claw/coze.pem" \
  ubuntu@124.223.64.152 "curl -s http://127.0.0.1:29538/ | head -c 30"
```

## 文件传输

### 上传到 152
```bash
scp -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
  -i "C:/Users/Administrator/Desktop/cherry claw/coze.pem" \
  "C:/path/to/local/file" ubuntu@124.223.64.152:/tmp/
```

### 从 152 下载
```bash
scp -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
  -i "C:/Users/Administrator/Desktop/cherry claw/coze.pem" \
  ubuntu@124.223.64.152:/tmp/remote_file "C:/Users/Administrator/Desktop/"
```

## 常见问题

### 连接超时 (exit code 255)
- 检查网络：`ping 124.223.64.152`
- 检查密钥权限：确认 `.pem` 文件存在且未被修改
- 服务器负载过高可能拒绝新连接

### 隧道断开
- 加 `ServerAliveInterval=15` 参数
- 使用 `-f` 后台运行避免终端关闭影响
- 用脚本定期检查隧道状态并自动重连

### 密钥格式错误
- 确认使用绝对路径
- Windows 路径含空格时用双引号包裹
- 如遇 `bad permissions`，在 Linux 侧执行 `chmod 600 /path/to/key`

## 连接测试

```bash
# 快速测试连接是否正常
ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 \
  -i "C:/Users/Administrator/Desktop/cherry claw/coze.pem" \
  ubuntu@124.223.64.152 "echo CONNECTED && uname -a"
```
