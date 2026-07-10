#!/usr/bin/env python3
"""给 xhs_scraper.py 打补丁：增加登录检测 + VNC 通知"""
import re

filepath = '/opt/redhunter/backend/app/services/xhs_scraper.py'

with open(filepath, 'r') as f:
    content = f.read()

changes = []

# 1. 添加 aiohttp import
if 'import aiohttp' not in content:
    content = content.replace(
        'from typing import List, Dict',
        'from typing import List, Dict\nimport aiohttp'
    )
    changes.append('Added import aiohttp')

# 2. 添加登录检测方法
login_check = '''
    async def _check_login_block(self, page, keyword: str) -> bool:
        """检测是否被登录弹窗挡住，是则触发 VNC 展示并等待扫码"""
        try:
            blocked = await page.evaluate('() => { const t = document.body.innerText; return t.includes("\\u767b\\u5f55\\u540e\\u67e5\\u770b") || t.includes("\\u767b\\u5f55\\u540e\\u63a8\\u8350"); }')
            if not blocked:
                return False

            logger.warning(f"[登录拦截] 检测到登录弹窗 (keyword={keyword})，触发 VNC 展示")

            try:
                async with aiohttp.ClientSession() as session:
                    await session.post(
                        "http://122.51.32.30:5098/api/vnc/trigger",
                        json={"reason": "小红书需要扫码登录", "keyword": keyword},
                        timeout=aiohttp.ClientTimeout(total=10)
                    )
                logger.info("[登录拦截] 已通知 VNC 网关")
            except Exception as e:
                logger.error(f"[登录拦截] 通知 VNC 网关失败: {e}")

            logger.info("[登录拦截] 等待扫码登录...")
            for i in range(120):
                await asyncio.sleep(5)
                still_blocked = await page.evaluate('() => { return document.body.innerText.includes("\\u767b\\u5f55\\u540e\\u67e5\\u770b"); }')
                if not still_blocked:
                    logger.info(f"[登录拦截] 登录完成！等待 {i*5} 秒")
                    await asyncio.sleep(3)
                    return False

                if i % 12 == 0 and i > 0:
                    logger.info(f"[登录拦截] 仍在等待扫码... ({i*5}s)")
                    try:
                        async with aiohttp.ClientSession() as session:
                            await session.post(
                                "http://122.51.32.30:5098/api/vnc/trigger",
                                json={"reason": f"小红书扫码登录等待中 ({i*5}秒)", "keyword": keyword},
                                timeout=aiohttp.ClientTimeout(total=10)
                            )
                    except:
                        pass

            logger.warning("[登录拦截] 等待超时（10分钟），继续尝试爬取")
            return False
        except Exception as e:
            logger.error(f"[登录拦截] 检测异常: {e}")
            return False
'''

if '_check_login_block' not in content:
    content = content.replace(
        '    async def search_all_images(self, keyword: str, limit: int = 20) -> List[Dict]:',
        login_check + '\n    async def search_all_images(self, keyword: str, limit: int = 20) -> List[Dict]:'
    )
    changes.append('Added _check_login_block method')

# 3. 在 page.goto 后插入检测调用
old = 'await asyncio.sleep(page_scroll_pause())\n\n                new_notes'
new = 'await asyncio.sleep(page_scroll_pause())\n\n                # === 登录检测 ===\n                if await self._check_login_block(page, keyword):\n                    continue\n\n                new_notes'

if old in content:
    content = content.replace(old, new)
    changes.append('Inserted login check call after page.goto')
else:
    changes.append('[FAIL] Pattern not found')
    import re
    for m in re.finditer(r'await asyncio\.sleep\(page_scroll_pause\(\)\)', content):
        start = max(0, m.start())
        end = min(len(content), m.end() + 60)
        changes.append(f'  Found at pos {m.start()}: ...{content[start:end]}...')

with open(filepath, 'w') as f:
    f.write(content)

for c in changes:
    print(f'  {c}')
print('=== 修改完成 ===')
