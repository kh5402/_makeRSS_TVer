
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

    # 既存のXMLファイルがあれば、その情報を取得
    existing_file = 'makeRSS_TVer.xml'
    existing_schedules = get_existing_schedules(existing_file) if os.path.exists(existing_file) else set()

    # 後で重複チェックするときの為の一覧
    existing_schedules_check = {url for _, _, url in existing_schedules}
    
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
    #print(soup.prettify()) 

    # 該当するdivタグを取得
    target_divs = soup.select('div.episode-pattern-c_container__7UBI_')

    # 確認のために出力
    print(f"取得したdivの数: {len(target_divs)}")

    # スケジュール情報の取得
    day_schedules = soup.find_all('div', class_='newer-page-main_episodeList__f_N7H')
    print(f"取得したdivの数: {len(day_schedules)}")  # ここで取得したdivの数を出力

    # 各スケジュールの情報を取得
    for day_schedule in day_schedules:
        # ここで各divの中身を出力して確認する
        print(f"各divの中身: {day_schedule}")

    


    # 各エピソードの情報を取得
    episodes = soup.find_all('div', class_='episode-pattern-b-layout_container__iciAm')
    
    for episode in episodes:
        link_elem = episode.find('a', class_='episode-pattern-b-layout_metaText__bndIm')
        title_elem_main = episode.find('div', class_='episode-pattern-b-layout_mainTitle__iQ_2j')
        title_elem_sub = episode.find('div', class_='episode-pattern-b-layout_subTitle__BnGfu')
        
        if link_elem and title_elem_main and title_elem_sub:
            link = link_elem['href']
            title_main = title_elem_main.text
            title_sub = title_elem_sub.text

            full_title = f"{title_main} {title_sub}"
            
            print(f"Full Title: {full_title}")
            print(f"Link: {link}")
            

            # 新規情報の確認
            try:
                datetime.strptime(date, "%Y/%m/%d")  # ここで日付のフォーマットをチェック
                print(f"日付のフォーマットはOKやで: {date}")

                # existing_schedules_check に含まれているかどうかを確認
                if url not in existing_schedules_check:
                    print(f"既存情報やからスキップ: {date, extracted_url}")  # 追加したログ出力
                else:
                    new_schedules.append((date, title, url, category, start_time))
                    print(f"新規情報を追加: {date, title, url, category, start_time}")  # ここで新規情報を出力
            except ValueError:
                print(f"新規情報の日付のフォーマットがおかしいから、このデータはスキップするで！日付: {date}")


    
    print(new_schedules)
            
    # 既存のスケジュール情報もリスト形式に変換
    existing_schedules_list = [(date, title, url) for date, title, url in existing_schedules]
    
    # 既存の情報と新規情報を合わせる
    all_schedules = existing_schedules_list + new_schedules

    # 日付の降順にソート
    all_schedules.sort(key=lambda x: datetime.strptime(x[0], "%Y/%m/%d"), reverse=True)

    # RSSフィードを生成
    rss = Element("rss", version="2.0")
    channel = SubElement(rss, "channel")
    SubElement(channel, "title").text = "TVer"
    SubElement(channel, "description").text = ""
    SubElement(channel, "link").text = ""
    for date, title, url, category, start_time in all_schedules:
        item = SubElement(channel, "item")
        SubElement(item, "title").text = title
        SubElement(item, "link").text = url
        SubElement(item, "pubDate").text = date
        SubElement(item, "category").text = category
        SubElement(item, "start_time").text = start_time

    
    xml_str = xml.dom.minidom.parseString(tostring(rss)).toprettyxml(indent="   ")

    # ファイルに保存
    with open(existing_file, 'w', encoding='utf-8') as f:
        f.write(xml_str)

# 非同期関数を実行
asyncio.get_event_loop().run_until_complete(main())
