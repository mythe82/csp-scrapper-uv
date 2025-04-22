import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import json
import time
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from sumy.summarizers.text_rank import TextRankSummarizer
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
import feedparser
from dotenv import load_dotenv
import os
import re
from deep_translator import GoogleTranslator
import matplotlib.pyplot as plt
import base64
from io import BytesIO
import numpy as np
import platform

# ---------- 환경변수 로딩 ----------
load_dotenv()

SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT"))
SENDER = os.getenv("SENDER")
SENDER_PASSWORD = os.getenv("EMAIL_PASSWORD")
RECEIVERS = os.getenv("RECEIVERS").split(",")

# ---------- 날짜 범위 ----------
today = datetime.today()
start_of_week = today - timedelta(days=today.weekday())
end_of_week = start_of_week + timedelta(days=6)

all_data = []
stop_scraping = False

# ---------- 공통 함수 ----------
def summarize_text(text, sentence_count=2, max_length=300):
    try:
        parser = PlaintextParser.from_string(text, Tokenizer("english"))
        summarizer = TextRankSummarizer()
        summary = summarizer(parser.document, sentence_count)
        summary_text = " ".join(str(sentence) for sentence in summary)
        summary_text = summary_text.strip()

        if len(summary_text) > max_length:
            summary_text = summary_text[:max_length].rstrip() + "..."

        return summary_text
    except Exception:
        return text


def summarize_long_text(text, max_chunks=5, max_length=150):
    try:
        chunks = re.split(r'\n|\.\s+', text)
        summaries = []
        for chunk in chunks:
            chunk = chunk.strip()
            if len(chunk) < 50:
                continue
            summary = summarize_text(chunk, sentence_count=1, max_length=max_length)
            summaries.append(summary)
            if len(summaries) >= max_chunks:
                break
        return " ".join(summaries)
    except Exception as e:
        print(f"❌ 긴 텍스트 요약 오류: {e}")
        return text


def translate_to_korean(text):
    try:
        return GoogleTranslator(source='en', target='ko').translate(text)
    except Exception as e:
        print(f"❌ 번역 오류: {e}")
        return text


def clean_aws_summary(summary_html):
    try:
        summary_text = BeautifulSoup(summary_html, "html.parser").get_text(separator=" ").strip()
        summary_text = re.sub(r"\s+", " ", summary_text)
        summary_text = re.sub(r"https?://\S+", "", summary_text)
        summary_text = re.sub(r"자세히 보기", "", summary_text, flags=re.IGNORECASE)

        phrases_to_remove = [
            r"이 새로운 기능은.*?사용할 수 있습니다\.",
            r"자세한 내용은.*?참고하세요\.",
            r"고객은.*?사용할 수 있습니다\.",
        ]
        for phrase in phrases_to_remove:
            summary_text = re.sub(phrase, "", summary_text)

        return summary_text.strip()
    except Exception as e:
        print(f"❌ AWS 요약 클렌징 오류: {e}")
        return summary_html


def clean_gcp_summary(summary_html):
    try:
        summary_text = BeautifulSoup(summary_html, "html.parser").get_text(separator=" ").strip()
        summary_text = re.sub(r"\s+", " ", summary_text)
        summary_text = re.sub(r"https?://\S+", "", summary_text)
        summary_text = re.sub(r"자세히 보기|Learn more", "", summary_text, flags=re.IGNORECASE)
        return summary_text.strip()
    except Exception as e:
        print(f"❌ GCP 요약 클렌징 오류: {e}")
        return summary_html

# ---------- 배너 Base64 ----------
def get_banner_base64():
    banner_path = "banner.png"  # 배너 이미지 파일명
    with open(banner_path, "rb") as f:
        img_base64 = base64.b64encode(f.read()).decode("utf-8")
    return f"data:image/png;base64,{img_base64}"

# ---------- 폰트 자동 설정 ----------
def set_korean_font():
    system = platform.system()
    if system == "Windows":
        plt.rc('font', family='Malgun Gothic')
    elif system == "Darwin":
        plt.rc('font', family='Apple SD Gothic Neo')
    else:
        plt.rc('font', family='NanumGothic')
    plt.rcParams['axes.unicode_minus'] = False

