
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
    esponse = await page.goto(url)

    # ログ出力を追加
    print("現在のHTTPヘッダー:", response.headers)

    # ページのHTMLを取得
    html = await page.content()
        
    # BeautifulSoupで解析
    soup = BeautifulSoup(html, 'html.parser')

    # スケジュール情報の取得
    day_schedules = soup.find_all('div', class_='sc--day')
    print(f"day_schedules: {day_schedules}")  # ここで取得した日ごとのスケジュール情報を出力

    # 各スケジュールの情報を取得
    for day_schedule in day_schedules:
        date_tag = day_schedule.find('div', class_='sc--day__hd js-pos a--tx')
        if date_tag is None:
            continue
        date = f"{yyyymm[:4]}/{yyyymm[4:]}/{date_tag.find('p', class_='sc--day__d f--head').text}"
            
        schedule_links = day_schedule.find_all('a', class_='m--scone__a hv--op')
            
        for link in schedule_links:
                
            title = re.search(r'<p class="m--scone__ttl">(.*?)</p>', str(link.find('p', class_='m--scone__ttl'))).group(1)
            title_tag = link.find('p', class_='m--scone__ttl')
            if title_tag:
                title = title_tag.get_text()
            title = html_unescape(str(title)) 
                    
            url = link['href']
            url = html_unescape(str(url))
                
            category = link.find('p', class_='m--scone__cat__name').text
            start_time_tag = link.find('p', class_='m--scone__start')
            start_time = start_time_tag.text if start_time_tag else ''

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
    SubElement(channel, "title").text = "弓木奈於のスケジュール"
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
