---
name: server-connect
description: 连接到已知服务器的标准方法。当你需要SSH连接到30服务器(Windows)、152服务器(Ubuntu)、NAS(群晖)或通过隧道访问家庭网络时，使用此技能。
---

# 服务器连接技能

## 速查表

| 服务器 | IP | 用户 | 认证 | 命令 |
|--------|-----|------|------|------|
| 30服务器(Windows) | 122.51.32.30 | Administrator | coze.pem | `ssh -o ConnectTimeout=5 -i ~/Downloads/coze.pem Administrator@122.51.32.30` |
| 152服务器(Ubuntu) | 124.223.64.152 | ubuntu | coze.pem | `ssh -o ConnectTimeout=5 -i ~/Downloads/coze.pem ubuntu@124.223.64.152` |
| NAS(群晖) | 192.168.0.21 | yang | 密码 | `sshpass -p 'Plsaemc_814@' ssh -o ConnectTimeout=5 yang@192.168.0.21` |

## 重要规则

### 1. 超时：永远 5 秒
所有 SSH 连接加 `-o ConnectTimeout=5`。152/30 在国内腾云，正常连接 <100ms。超过 5 秒 = 服务器挂了或者断网，不要等待。

### 2. 编码问题
- **30服务器(Windows)**: 输出是 GBK 编码。读取时用 `python3 -c "print(r.stdout.decode('gbk', errors='replace'))"` 或 paramiko 库
- **152服务器(Ubuntu)**: 正常 UTF-8，无编码问题
- **NAS**: 正常 UTF-8，但 scp 不可用

### 3. 文件传输
- **30 + 152**: 用 paramiko sftp 或 `scp`
- **NAS**: scp 不可用，用 `ssh ... "cat > file" < localfile` 传文件

### 4. GitHub推送
- Token 用 `ghp_` 开头的 Classic PAT（Fine-grained PAT 不能 git push）
- 如果本机直连 GitHub 超时，从 152 服务器中转：`ssh 152 "cd /tmp && git clone ... && git push"`

### 5. 本机密钥
- `~/.ssh/id_rsa` — Mac 本机密钥（已生成）
- `~/Downloads/coze.pem` — 30/152 服务器通用密钥
- `~/Desktop/nas_key.pub` — NAS 公钥（需配合密码使用）

## 隧道架构

```
家庭网络 ← NAS(:1081 SOCKS5) ← SSH反向隧道 → 30服务器(:1081)
家庭网络 ← Mac(:1082 Token) ← SSH反向隧道 → 30服务器(:2080)
```

### Mac 隧道（local_tunnel.py）
- 文件: `~/Desktop/local_tunnel.py`
- 端口: localhost:1082
- 认证: 连接后第一行发送 `cherryclaw-local-tunnel-2026\n`
- 30服务器转发端口: 2080
- 自动启动: `~/Library/LaunchAgents/com.cherryclaw.localtunnel.plist`

### NAS 隧道
- SOCKS5: localhost:1081
- 守护: `/volume1/nas_proxy/tunnel_keep.sh`（每60秒自检）
- 文件: `/volume1/nas_proxy/`（持久化目录，重启不丢失）

## 152 服务器服务

| 端口 | 服务 | 说明 |
|------|------|------|
| 29528 | insthunter | Instagram采集 |
| 29538 | redhunter | 小红书抓取 |
| 29540 | tickhunter | TikTok采集 |
| 8080 | mcp-gateway | MCP统一网关 |
| 8081 | mcp-proxy | MCP代理（含registry/search/readme） |
| 29550 | search-mcp | (已删除) |

## 注意事项
- 152 只有 3.6GB 内存，注意进程占用
- redhunter 会产生 Playwright 孤儿进程，定期清理
- pyhton unbuffer 模式解决输出缓存问题（`python3 -u` 或 `PYTHONUNBUFFERED=1`）
