
import os
import re
from bs4 import BeautifulSoup
from pyppeteer import launch
from xml.etree.ElementTree import Element, SubElement, tostring, ElementTree
from datetime import datetime, timedelta
import xml.dom.minidom
import xml.etree.ElementTree as ET
import asyncio
import requests
from html import unescape as html_unescape
from urllib.parse import urlparse, parse_qs
from pytz import timezone

# 既存のXMLファイルから情報取得
def get_existing_schedules(file_name):
    existing_schedules = set()
    tree = ET.parse(file_name)
    root = tree.getroot()
    for item in root.findall(".//item"):
        date = item.find('pubDate').text
        title = html_unescape(item.find('title').text)
        url = html_unescape(item.find('link').text)
        existing_schedules.add((date, title, url))
    return existing_schedules

async def main():


    # 現在の日付と時間を日本時間で取得
    jst = timezone('Asia/Tokyo')
    now = datetime.now(jst)
    date = now.strftime("%Y/%m/%d %H:%M")
    
    # 既存のXMLファイルがあれば、その情報を取得
    existing_file = 'makeRSS_TVer.xml'
    existing_schedules = get_existing_schedules(existing_file) if os.path.exists(existing_file) else set()
    
    # 確認用：既存情報が空かどうか
    print(f"既存情報: {existing_schedules}")
    
    # 後で重複チェックするときの為の一覧
    existing_schedules_check = {url for _, _, url in existing_schedules}

    # 確認用：既存情報チェック用も空かどうか
    print(f"既存情報チェック用: {existing_schedules_check}")

    # 新規情報を保存するリスト
    new_schedules = []
        
    # Pyppeteerでブラウザを開く
    browser = await launch(
        executablePath='/usr/bin/chromium-browser',
        headless=True,
        args=[
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-accelerated-2d-canvas',
            '--disable-gpu'
        ],
        defaultViewport=None,
        userDataDir='./user_data'
    )
        
    page = await browser.newPage()
    
    url = "https://tver.jp/newer" 
    await page.goto(url, {'waitUntil': 'networkidle0'})
    await page.waitForSelector('div.newer-page-main_episodeList__f_N7H')  # このクラスが読み込まれるまで待つ

    # ログ出力を追加
    #print("現在のHTTPヘッダー:", response.headers)

    # ページのHTMLを取得
    html = await page.content()
        
    # BeautifulSoupで解析
    soup = BeautifulSoup(html, 'html.parser')

    # スケジュール情報の親divを取得
    parent_div = soup.find('div', class_='newer-page-main_episodeList__f_N7H')

    # 子のdivを全て取得
    day_schedules = parent_div.find_all('div', class_='episode-pattern-c_container__7UBI_')
    #print(f"取得した子divの数: {len(day_schedules)}")  # ここで取得した子divの数を出力

    # 各スケジュールの情報を取得
    for day_schedule in day_schedules:
        # ここで各子divの中身を出力して確認する
        #print(f"各子divの中身: {day_schedule}")

        link_elem = day_schedule.find('a', class_='episode-pattern-c_thumbnailWrapper__JVZ5K')
        if link_elem:
            link = link_elem['href']
        else:
            link = None

        title_elem_main = day_schedule.find('div', class_='episode-pattern-c_seriesTitle__8MwGR')
        if title_elem_main:
            title_main = title_elem_main.text.strip()
        else:
            title_main = None

        title_elem_sub = day_schedule.find('div', class_='episode-pattern-c_episodeTitle__FCfJd')
        if title_elem_sub:
            title_sub = title_elem_sub.text.strip()
        else:
            title_sub = None
        
        title_provider_elem = day_schedule.find('div', class_='episode-pattern-b-layout_productionProviderName__Y3fZn')
        if title_provider_sub:
            title_provider_sub = title_provider_elem.text.strip()
        else:
            title_provider_sub = ""

        if link_elem and title_elem_main and title_elem_sub:
            link = "https://tver.jp" + link_elem['href']
            title_main = title_elem_main.text
            title_sub = title_elem_sub.text
            title_provider = title_provider_sub.text

            full_title = f"{title_main} {title_sub}"
            if title_provider:
                full_title += f" {title_provider}"

            
            #print(f"Full Title: {full_title}")
            #print(f"Link: {link}")
            
            # existing_schedules_check に含まれているかどうかを確認
            if link not in existing_schedules_check:
                new_schedules.append((date, full_title, link))
            else:
                print(f"既存情報やからスキップ: {full_title}")  # 追加したログ出力

    
    print(new_schedules)
            
    # 既存のスケジュール情報もリスト形式に変換
    existing_schedules_list = [(date, title, link) for date, title, link in existing_schedules]
    
    # 既存の情報と新規情報を合わせる
    all_schedules = existing_schedules_list + new_schedules

    # 日付の降順にソート
    all_schedules.sort(key=lambda x: datetime.strptime(x[0], "%Y/%m/%d %H:%M"), reverse=True)

    # RSSフィードを生成
    rss = Element("rss", version="2.0")
    channel = SubElement(rss, "channel")
    SubElement(channel, "title").text = "TVer"
    SubElement(channel, "description").text = ""
    SubElement(channel, "link").text = ""
    for date, title, link in all_schedules:
        item = SubElement(channel, "item")
        SubElement(item, "title").text = title
        SubElement(item, "link").text = link
        SubElement(item, "pubDate").text = date
    
    xml_str = xml.dom.minidom.parseString(tostring(rss)).toprettyxml(indent="   ")

    # 空白行を取り除く
    xml_str = os.linesep.join([s for s in xml_str.splitlines() if s.strip()])

    # ファイルに保存
    with open(existing_file, 'w', encoding='utf-8') as f:
        f.write(xml_str)

# 非同期関数を実行
asyncio.get_event_loop().run_until_complete(main())