# ---------- Azure 크롤러 ----------
def crawl_azure_updates():
    global all_data, stop_scraping
    print("🚀 [Azure] 업데이트 수집 시작")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            base_url = "https://azure.microsoft.com/en-us/updates?filters=%5B%22Launched%22%5D"
            try:
                page.goto(base_url, timeout=10000)
            except Exception as e:
                print(f"❌ [Azure] 페이지 로딩 실패: {e}")
                return

            page.wait_for_timeout(3000)

            pagination_items = page.query_selector_all("ul#pagination li")
            last_page_num = 1
            for item in pagination_items:
                text = item.inner_text().strip()
                if text.isdigit():
                    last_page_num = max(last_page_num, int(text))

            current_page = 1
            while current_page <= last_page_num:
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(2)

                html = page.content()
                soup = BeautifulSoup(html, "html.parser")
                items = soup.select("li.ocr-faq-item.accordion_bg")

                for item in items:
                    try:
                        title_elem = item.select_one("h2.lead")
                        title = title_elem.get_text(strip=True) if title_elem else ""

                        content_elem = item.select_one("div.accordion-item.col-xl-8")
                        content = content_elem.get_text(strip=True).replace("\n", " ") if content_elem else ""

                        date_elem = (
                            item.select_one("div.updated_dates div.modified_date span")
                            or item.select_one("div.updated_dates div.created_date span")
                        )
                        date_text = date_elem.get_text(strip=True) if date_elem else ""
                        post_date = datetime.strptime(date_text, "%m/%d/%Y") if date_text else None

                        rss_link_elem = item.select_one('a[data-bi-cn="Accordion detail - Share RSS"]')
                        rss_link = rss_link_elem["href"] if rss_link_elem else ""

                        post_id = ""
                        if rss_link:
                            post_id = rss_link.split("/")[-1]

                        post_link = f"https://azure.microsoft.com/updates?id={post_id}" if post_id else ""

                        if post_date:
                            if start_of_week.date() <= post_date.date() <= end_of_week.date():
                                summary_en = summarize_text(content, sentence_count=2, max_length=300)
                                summary_ko = translate_to_korean(summary_en)

                                all_data.append({
                                    "source": "Azure",
                                    "title": title,
                                    "date": date_text,
                                    "content": content,
                                    "link": post_link,
                                    "summary": summary_ko
                                })
                            else:
                                stop_scraping = True
                                break

                    except Exception as e:
                        print(f"❌ [Azure] {current_page}페이지 항목 파싱 오류: {e}")

                if stop_scraping:
                    break

                next_page_num = current_page + 1
                if next_page_num > last_page_num:
                    break

                try:
                    next_li = page.query_selector(f'ul#pagination li:text-is("{next_page_num}")')
                    if next_li:
                        next_li.click()
                        page.wait_for_selector(f'ul#pagination li.active:text-is("{next_page_num}")', timeout=5000)
                        current_page += 1
                    else:
                        break
                except Exception:
                    break

        finally:
            browser.close()
    azure_count = len([d for d in all_data if d["source"] == "Azure"])
    print(f"📄 [Azure] 업데이트 수집 완료 - {azure_count}건")

# ---------- AWS 크롤러 ----------
def crawl_aws_updates():
    global all_data
    print("🚀 [AWS] 업데이트 수집 시작")
    feed_url = "https://aws.amazon.com/new/feed/"
    feed = feedparser.parse(feed_url)
    for entry in feed.entries:
        try:
            title = entry.title
            link = entry.link
            date_parsed = entry.published_parsed
            post_date = datetime(*date_parsed[:6])
            if start_of_week.date() <= post_date.date() <= end_of_week.date():
                cleaned_summary = clean_aws_summary(entry.summary)
                summary_en = summarize_text(cleaned_summary, sentence_count=1, max_length=150)
                summary_ko = translate_to_korean(summary_en)

                all_data.append({
                    "source": "AWS",
                    "title": title,
                    "date": post_date.strftime("%Y-%m-%d"),
                    "content": cleaned_summary,
                    "link": link,
                    "summary": summary_ko
                })
        except Exception as e:
            print(f"❌ [AWS] RSS 항목 파싱 오류: {e}")
    aws_count = len([d for d in all_data if d["source"] == "AWS"])
    print(f"📄 [AWS] 업데이트 수집 완료 - {aws_count}건")

# ---------- GCP 크롤러 ----------
def crawl_gcp_updates():
    global all_data
    print("🚀 [GCP] 업데이트 수집 시작")
    rss_url = "https://cloud.google.com/feeds/gcp-release-notes.xml"
    feed = feedparser.parse(rss_url)

    service_pattern = re.compile(r"([A-Z][a-zA-Z0-9\s\-\(\)]+)\s+(Feature|Announcement)\s+", re.MULTILINE)

    for entry in feed.entries:
        try:
            title = entry.title
            date_text = entry.get('published') or entry.get('updated')
            if not date_text:
                continue

            try:
                post_date = datetime.strptime(date_text, "%a, %d %b %Y %H:%M:%S %Z")
            except ValueError:
                post_date = datetime.strptime(date_text[:16], "%Y-%m-%dT%H:%M")

            if not (start_of_week.date() <= post_date.date() <= end_of_week.date()):
                continue

            raw_content = clean_gcp_summary(entry.summary)
            matches = list(service_pattern.finditer(raw_content))
            if not matches:
                continue

            for i, match in enumerate(matches):
                service_name = match.group(1).strip()
                category = match.group(2).strip()
                start_idx = match.end()
                end_idx = matches[i + 1].start() if i + 1 < len(matches) else len(raw_content)
                content = raw_content[start_idx:end_idx].strip()

                if not content:
                    continue

                if "Security" in service_name or "CVE-" in content:
                    continue

                summary_en = summarize_long_text(content, max_chunks=3, max_length=150)
                summary_ko = translate_to_korean(summary_en)

                all_data.append({
                    "source": "GCP",
                    "title": f"{service_name} ({category})",
                    "date": post_date.strftime("%Y-%m-%d"),
                    "content": content,
                    "link": "https://cloud.google.com/release-notes",
                    "summary": summary_ko
                })

        except Exception as e:
            print(f"❌ [GCP] RSS 항목 파싱 오류: {e}")

    gcp_count = len([d for d in all_data if d["source"] == "GCP"])
    print(f"📄 [GCP] 업데이트 수집 완료 - {gcp_count}건")

