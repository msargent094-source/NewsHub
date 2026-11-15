#!/usr/bin/env python3
"""Fetch source-filtered public Google News RSS results; no browser CORS dependency."""
import datetime as dt
import email.utils
import hashlib
import html
import json
import pathlib
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

SOURCES = {
    "ABC News": "abc.net.au",
    "SBS News": "sbs.com.au",
    "The Guardian Australia": "theguardian.com",
    "Reuters": "reuters.com",
    "BBC News": "bbc.com/news",
    "Al Jazeera": "aljazeera.com",
    "Associated Press": "apnews.com",
}
TOPICS = {
    "Australia": "Australia",
    "World": "world",
    "Politics": "politics",
    "Business": "business economy",
    "Technology": "technology",
    "Sport": "sport",
}
OUT = pathlib.Path("data/news.json")
GUARDIAN_RSS = "https://www.theguardian.com/au/rss"
MEDIA_NS = "{http://search.yahoo.com/mrss/}"
KEYWORDS = {
    "Sport": ("sport", "football", "cricket", "afl", "nrl", "tennis", "olympic", "soccer", "rugby", "jillaroos"),
    "Technology": ("technology", "artificial intelligence", "cyber", "software", "smartphone", "computer", "tech "),
    "Business": ("business", "economy", "inflation", "interest rate", "reserve bank", "market", "stocks", "finance"),
    "Politics": ("politic", "election", "parliament", "minister", "government", "senate", "president", "congress"),
}
def category_for(title, fallback):
    low = title.lower()
    for category, terms in KEYWORDS.items():
        if any(term in low for term in terms):
            return category
    return fallback

def image_for(item):
    for tag in (MEDIA_NS+"content", MEDIA_NS+"thumbnail", "enclosure"):
        for element in item.findall(tag):
            url = element.get("url", "")
            kind = element.get("type", "")
            if url.startswith("https://") and (tag != "enclosure" or kind.startswith("image/")):
                return url
    description = html.unescape(item.findtext("description") or "")
    for match in re.finditer(r'<img\\b[^>]*\\bsrc=["\\'](https://[^"\\']+)["\\']', description, re.I):
        candidate = html.unescape(match.group(1))
        host = urllib.parse.urlsplit(candidate).hostname or ""
        if host and not host.endswith("google.com") and not host.endswith("gstatic.com"):
            return candidate
    return None

def add_story(stories, item, name, category):
    title = (item.findtext("title") or "").strip()
    link = (item.findtext("link") or "").strip()
    if not title or not link:
        return False
    date = item.findtext("pubDate") or ""
    try:
        published = email.utils.parsedate_to_datetime(date).astimezone(dt.timezone.utc).isoformat()
    except (TypeError, ValueError):
        published = dt.datetime.now(dt.timezone.utc).isoformat()
    normalized = re.sub(r"[^a-z0-9]+", " ", re.sub(r"\s+[-|]\s+[^-|]{2,90}$", "", title.lower())).strip()
    ident = hashlib.sha256((name+"|"+normalized).encode()).hexdigest()[:20]
    entry = {"id":ident,"title":title,"url":link,"source":name,"category":category_for(title,category),"published":published}
    image = image_for(item)
    if image: entry["image"] = image
    stories.setdefault(ident,entry)
    return True
def fetch(url):
    req=urllib.request.Request(url,headers={"User-Agent":"NewsHub/1.0 (+https://github.com/msargent094-source/NewsHub)"})
    with urllib.request.urlopen(req,timeout=20) as response:
        return response.read()
def main():
    old=[]
    if OUT.exists():
        try: old=json.loads(OUT.read_text()).get("articles",[])
        except (ValueError,OSError): pass
    stories={}
    warnings=[]
    for name,domain in SOURCES.items():
        count=0
        for category,term in TOPICS.items():
            query=f"site:{domain} {term} when:7d"
            url="https://news.google.com/rss/search?"+urllib.parse.urlencode({"q":query,"hl":"en-AU","gl":"AU","ceid":"AU:en"})
            try:
                root=ET.fromstring(fetch(url))
                for item in root.findall(".//item")[:15]:
                    title=(item.findtext("title") or "").strip()
                    link=(item.findtext("link") or "").strip()
                    if not title or not link: continue
                    # Google News is a discovery feed, not a direct publisher RSS feed.
                    # Keep the original Google News link rather than guessing a destination.
                    source_text=(item.findtext("source") or "").lower()
                    if name=="ABC News" and not ("abc" in source_text or "australian broadcasting" in source_text):continue
                    if name=="SBS News" and "sbs" not in source_text:continue
                    if name=="Reuters" and "reuters" not in source_text:continue
                    if name=="BBC News" and "bbc" not in source_text:continue
                    if name=="Al Jazeera" and "al jazeera" not in source_text:continue
                    if name=="Associated Press" and not ("associated press" in source_text or source_text=="ap news"):continue
                    if name=="The Guardian Australia" and "guardian" not in source_text:continue
                    if add_story(stories,item,name,category): count+=1
            except Exception as exc:
                warnings.append(f"{name} / {category}: {type(exc).__name__}: {exc}")
        if name == "The Guardian Australia":
            try:
                root = ET.fromstring(fetch(GUARDIAN_RSS))
                for item in root.findall(".//item")[:80]:
                    if add_story(stories,item,name,"World"): count += 1
            except Exception as exc:
                warnings.append(f"Guardian RSS: {type(exc).__name__}: {exc}")
        if count==0: warnings.append(f"No current results for {name}")
    if not stories:
        for a in old:
            if a.get("id"): stories[a["id"]]=a
        warnings.append("No new results; retained last published articles")
    # Preserve previously discovered images for articles with stable IDs.
    previous = {a.get("id"): a for a in old}
    for ident, article in stories.items():
        if not article.get("image") and previous.get(ident, {}).get("image"):
            article["image"] = previous[ident]["image"]
    entries=sorted(stories.values(),key=lambda x:x["published"],reverse=True)[:600]
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps({"updatedAt":dt.datetime.now(dt.timezone.utc).isoformat(),"articles":entries,"warnings":warnings},ensure_ascii=False,indent=2)+"\n")
    print(f"Saved {len(entries)} articles; {len(warnings)} warnings")
if __name__=="__main__":main()
