import requests
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime
import pytz
import os
import re

def main():
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

    logging.debug("Initialized RSS feed.")
    
    url = "https://tver.jp/newer"
    response = requests.get(url)
    pageContent = response.text

    logging.debug("Fetched webpage content.")
    logging.debug(pageContent)
        
    # 正規表現で取得する部分
    articles = re.findall(r'<div class="newer-page-main_spEpisodeWrapper__huS6z">.*?</div></div></div></div>', pageContent)
    logging.debug(f"Found {len(articles)} articles.")
    
    for article in articles:
        link_match = re.search(r'href="(/episodes/[^"]+)"', article)
        title_match = re.search(r'<div class="episode-pattern-b-layout_mainTitle__iQ_2j">([^<]+)</div>', article)
        subtitle_match = re.search(r'<div class="episode-pattern-b-layout_subTitle__BnGfu">([^<]+)</div>', article)
        
        link = link_match.group(1) if link_match else "Link not found"
        title = title_match.group(1) if title_match else "Title not found"
        subtitle = subtitle_match.group(1) if subtitle_match else "Subtitle not found"
        
        # タイトルとサブタイトルを結合
        full_title = f"{title} {subtitle}"
        
        # 既存のリンクならスキップ
        if link in existing_links:
            continue
        
        # 現在の日時を取得
        date_now = datetime.now().strftime('%a, %d %b %Y %H:%M:%S %Z')
        
        channel = root.find("channel")
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = full_title
        ET.SubElement(item, "link").text = link
        ET.SubElement(item, "pubDate").text = date_now

    logging.debug("Added new item to RSS.")
                
    # 整形して保存
    xml_str = ET.tostring(root)
    
    # 不正なXML文字を取り除く
    xml_str = re.sub(u'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', xml_str.decode()).encode()
    xml_pretty_str = minidom.parseString(xml_str).toprettyxml(indent="  ")

    # 空白行を取り除く
    xml_pretty_str = os.linesep.join([s for s in xml_pretty_str.splitlines() if s.strip()])

    with open(output_file, "w") as f:
        f.write(xml_pretty_str)

    logging.debug("Saved RSS feed.")

if __name__ == "__main__":
    main()
