#!/usr/bin/env python3
"""Fix: _check_login_block should return True when login was detected (so caller skips current iteration)"""

filepath = '/opt/redhunter/backend/app/services/xhs_scraper.py'

with open(filepath, 'r') as f:
    content = f.read()

# Bug 1: The method should return True when login was detected (to trigger continue)
# Currently returns False in ALL cases

# Fix the timeout case: return True (was blocked, should retry)
content = content.replace(
    '            logger.warning("[登录拦截] 等待超时（10分钟），继续尝试爬取")\n            return False',
    '            logger.warning("[登录拦截] 等待超时（10分钟），跳过本轮重试")\n            return True'
)

# Fix the success case: return True (was blocked, now retry)
content = content.replace(
    '                    await asyncio.sleep(3)\n                    return False',
    '                    await asyncio.sleep(3)\n                    return True'
)

# Bug 2: The periodic reminder still uses direct POST to 30 (which doesn't work due to firewall)
# Replace with file flag method
old_reminder = '''                if i % 12 == 0 and i > 0:
                    logger.info(f"[登录拦截] 仍在等待扫码... ({i*5}s)")
                    try:
                        async with aiohttp.ClientSession() as session:
                            await session.post(
                                "http://122.51.32.30:5098/api/vnc/trigger",
                                json={"reason": f"小红书扫码登录等待中 ({i*5}秒)", "keyword": keyword},
                                timeout=aiohttp.ClientTimeout(total=10)
                            )
                    except:
                        pass'''

new_reminder = '''                if i % 12 == 0 and i > 0:
                    logger.info(f"[登录拦截] 仍在等待扫码... ({i*5}s)")
                    try:
                        from app.routers.vnc_router import set_login_needed
                        set_login_needed(f"小红书扫码登录等待中 ({i*5}秒)", keyword)
                    except:
                        pass'''

if old_reminder in content:
    content = content.replace(old_reminder, new_reminder)
    print("[FIXED] Reminder now uses file flag instead of HTTP POST")
else:
    print("[WARN] Reminder pattern not found")

with open(filepath, 'w') as f:
    f.write(content)

print("[FIXED] _check_login_block returns True on login detection")
print("=== FIX COMPLETE ===")
