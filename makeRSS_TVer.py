
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

#URLが可変する部分を除外してURLを確認する
def extract_url_part(url):
    parsed_url = urlparse(url)
    path = parsed_url.path.split("/")[-1]  # /103002 や /102232 を取得
    query = parse_qs(parsed_url.query)
    unique_part = f"{path}_{query.get('pri1', [''])[0]}_{query.get('wd00', [''])[0]}_{query.get('wd01', [''])[0]}_{query.get('wd02', [''])[0]}"
    return unique_part


async def main():

    # 既存のXMLファイルがあれば、その情報を取得
    existing_file = 'makeRSS_TVer.xml'
    existing_schedules = get_existing_schedules(existing_file) if os.path.exists(existing_file) else set()

    # 後で重複チェックするときの為の一覧
    existing_schedules_check = {(date, extract_url_part(url)) for date, _, url, _, _ in existing_schedules}
    
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
    response = await page.goto(url)

    # ログ出力を追加
    print("現在のHTTPヘッダー:", response.headers)

    # ページのHTMLを取得
    html = await page.content()
        
    # BeautifulSoupで解析
    soup = BeautifulSoup(html, 'html.parser')
    print(soup.prettify()) 

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
            

            # 新規情報の確認 URLは変わるので日付とタイトルだけで確認
            extracted_url = extract_url_part(url)
            try:
                datetime.strptime(date, "%Y/%m/%d")  # ここで日付のフォーマットをチェック
                if (date, extracted_url) not in existing_schedules_check:
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
