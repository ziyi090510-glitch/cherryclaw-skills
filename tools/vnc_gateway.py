#!/usr/bin/env python3
"""
VNC 网关服务 — 运行在 30 服务器（Windows）
端口 5098

架构（反转）：
  30 轮询 152 的 /api/vnc/status
  当 login_needed=true → 打开 noVNC 页面 + Bark 通知
  平时空载无感

依赖：
  - SSH 隧道 (30→152): ssh -L 6080:localhost:6080
  - 152 的 x11vnc :5900 + noVNC websockify :6080
"""
import sys, os, json, logging, socket, subprocess, threading, time, urllib.request
from pathlib import Path
from flask import Flask, request, jsonify

# ========== 配置 ==========
PORT = 5098
POLL_INTERVAL = 3  # 轮询间隔（秒）
SSH_KEY = r"C:\Users\Administrator\Desktop\cherry claw\coze.pem"
SSH_HOST = "ubuntu@124.223.64.152"
VNC_LOCAL_PORT = 6080
VNC_URL = f"http://localhost:{VNC_LOCAL_PORT}/vnc.html?autoconnect=1&host=localhost&port={VNC_LOCAL_PORT}&resize=scale"
REDHUNTER_STATUS_URL = "http://124.223.64.152:29538/api/vnc/status"
BARK_URL = "https://api.day.app"
BARK_KEY = "sj7VJetGeZ8zHdx4g9S4gf"
LOG_FILE = Path(__file__).parent / "vnc_gateway.log"
# ==========================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"), logging.StreamHandler()],
)
logger = logging.getLogger("vnc_gateway")

app = Flask(__name__)

# 状态
_vnc_shown = False  # 防止重复弹窗
_poll_thread = None
_stop_polling = False


def check_tunnel() -> bool:
    """检查本地 VNC 隧道是否通"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.settimeout(3)
        result = s.connect_ex(("127.0.0.1", VNC_LOCAL_PORT))
        return result == 0
    finally:
        s.close()


def ensure_tunnel():
    """确保 SSH 隧道存在"""
    if check_tunnel():
        return True
    logger.warning("VNC 隧道未建立，正在启动...")
    try:
        subprocess.Popen(
            [
                "ssh", "-o", "StrictHostKeyChecking=no",
                "-o", "ServerAliveInterval=15",
                "-o", "ServerAliveCountMax=3",
                "-f", "-N",
                "-L", f"{VNC_LOCAL_PORT}:127.0.0.1:{VNC_LOCAL_PORT}",
                "-i", SSH_KEY, SSH_HOST,
            ],
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        for _ in range(10):
            time.sleep(1)
            if check_tunnel():
                logger.info("SSH 隧道已建立")
                return True
        logger.error("SSH 隧道建立失败")
        return False
    except Exception as e:
        logger.error(f"建立 SSH 隧道异常: {e}")
        return False


def open_browser(url: str):
    """在 Windows 上打开 Chrome 展示 VNC"""
    try:
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        ]
        chrome = None
        for p in chrome_paths:
            if os.path.exists(p):
                chrome = p
                break
        if chrome:
            subprocess.Popen(
                [chrome, "--new-window", url, "--window-size=900,700"],
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            logger.info(f"Chrome 已打开: {url}")
        else:
            import webbrowser
            webbrowser.open(url)
            logger.info(f"默认浏览器已打开: {url}")
    except Exception as e:
        logger.error(f"打开浏览器失败: {e}")


def send_bark(title: str, body: str, url: str = ""):
    """发送 Bark 推送"""
    try:
        import requests
        payload = {
            "title": title,
            "body": body,
            "group": "xhs_login",
            "icon": "https://img.icons8.com/color/48/qr-code.png",
        }
        if url:
            payload["url"] = url
        resp = requests.post(f"{BARK_URL}/{BARK_KEY}", json=payload, timeout=10)
        logger.info(f"Bark 通知已发送: {resp.status_code}")
    except Exception as e:
        logger.error(f"Bark 通知失败: {e}")


def poll_redhunter():
    """轮询 152 的 VNC 状态（后台线程）"""
    global _vnc_shown
    logger.info("轮询线程启动，每 %ds 检查 152 登录状态", POLL_INTERVAL)

    while not _stop_polling:
        try:
            resp = urllib.request.urlopen(REDHUNTER_STATUS_URL, timeout=5)
            data = json.loads(resp.read().decode())

            if data.get("login_needed") and not _vnc_shown:
                _vnc_shown = True
                info = data.get("info", "小红书需要扫码登录")
                keyword = data.get("keyword", "")

                logger.info(f"检测到登录需要！info={info}")

                # 1. 确保隧道
                ensure_tunnel()

                # 2. 打开 noVNC 页面（自动连接）
                open_browser(VNC_URL)

                # 3. Bark 通知
                title = "需要扫码登录"
                body = info
                if keyword:
                    body += f"\n关键词: {keyword}"
                send_bark(title, body, VNC_URL)

            elif not data.get("login_needed"):
                if _vnc_shown:
                    logger.info("登录已完成，重置 VNC 展示状态")
                _vnc_shown = False

        except urllib.error.URLError:
            pass  # 152 暂时不可达，下次再试
        except Exception as e:
            logger.error(f"轮询异常: {e}")

        time.sleep(POLL_INTERVAL)


# ========== Flask 路由 ==========

@app.route("/api/vnc/trigger", methods=["POST"])
def trigger_vnc():
    """（兼容旧接口）手动触发 VNC 展示"""
    global _vnc_shown
    data = request.get_json() or {}
    reason = data.get("reason", "需要扫码登录")
    keyword = data.get("keyword", "")

    _vnc_shown = True
    ensure_tunnel()
    open_browser(VNC_URL)

    title = "需要扫码登录"
    body = reason
    if keyword:
        body += f"\n关键词: {keyword}"
    send_bark(title, body, VNC_URL)

    logger.info(f"VNC 手动触发: {reason}")
    return jsonify({"status": "ok", "message": "VNC 页面已打开，请扫码"})


@app.route("/api/vnc/status", methods=["GET"])
def vnc_status():
    """查询 VNC 网关状态"""
    tunnel_ok = check_tunnel()
    return jsonify({
        "vnc_tunnel": tunnel_ok,
        "vnc_shown": _vnc_shown,
        "polling_alive": _poll_thread is not None and _poll_thread.is_alive(),
        "vnc_url": VNC_URL if tunnel_ok else None,
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "vnc_gateway"})


def main():
    global _poll_thread, _stop_polling

    logger.info("=" * 40)
    logger.info(f"VNC 网关服务启动 - 端口 {PORT}")
    logger.info(f"轮询 152: {REDHUNTER_STATUS_URL}")
    logger.info(f"VNC 地址: {VNC_URL}")
    logger.info("=" * 40)

    # 启动时检查隧道
    if check_tunnel():
        logger.info("SSH 隧道已存在")
    else:
        logger.info("SSH 隧道未建立，尝试连接...")
        ensure_tunnel()

    # 启动轮询线程
    _stop_polling = False
    _poll_thread = threading.Thread(target=poll_redhunter, daemon=True)
    _poll_thread.start()

    # 启动 Flask
    app.run(host="0.0.0.0", port=PORT, debug=False)


if __name__ == "__main__":
    main()
