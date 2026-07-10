"""VNC 触发路由器 — 供 30 服务器轮询检测登录状态"""
import os, logging
from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/vnc", tags=["vnc"])

LOGIN_NEEDED_FILE = "/tmp/xhs_login_needed.flag"

@router.get("/status")
async def vnc_status():
    """30 服务器轮询此接口，检测是否需要展示 VNC"""
    needed = os.path.exists(LOGIN_NEEDED_FILE)
    if needed:
        try:
            with open(LOGIN_NEEDED_FILE, "r") as f:
                info = f.read().strip()
        except:
            info = ""
        return {"login_needed": True, "info": info, "keyword": info}
    return {"login_needed": False, "info": ""}


def set_login_needed(reason: str = "小红书需要扫码登录", keyword: str = ""):
    """设置登录需要标志（供 xhs_scraper.py 调用）"""
    try:
        with open(LOGIN_NEEDED_FILE, "w") as f:
            f.write(f"{reason}|{keyword}")
        logger.info(f"[VNC] 登录需要标志已设置: {reason}")
    except Exception as e:
        logger.error(f"[VNC] 设置登录标志失败: {e}")


def clear_login_needed():
    """清除登录需要标志"""
    try:
        if os.path.exists(LOGIN_NEEDED_FILE):
            os.remove(LOGIN_NEEDED_FILE)
            logger.info("[VNC] 登录需要标志已清除")
    except Exception as e:
        logger.error(f"[VNC] 清除登录标志失败: {e}")
