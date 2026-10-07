import requests
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime, timezone, timedelta
from email.utils import format_datetime, parsedate_to_datetime
from urllib.parse import urlencode
import hashlib


# --------------------------------------------------
# 設定
# --------------------------------------------------

TOURNAMENT = 106
REGION = "rt"

JSON_URL = (
    f"https://storage.googleapis.com/"
    f"mbs-rugby/{TOURNAMENT}/{REGION}/index.json"
)

TOPICS_BASE = "https://www.mbs.jp/rugby/topics/"

OUTPUT = Path(__file__).parent / "mbs_rugby.xml"

JST = timezone(timedelta(hours=9))

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/154.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ja-JP,ja;q=0.9,en;q=0.8",
}


# --------------------------------------------------
# 既存RSSを読み込む
# --------------------------------------------------

old_items = {}

if OUTPUT.exists():

    try:

        old_tree = ET.parse(OUTPUT)

        for item in old_tree.getroot().findall(
            "./channel/item"
        ):

            guid = item.findtext(
                "guid",
                ""
            )

            if guid:

                old_items[guid] = {
                    "title": item.findtext(
                        "title",
                        ""
                    ),
                    "link": item.findtext(
                        "link",
                        ""
                    ),
                    "description": item.findtext(
                        "description",
                        ""
                    ),
                    "pubDate": item.findtext(
                        "pubDate",
                        ""
                    ),
                    "guid": guid,
                }

    except Exception:

        old_items = {}


# --------------------------------------------------
# MBS JSON取得
# --------------------------------------------------

print("取得URL:")
print(JSON_URL)
print()

response = requests.get(
    JSON_URL,
    headers=HEADERS,
    timeout=30
)

print(
    "HTTP:",
    response.status_code
)

response.raise_for_status()

data = response.json()

print(
    "JSON取得件数:",
    len(data),
    "件"
)

print()


# --------------------------------------------------
# 記事取得
# --------------------------------------------------

current_items = []
seen = set()


for entry in data:

    article_id = str(
        entry.get(
            "id",
            ""
        )
    ).strip()

    title = str(
        entry.get(
            "title",
            ""
        )
    ).strip()

    time_text = str(
        entry.get(
            "time",
            ""
        )
    ).strip()


    if not article_id or not title:
        continue


    # --------------------------------------------------
    # 記事URL
    # --------------------------------------------------

    query = urlencode(
        {
            "tournament": TOURNAMENT,
            "r": REGION,
            "a": article_id,
        }
    )

    article_url = (
        TOPICS_BASE
        + "?"
        + query
    )


    # --------------------------------------------------
    # 重複防止
    # --------------------------------------------------

    guid = hashlib.sha256(
        article_url.encode("utf-8")
    ).hexdigest()

    if guid in seen:
        continue

    seen.add(guid)


    # --------------------------------------------------
    # 公開日時
    #
    # 例：
    # 20261007050413
    # ↓
    # 2026/10/07 05:04:13 JST
    # --------------------------------------------------

    try:

        dt = datetime.strptime(
            time_text,
            "%Y%m%d%H%M%S"
        )

        dt = dt.replace(
            tzinfo=JST
        )

        pub_date = format_datetime(
            dt
        )

    except Exception:

        print(
            "日時解析失敗:",
            time_text,
            title
        )

        continue


    # --------------------------------------------------
    # RSS用データ
    # --------------------------------------------------

    current_items.append(
        {
            "title": title,
            "link": article_url,
            "description": (
                "MBS 全国高校ラグビー "
                "「地区大会トピックス」"
            ),
            "pubDate": pub_date,
            "guid": guid,
        }
    )


# --------------------------------------------------
# 既存RSSと統合
# --------------------------------------------------

all_items = []
seen_guids = set()


for item in current_items:

    if item["guid"] not in seen_guids:

        all_items.append(item)
        seen_guids.add(item["guid"])


for guid, item in old_items.items():

    if guid not in seen_guids:

        all_items.append(item)
        seen_guids.add(guid)


# --------------------------------------------------
# 新しい順に並べる
# --------------------------------------------------

def get_date(item):

    try:

        return parsedate_to_datetime(
            item["pubDate"]
        )

    except Exception:

        return datetime.min.replace(
            tzinfo=timezone.utc
        )


all_items.sort(
    key=get_date,
    reverse=True
)

all_items = all_items[:300]


# --------------------------------------------------
# RSS作成
# --------------------------------------------------

rss = ET.Element(
    "rss",
    version="2.0"
)

channel = ET.SubElement(
    rss,
    "channel"
)


ET.SubElement(
    channel,
    "title"
).text = (
    "MBS 全国高校ラグビー "
    "地区大会トピックス"
)


ET.SubElement(
    channel,
    "link"
).text = (
    "https://www.mbs.jp/rugby/"
)


ET.SubElement(
    channel,
    "description"
).text = (
    "MBS 全国高校ラグビー "
    "「地区大会トピックス」の新着情報"
)


ET.SubElement(
    channel,
    "language"
).text = "ja"


# --------------------------------------------------
# RSS記事
# --------------------------------------------------

for item in all_items:

    element = ET.SubElement(
        channel,
        "item"
    )


    ET.SubElement(
        element,
        "title"
    ).text = item["title"]


    ET.SubElement(
        element,
        "link"
    ).text = item["link"]


    ET.SubElement(
        element,
        "description"
    ).text = item["description"]


    ET.SubElement(
        element,
        "pubDate"
    ).text = item["pubDate"]


    guid_element = ET.SubElement(
        element,
        "guid"
    )

    guid_element.set(
        "isPermaLink",
        "false"
    )

    guid_element.text = item["guid"]


# --------------------------------------------------
# XML保存
# --------------------------------------------------

tree = ET.ElementTree(rss)

ET.indent(
    tree,
    space="  "
)

tree.write(
    OUTPUT,
    encoding="utf-8",
    xml_declaration=True
)


# --------------------------------------------------
# 結果表示
# --------------------------------------------------

print("RSS作成成功")

print(
    "今回取得:",
    len(current_items),
    "件"
)

print(
    "RSS保存件数:",
    len(all_items),
    "件"
)

print(
    "保存先:",
    OUTPUT
)

print()
print("取得記事:")


for i, item in enumerate(
    current_items,
    start=1
):

    print()

    print(
        f"[{i}] {item['title']}"
    )

    print(
        "    ",
        item["pubDate"]
    )

    print(
        "    ",
        item["link"]
    )