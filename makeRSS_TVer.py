import asyncio
from pyppeteer import launch
from datetime import datetime
import xml.etree.ElementTree as ET
import os
import re

async def main():
    output_file = "makeRSS_TVer.xml"
    
    # 既存のRSSフィードを読み込む
    existing_links = set()
    if os.path.exists(output_file):
        tree = ET.parse(output_file)
        root = tree.getroot()
        for item in root.findall(".//item/link"):
            existing_links.add(item.text)
    else:
        root = ET.Element("rss", version="2.0")
        channel = ET.SubElement(root, "channel")
        ET.SubElement(channel, "title").text = "TVer"
        ET.SubElement(channel, "description").text = "TVer"
        ET.SubElement(channel, "link").text = "https://tver.jp/newer"

    print("Initialized RSS feed.")
    
    # Pyppeteerでブラウザ操作
    browser = await launch(headless=True)
    page = await browser.newPage()
    await page.goto('https://tver.jp/newer')
    
    pageContent = await page.content()
    
    # 正規表現で記事を抽出
    articles = re.findall(r'<div class="newer-page-main_spEpisodeWrapper__huS6z">.*?</div></div></div></div>', pageContent)
    print(f"Found {len(articles)} articles.")
    
    for article in articles:
        link_match = re.search(r'href="(/episodes/[^"]+)"', article)
        title_match = re.search(r'<div class="episode-pattern-b-layout_mainTitle__iQ_2j">([^<]+)</div>', article)
        subtitle_match = re.search(r'<div class="episode-pattern-b-layout_subTitle__BnGfu">([^<]+)</div>', article)
        
        link = link_match.group(1) if link_match else "Link not found"
        title = title_match.group(1) if title_match else "Title not found"
        subtitle = subtitle_match.group(1) if subtitle_match else "Subtitle not found"
        
        full_title = f"{title} {subtitle}"
        
        if link in existing_links:
            continue
        
        date_now = datetime.now().strftime('%a, %d %b %Y %H:%M:%S %Z')
        
        channel = root.find("channel")
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = full_title
        ET.SubElement(item, "link").text = link
        ET.SubElement(item, "pubDate").text = date_now
    
    # RSSを保存
    xml_str = ET.tostring(root)
    xml_pretty_str = minidom.parseString(xml_str).toprettyxml(indent="  ")
    xml_pretty_str = os.linesep.join([s for s in xml_pretty_str.splitlines() if s.strip()])
    with open(output_file, "w") as f:
        f.write(xml_pretty_str)
    
    print("Saved RSS feed.")
    await browser.close()

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
