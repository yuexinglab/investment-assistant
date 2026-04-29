"""诊断脚本：获取并分析 result_new 页面的 HTML"""
import os
import re

base_dir = r"D:\HuaweiMoveData\Users\86136\Documents\GitHub\investment-assistant"
os.chdir(base_dir)

from app import app

proj_id = "A1_1_0测试2_20260429_151410"
output_file = os.path.join(base_dir, "debug_result_new.html")

with app.test_client() as client:
    response = client.get(f"/project/{proj_id}/result_new")
    status = response.status_code
    content_length = len(response.data)
    html = response.data.decode('utf-8', errors='replace')

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

    results = []

    def log(msg):
        results.append(msg)

    log(f"Status: {status}")
    log(f"Content-Length: {content_length}")

    body_match = re.search(r'<body[^>]*>', html)
    body_close = re.findall(r'</body>', html)
    log(f"Body tag: {'OK' if body_match else 'MISSING'}")
    log(f"Body close tags: {len(body_close)}")

    scripts = re.findall(r'<script[^>]*>', html)
    log(f"\nScript tags count: {len(scripts)}")

    pointer_events = re.findall(r'pointer-events\s*:\s*none', html, re.IGNORECASE)
    log(f"pointer-events:none occurrences: {len(pointer_events)}")

    overlay_divs = re.findall(r'<div[^>]*class="[^"]*overlay[^"]*"', html, re.IGNORECASE)
    log(f"Overlay divs: {len(overlay_divs)}")

    tab_content_active = re.search(r'id="tab-(\w+)"[^>]*class="[^"]*active[^"]*"', html)
    if tab_content_active:
        log(f"Initial active tab: tab-{tab_content_active.group(1)}")
    else:
        log("No active tab found!")

    style_link = re.search(r'<link[^>]*href="(/static/style\.css[^"]*)"[^>]*>', html)
    if style_link:
        css_url = style_link.group(1)
        log(f"style.css link: {css_url}")
        css_response = client.get(css_url)
        log(f"style.css status: {css_response.status_code}, size: {len(css_response.data)}")
    else:
        log("style.css link NOT FOUND")

    style_blocks = re.findall(r'<style[^>]*>(.*?)</style>', html, re.DOTALL)
    for i, block in enumerate(style_blocks):
        if 'tab-content' in block:
            log(f"\nStyle block {i+1} has .tab-content rules:")
            tab_rules = re.findall(r'[^\n]*tab-content[^\n]*', block)
            for rule in tab_rules:
                log(f"  {rule.strip()}")

    if 'fetch(' in html and 'getReader()' in html:
        log("\nSSE/ReadableStream code FOUND in page!")

    tab_bar = re.search(r'<div[^>]*class="[^"]*tab-bar[^"]*"[^>]*>', html)
    if tab_bar:
        log(f"\nTab bar: {tab_bar.group(0)[:100]}")

    report_wrap = re.search(r'<div[^>]*class="report-wrap"', html)
    log(f"report-wrap div: {'OK' if report_wrap else 'MISSING'}")

    with open(os.path.join(base_dir, "debug_result.txt"), 'w', encoding='utf-8') as f:
        f.write('\n'.join(results))

print("Done. Check debug_result.txt and debug_result_new.html")
