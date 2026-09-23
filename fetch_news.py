"""국세·재정 공공기관 RSS를 모아 news.json 으로 저장한다.
GitHub Actions 에서 하루 한 번 실행된다. 파이썬 기본 기능만 사용."""

import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

KST = timezone(timedelta(hours=9))

FEEDS = [
    ("재정경제부", "https://mofe.go.kr/com/detailRssTagService.do?bbsId=MOSFBBS_000000000028"),
    ("재정경제부", "https://mofe.go.kr/com/detailRssTagService.do?bbsId=MOSFBBS_000000000030"),
]

MAX_ITEMS = 15
TIMEOUT = 20


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (news-collector)"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as res:
        return res.read()


def clean(text):
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    return " ".join(text.split()).strip()


def to_date(value):
    if not value:
        return ""
    try:
        return parsedate_to_datetime(value).astimezone(KST).strftime("%Y.%m.%d")
    except Exception:
        pass
    m = re.search(r"(\d{4})[-.](\d{2})[-.](\d{2})", value)
    if m:
        return f"{m.group(1)}.{m.group(2)}.{m.group(3)}"
    return ""


def parse(source, xml_bytes):
    items = []
    root = ET.fromstring(xml_bytes)
    for node in root.iter("item"):
        title = clean(node.findtext("title"))
        link = (node.findtext("link") or "").strip()
        date = to_date(node.findtext("pubDate") or node.findtext("date"))
        if not title or not link:
            continue
        items.append({"src": source, "title": title, "date": date, "url": link})
    return items


def sort_key(item):
    try:
        return datetime.strptime(item["date"], "%Y.%m.%d")
    except Exception:
        return datetime(1970, 1, 1)


def main():
    collected = []
    for source, url in FEEDS:
        try:
            collected.extend(parse(source, fetch(url)))
            print(f"[성공] {source} {url}")
        except Exception as err:
            print(f"[실패] {source} {url} -> {err}")

    seen, unique = set(), []
    for item in collected:
        if item["url"] in seen:
            continue
        seen.add(item["url"])
        unique.append(item)

    unique.sort(key=sort_key, reverse=True)
    unique = unique[:MAX_ITEMS]

    if not unique:
        print("수집된 항목이 없어 news.json 을 변경하지 않는다.")
        return

    data = {
        "updated": datetime.now(KST).strftime("%Y.%m.%d"),
        "items": unique,
    }
    with open("news.json", "w", encoding="utf-8") as fp:
        json.dump(data, fp, ensure_ascii=False, indent=2)
    print(f"{len(unique)}건 저장 완료")


if __name__ == "__main__":
    main()
