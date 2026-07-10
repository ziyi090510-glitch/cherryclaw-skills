---
name: redhunter-vnc-login
description: 小红书爬虫(RedHunter)遇到登录拦截时的 VNC 扫码登录系统。检测到"登录后查看"弹窗后，自动触发 VNC 展示 + Bark 通知，等待用户扫码登录后恢复爬取。
---

# RedHunter VNC 扫码登录系统

## 架构

```
152 服务器 (Linux, 124.223.64.152)      30 服务器 (Windows, 122.51.32.30)
┌──────────────────────────────┐      ┌──────────────────────────────┐
│  Xvfb :99 + Chrome(CDP 9222) │      │  Chrome 自动打开 noVNC      │
│  x11vnc :5900                 │ SSH  │  VNC 网关 :5098 (轮询)      │
│  noVNC websockify :6080      │──→   │  Bark 通知                  │
│  RedHunter API :29538         │隧道  │  Windows 开机自启           │
│  └─ VNC 路由 + 登录检测      │      │  SSH 隧道 :6080→152:6080    │
└──────────────────────────────┘      └──────────────────────────────┘
```

## 工作流程

1. RedHunter 爬虫调用 `xhs_scraper.search_all_images()`
2. 每次 `page.goto()` 后执行 `_check_login_block()`
3. 检测到页面包含「登录后查看」→ 写入 `/tmp/xhs_login_needed.flag`
4. 30 的 VNC 网关每 3 秒轮询 152 的 `/api/vnc/status`
5. 检测到标志 → 打开 Chrome(noVNC, autoconnect=1) + Bark 推送
6. 用户扫码 → 检测登录完成 → 清除标志 → 爬虫继续

## 组件清单

### 152 服务器组件

| 组件 | 端口 | 启动方式 | 说明 |
|------|------|----------|------|
| Xvfb | :99 | `Xvfb :99 -screen 0 1280x900x24` | 虚拟显示器 |
| Chrome CDP | 9222 | `google-chrome --remote-debugging-port=9222 --no-sandbox --user-data-dir=/tmp/chrome_persist` | 浏览器自动化 |
| x11vnc | 5900 | `x11vnc -display :99 -forever -shared -rfbport 5900` | Xvfb 转 VNC |
| noVNC | 6080 | `websockify --web=/usr/share/novnc 6080 localhost:5900` | Web VNC 客户端 |
| RedHunter | 29538 | `uvicorn app.main:app --host 0.0.0.0 --port 29538` | 爬虫 API |

### 30 服务器组件

| 组件 | 端口 | 文件路径 | 说明 |
|------|------|----------|------|
| VNC 网关 | 5098 | `C:\Users\Administrator\Desktop\vnc_gateway.py` | 轮询 + 弹窗 + Bark |
| SSH 隧道 | 6080 | `ssh -L 6080:localhost:6080 ubuntu@124.223.64.152` | 转发 noVNC |
| 启动脚本 | - | `C:\Users\Administrator\Desktop\start_vnc_gateway.bat` | 开机自启 |

## 关键文件

### 152 服务器

```
/opt/redhunter/backend/
├── app/
│   ├── main.py                    # 主入口，已注册 vnc_router
│   ├── routers/
│   │   └── vnc_router.py          # VNC 状态 API (文件标志方式)
│   └── services/
│       └── xhs_scraper.py         # 已注入登录检测
└── .env                           # XHS_COOKIE 配置
```

### 30 服务器

```
C:\Users\Administrator\Desktop\
├── vnc_gateway.py                 # VNC 网关（轮询 + 弹窗 + Bark）
├── start_vnc_gateway.bat          # 开机自启脚本
├── vnc_gateway.log                # 运行日志
└── cherry claw\coze.pem           # SSH 密钥
```

## 部署步骤

### 首次部署

```bash
# 152 服务器：启动 Xvfb（如果没在跑）
Xvfb :99 -screen 0 1280x900x24

# 152 服务器：启动 x11vnc
x11vnc -display :99 -forever -shared -rfbport 5900

# 152 服务器：启动 noVNC
websockify --web=/usr/share/novnc 6080 localhost:5900 &

# 152 服务器：启动 Chrome（持久化用户数据）
export DISPLAY=:99
google-chrome --remote-debugging-port=9222 --no-sandbox \
  --window-size=1280,900 --user-data-dir=/tmp/chrome_persist \
  --proxy-server=socks5://127.0.0.1:1081

# 30 服务器：建立 SSH 隧道
ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=15 -f -N \
  -L 6080:localhost:6080 \
  -i "C:\Users\Administrator\Desktop\cherry claw\coze.pem" \
  ubuntu@124.223.64.152

# 30 服务器：启动 VNC 网关
python C:\Users\Administrator\Desktop\vnc_gateway.py
```

### 登录检测代码注入（xhs_scraper.py）

在 `page.goto()` 后添加：
```python
# === 登录检测 ===
if await self._check_login_block(page, keyword):
    continue
```

`_check_login_block` 方法功能：
1. 检查页面是否包含「登录后查看」「登录后推荐」
2. 检测到则写入 `/tmp/xhs_login_needed.flag`
3. 轮询等待（每 5s，最长 10 分钟）
4. 登录完成返回 `True` → 调用方 `continue` 重试
5. 超时也返回 `True`（跳过本轮，继续尝试）

## 故障排查

### Chrome 启动失败
```
# 检查 DISPLAY 是否设置
echo $DISPLAY  # 应该显示 :99

# 检查 Xvfb 是否在运行
ps aux | grep Xvfb

# 手动启动 Chrome
export DISPLAY=:99
google-chrome --remote-debugging-port=9222 --no-sandbox about:blank
```

### VNC 不显示
```
# 检查 x11vnc
ss -tlnp | grep 5900

# 检查 noVNC
ss -tlnp | grep 6080

# 测试 noVNC 页面
curl -s http://127.0.0.1:6080/vnc.html | head -3

# 检查 SSH 隧道（从 30）
netstat -ano | findstr :6080
```

### 网关未触发
```
# 检查登录标志（152 上）
cat /tmp/xhs_login_needed.flag

# 检查 API（从 30）
curl -s http://124.223.64.152:29538/api/vnc/status

# 检查网关日志
tail -20 C:\Users\Administrator\Desktop\vnc_gateway.log
```

### Bark 通知不到
- 确认 Bark key 正确（在 `vnc_gateway.py` 中）
- 测试：`curl -X POST https://api.day.app/YOUR_KEY -d '{"body":"test"}'`