# ---------- 파이차트 생성 ----------
def generate_summary_chart():
    set_korean_font()

    counts = {
        "Azure": len([d for d in all_data if d["source"] == "Azure"]),
        "AWS": len([d for d in all_data if d["source"] == "AWS"]),
        "GCP": len([d for d in all_data if d["source"] == "GCP"]),
    }

    total = sum(counts.values())

    def make_label(name, count):
        percent = (count / total) * 100 if total else 0
        return f"{name}\n{count}건 ({percent:.1f}%)"

    labels = [make_label(name, count) for name, count in counts.items()]

    fig, ax = plt.subplots(figsize=(6, 6))
    wedges, texts = ax.pie(counts.values(), startangle=90)

    bbox_props = dict(boxstyle="round,pad=0.3", fc="white", ec="gray", lw=0.5)
    kw = dict(arrowprops=dict(arrowstyle="-"), bbox=bbox_props, zorder=0, va="center")

    for i, p in enumerate(wedges):
        ang = (p.theta2 - p.theta1) / 2. + p.theta1
        y = np.sin(np.deg2rad(ang))
        x = np.cos(np.deg2rad(ang))
        horizontalalignment = {-1: "right", 1: "left"}[int(np.sign(x))]
        ax.annotate(labels[i], xy=(x, y), xytext=(1.2 * np.sign(x), 1.2 * y),
                    horizontalalignment=horizontalalignment, **kw)

    ax.set_title(f"이번 주 Cloud 업데이트 요약", fontsize=14)

    buf = BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode("utf-8")
    return f"data:image/png;base64,{img_base64}"

# ---------- 파일 저장 ----------
def save_files():
    os.makedirs("output", exist_ok=True)
    json_filename = f"output/cloud_updates_week_{today.strftime('%Y-%m-%d')}.json"
    with open(json_filename, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 업데이트 데이터 저장 완료: {json_filename}")
    return json_filename

# ---------- 이메일 발송 ----------
def send_email():
    if not all_data:
        print("ℹ️ 이번 주 업데이트가 없습니다. 메일 발송하지 않음.")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[Cloud Updates] 이번 주 소식지 ({today.strftime('%Y-%m-%d')})"
    msg["From"] = SENDER
    msg["To"] = ", ".join(RECEIVERS)

    banner_base64 = get_banner_base64()
    chart_base64 = generate_summary_chart()

    html_content = f"""
    <h2>📢 클라우드 주간 업데이트 ({today.strftime('%Y-%m-%d')})</h2>
    <img src="{banner_base64}" alt="배너" style="width: 100%; max-width: 800px; margin-bottom: 20px;">
    <img src="{chart_base64}" alt="Cloud Update Summary Chart" style="max-width: 600px; margin-bottom: 20px;">
    """

    for provider in ["Azure", "AWS", "GCP"]:
        provider_items = [item for item in all_data if item["source"] == provider]
        if provider_items:
            icon = "🔷" if provider == "Azure" else ("🟧" if provider == "AWS" else "🟩")
            html_content += f"<h3>{icon} {provider} 업데이트</h3><ul>"
            for item in provider_items:
                extra_note = f" (날짜: {item['date']})" if provider == "GCP" else ""
                html_content += (
                    f"<li style='margin-bottom: 20px;'>"
                    f"<strong>{item['date']}</strong> - <strong>{item['title']}</strong><br>"
                    f"{item['summary']} <a href='{item['link']}' style='color: blue;'>자세히 보기{extra_note}</a></li>"
                )
            html_content += "</ul>"

    msg.attach(MIMEText(html_content, "html"))
    send_with_retry(msg)

# ---------- 메일 재시도 ----------
def send_with_retry(msg, retries=3):
    for attempt in range(retries):
        try:
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(SENDER, SENDER_PASSWORD)
                server.sendmail(SENDER, RECEIVERS, msg.as_string())
            print("✅ 뉴스레터 메일 발송 완료")
            return
        except Exception as e:
            print(f"❌ 메일 발송 실패 (시도 {attempt+1}): {e}")
            time.sleep(3)
    print("❗️ 모든 메일 발송 재시도 실패")

# ---------- 실행 ----------
if __name__ == "__main__":
    crawl_azure_updates()
    crawl_gcp_updates()
    crawl_aws_updates()
    save_files()
    send_email()
