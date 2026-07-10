#!/usr/bin/env python3
"""诊断小红书搜索为什么返回0条"""
import asyncio, json
from playwright.async_api import async_playwright

async def main():
    p = await async_playwright().start()
    b = await p.chromium.connect_over_cdp('http://localhost:9222')
    ctx = b.contexts[0]
    pg = await ctx.new_page()
    await pg.add_init_script('Object.defineProperty(navigator,"webdriver",{get:()=>false})')

    await pg.goto('https://www.xiaohongshu.com/search_result/?keyword=%E6%89%8B%E6%9C%BA%E5%A3%B3',
                  wait_until='domcontentloaded', timeout=30000)
    await asyncio.sleep(5)

    print(f'URL: {pg.url[:80]}')
    print(f'Title: {(await pg.title())[:50]}')

    result = await pg.evaluate('''() => {
        var s = window.__INITIAL_STATE__;
        if (s && s.search && s.search.notes) {
            return {found: true, count: s.search.notes.length};
        }
        return {found: false, body: (document.body?document.body.innerText.slice(0,300):''),
                state_keys: s ? Object.keys(s).slice(0,5) : []};
    }''')
    print(f'Result: {json.dumps(result, ensure_ascii=False)[:200]}')

    await b.close()

asyncio.run(main())
