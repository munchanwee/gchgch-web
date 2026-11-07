#!/usr/bin/env python3
"""gchgch 정적 사이트 생성기

data/works.json 을 원본으로 _site/ 에 배포용 사이트를 만든다.
- work/<slug>/index.html : 작업마다 본문이 HTML에 바로 들어 있는 정적 페이지
- index.html             : 작업 카드 목록을 미리 넣는다 (자바스크립트가 같은 모양으로 다시 그린다)
- index.html, about.html : 구조화 데이터(JSON-LD)를 넣는다
- work.html              : 옛 주소(work.html?id=slug)를 새 주소로 보낸다
- sitemap.xml(페이지마다 git 기록으로 수정일 lastmod 자동 계산), robots.txt, llms.txt
- 404.html : 없는 주소일 때 보여 줄 한글 안내 페이지 (작업 목록 링크 포함)

GitHub Actions(.github/workflows/pages.yml)가 main 에 푸시될 때마다 실행한다.
로컬 확인: python tools/build.py  →  python -m http.server -d _site 8127
초안 미리보기: python tools/build.py --draft tools/overview_draft.json
표준 라이브러리만 쓴다.
"""
import html
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "_site")
SITE = "https://gchgch.com"
COPY = ["assets", "css", "js", "images", "data", "index.html", "about.html", "works.html", "CNAME"]
CATS = {"brand": "Brand", "graphic": "Graphic", "digital": "Digital", "space": "Space"}
ORG_ID = SITE + "/#org"
SITE_ID = SITE + "/#website"

COMPANY = {
    "name": "그치그치",
    "name_en": "GCHGCH STUDIO",
    "ceo": "박하연",
    "brn": "356-59-00920",
    "industry": "전문, 과학 및 기술 서비스업",
    "region": "전남광주통합특별시",
    "locality": "동구",
    "street": "동계천로 84 1층",
    "email": "gchgchstudio@gmail.com",
    "phone": "010-9625-4310",
    "phone_intl": "+82-10-9625-4310",
    "instagram": "https://www.instagram.com/gchgchstudio/",
    "disabled_no": "제0014-2026-03868호",
    "disabled_from": "2026-10-27",
    "disabled_to": "2029-10-26",
    "disabled_law": "장애인기업활동 촉진법 제18조의2 제2항",
    "disabled_check": "https://www.smpp.go.kr",
}
ADDRESS = f"{COMPANY['region']} {COMPANY['locality']} {COMPANY['street']}"
DISABLED_LINE = (f"그치그치(GCHGCH STUDIO)는 중소벤처기업부 장애인기업 확인({COMPANY['disabled_no']}, "
                 f"유효기간 {COMPANY['disabled_from']}~{COMPANY['disabled_to']})을 받은 디자인 스튜디오입니다.")
SERVICES = ["브랜드 기획", "네이밍", "브랜드 아이덴티티(BI)", "기업·기관 아이덴티티(CI)", "CI 매뉴얼",
            "패키지 디자인", "시각·광고 디자인", "웹·디지털 디자인", "공간·인테리어 디자인"]
DESCRIPTION = ("그치그치(GCHGCH STUDIO)는 전남광주통합특별시 동구의 디자인 스튜디오입니다. "
               "브랜드 기획, 네이밍, BI·CI 아이덴티티, 패키지·시각 디자인, 웹 디자인을 합니다. "
               "중소벤처기업부 확인 장애인기업입니다.")
AI_BOTS = ["GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "Claude-SearchBot", "Claude-User",
           "anthropic-ai", "PerplexityBot", "Perplexity-User", "Google-Extended", "Googlebot", "Bingbot",
           "Yeti", "Applebot", "Applebot-Extended", "DuckDuckBot", "Daumoa"]


def esc(s):
    return html.escape("" if s is None else str(s), quote=True)


def text_of(s):
    """HTML 조각에서 글자만 남긴다 (설명문, llms.txt용)"""
    import re
    s = re.sub(r"<li>", " · ", s or "")
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip(" ·")


def absu(path):
    return path if path.startswith("http") else SITE + "/" + path.lstrip("/")


def client_name(w):
    return (w.get("client") or "").split(" (")[0].strip()


def jsonld(obj):
    return ('<script type="application/ld+json">' +
            json.dumps(obj, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/") +
            "</script>")


def org_ld():
    return {
        "@type": "ProfessionalService",
        "@id": ORG_ID,
        "name": COMPANY["name"],
        "alternateName": [COMPANY["name_en"], "gchgch", "그치그치 스튜디오"],
        "legalName": COMPANY["name"],
        "url": SITE + "/",
        "logo": absu("assets/favicon.png"),
        "image": absu("assets/og.png"),
        "description": DESCRIPTION,
        "email": COMPANY["email"],
        "telephone": COMPANY["phone_intl"],
        "taxID": COMPANY["brn"],
        "founder": {"@type": "Person", "name": COMPANY["ceo"], "jobTitle": "대표"},
        "address": {"@type": "PostalAddress", "streetAddress": COMPANY["street"],
                    "addressLocality": COMPANY["locality"], "addressRegion": COMPANY["region"],
                    "addressCountry": "KR"},
        "areaServed": {"@type": "Country", "name": "대한민국"},
        "knowsAbout": SERVICES,
        "sameAs": [COMPANY["instagram"]],
        "hasCredential": {
            "@type": "EducationalOccupationalCredential",
            "name": "장애인기업 확인서",
            "credentialCategory": "장애인기업 확인",
            "identifier": COMPANY["disabled_no"],
            "dateCreated": COMPANY["disabled_from"],
            "expires": COMPANY["disabled_to"],
            "description": f"{COMPANY['disabled_law']}에 따른 장애인기업 확인. 진위 확인: 공공구매 종합정보망",
            "recognizedBy": {"@type": "GovernmentOrganization", "name": "중소벤처기업부"},
            "url": COMPANY["disabled_check"],
        },
    }


def website_ld():
    return {"@type": "WebSite", "@id": SITE_ID, "url": SITE + "/", "name": "그치그치 GCHGCH STUDIO",
            "inLanguage": "ko", "publisher": {"@id": ORG_ID}}


def load_works(draft=None):
    with open(os.path.join(ROOT, "data", "works.json"), encoding="utf-8") as f:
        data = json.load(f)
    works = data if isinstance(data, list) else data.get("works", [])
    works = [w for w in works if w and w.get("published") is not False and w.get("slug")]
    works.sort(key=lambda w: w.get("date") or "", reverse=True)
    if draft:
        with open(draft, encoding="utf-8") as f:
            extra = json.load(f)
        for w in works:
            if w["slug"] in extra:
                w["body"] = extra[w["slug"]] + (w.get("body") or "")
    return works


# ---------- 화면 조각: js/works.js 와 같은 마크업을 만든다 ----------

def wide_flags(n):
    rows, left, two = [], n, True
    while left > 0:
        k = min(2 if two else 3, left)
        rows.append(k)
        left -= k
        two = not two
    if len(rows) > 1 and rows[-1] == 1:
        rows.pop()
        if rows[-1] == 3:
            rows[-1] = 2
            rows.append(2)
        else:
            rows[-1] += 1
    flags, side = [], 0
    for k in rows:
        for j in range(k):
            flags.append(j == side if k == 2 else k == 1)
        if k == 2:
            side = 1 - side
    return flags


def card_img(src, alt, cls):
    if src:
        return f'<img src="/{esc(src.lstrip("/"))}" alt="{esc(alt)}" loading="lazy">'
    return f'<div class="ph {cls} mono">Image</div>'


def grid_html(works):
    out = []
    for i, (w, wide) in enumerate(zip(works, wide_flags(len(works)))):
        out.append(
            f'<a href="/work/{esc(w["slug"])}/" class="card{" card--w" if wide else ""} is-in">'
            f'<div class="card__img">{card_img(w.get("cover"), w["title"], "ph--o" if i % 3 == 0 else "")}</div>'
            f'<div class="card__meta"><h3 class="card__t">{esc(w["title"])}</h3>'
            f'<span class="mono card__c">{esc(w.get("type") or CATS.get(w.get("category"), ""))}</span></div></a>')
    return "".join(out)


def para(b):
    if b.get("li"):
        return "<ul>" + "".join(f"<li>{esc(x)}</li>" for x in b["li"]) + "</ul>"
    return f"<p>{esc(b.get('p'))}</p>"


def src_of(s):
    return "/" + (s or "").lstrip("/")


def block_alts(w):
    """블록 이미지의 alt. 데이터에 alt가 있으면 그것을, 없으면 작업명과 가까운 단락 제목으로 만든다."""
    title, head, n, alts = w["title"], "", 0, []
    for b in w["blocks"]:
        if b.get("h"):
            head = b["h"]
        if b.get("t") in ("img", "side"):
            n += 1
            alts.append([b.get("alt") or (f"{title} {head}" if head else f"{title} 대표 이미지")])
        elif b.get("t") == "pair":
            alts.append([b.get("alt_a") or f"{title} {head or '작업'} 이미지 1",
                         b.get("alt_b") or f"{title} {head or '작업'} 이미지 2"])
        else:
            alts.append([])
    return alts


def blocks_html(w):
    out = []
    if w.get("body"):
        out.append(f'<div class="wb__text"><h2>개요</h2>{w["body"]}</div>')
    for b, alt in zip(w["blocks"], block_alts(w)):
        t = b.get("t")
        if t == "img":
            cls = f'wb__img wb--{esc(b.get("size") or "wide")}' + (f' wb--{esc(b["align"])}' if b.get("align") else "")
            out.append(f'<figure class="{cls}"><img src="{esc(src_of(b.get("src")))}" alt="{esc(alt[0])}" loading="lazy"></figure>')
        elif t == "text":
            out.append('<div class="wb__text">' + (f'<h2>{esc(b["h"])}</h2>' if b.get("h") else "") + para(b) + "</div>")
        elif t == "quote":
            out.append(f'<p class="wb__quote">{esc(b.get("p"))}</p>')
        elif t == "pair":
            out.append(f'<div class="wb__pair" style="grid-template-columns:{esc(b.get("ratio") or "1fr 1fr")}">'
                       f'<img src="{esc(src_of(b.get("a")))}" alt="{esc(alt[0])}" loading="lazy">'
                       f'<img src="{esc(src_of(b.get("b")))}" alt="{esc(alt[1])}" loading="lazy"></div>')
        elif t == "side":
            out.append(f'<div class="wb__side"><img src="{esc(src_of(b.get("src")))}" alt="{esc(alt[0])}" loading="lazy">'
                       '<div class="wb__text wb__text--in">' + (f'<h2>{esc(b["h"])}</h2>' if b.get("h") else "") + para(b) + "</div></div>")
    return '<div class="wb">' + "".join(out) + "</div>"


def detail_html(w, nxt):
    meta = (f'<dl class="wd__meta">'
            f'<div><dt class="mono">Client</dt><dd>{esc(w.get("client") or "—")}</dd></div>'
            f'<div><dt class="mono">Category</dt><dd>{esc(CATS.get(w.get("category"), "—"))}</dd></div>'
            f'<div><dt class="mono">Scope</dt><dd>{esc(w.get("type") or "—")}</dd></div></dl>')
    h = '<a href="/" class="wd__back mono">← Works</a>' + f'<h1 class="wd__title">{esc(w["title"])}</h1>' + meta
    if w.get("blocks"):
        h += f'<p class="wd__lead">{esc(w.get("summary"))}</p>' + blocks_html(w)
        if w.get("note"):
            h += f'<p class="wd__note mono">{esc(w["note"])}</p>'
    else:
        gal = [s for s in (w.get("gallery") or []) if s]
        wide = w.get("gallery_wide") or []
        h += f'<div class="wd__cover">{card_img(w.get("cover"), w["title"] + " 대표 이미지", "ph--o")}</div>'
        h += ('<div class="wd__body"><span class="mono" style="color:var(--orange)">Process</span><div>' +
              (f'<p class="wd__summary">{esc(w["summary"])}</p>' if w.get("summary") else "") +
              f'<div class="wd__text">{w.get("body") or ""}</div></div></div>')
        if gal:
            wide_cls = ' class="is-wide"'
            h += '<div class="wd__gallery">' + "".join(
                f'<img{wide_cls if s in wide else ""} src="{esc(src_of(s))}" alt="{esc(w["title"])} 작업 이미지 {i}" loading="lazy">'
                for i, s in enumerate(gal, 1)) + "</div>"
    if nxt and nxt is not w:
        h += (f'<div class="wd__next"><span class="mono">Next</span>'
              f'<a href="/work/{esc(nxt["slug"])}/">{esc(nxt["title"])} →</a></div>')
    return h


def work_images(w):
    srcs = [w.get("cover")] + [b.get(k) for b in (w.get("blocks") or []) for k in ("src", "a", "b")] + (w.get("gallery") or [])
    seen = []
    for s in srcs:
        if s and absu(s) not in seen:
            seen.append(absu(s))
    return seen[:12]


HEADER = """<header class="hd" id="hd">
  <div class="wrap hd__in">
    <a href="/" class="hd__logo" aria-label="gchgch 홈">
      <img class="lg-o" src="/assets/gchgch-oneline-orange.svg" alt="gchgch">
      <img class="lg-w" src="/assets/gchgch-oneline-white.svg" alt="">
    </a>
    <nav class="nav" id="nav">
      <a href="/" class="is-on">Works</a>
      <a href="/about.html">About</a>
    </nav>
    <button class="burger" id="burger" aria-label="메뉴 열기"><span></span><span></span></button>
  </div>
</header>"""

TAIL = """<section class="contact" style="padding-top:clamp(72px,8vw,120px)">
  <div class="wrap">
    <h2 class="contact__q">같이 물어봐요.</h2>
    <div class="contact__row" style="margin-top:32px">
      <p class="contact__p">답을 정해 오지 않아도 괜찮습니다.</p>
      <div class="contact__links"><a href="mailto:gchgchstudio@gmail.com">gchgchstudio@gmail.com <span>↗</span></a><a href="https://www.instagram.com/gchgchstudio/" target="_blank" rel="noopener">@gchgchstudio <span>↗</span></a></div>
    </div>
  </div>
</section>
</main>

<footer class="ftm">
  <div class="wrap ftm__in">
    <span>© 2026 gchgch</span>
    <span class="ftm__links"><a href="mailto:gchgchstudio@gmail.com">gchgchstudio@gmail.com</a><a href="https://www.instagram.com/gchgchstudio/" target="_blank" rel="noopener">Instagram</a></span>
  </div>
</footer>

<script src="/js/main.js"></script>
</body>
</html>
"""


DESC_MAX = 80  # 네이버 서치어드바이저 권장 길이


def page_desc(summary, cname, loc):
    """작업 페이지 설명문. 80자를 넘으면 덜 중요한 것부터 뺀다."""
    summary = summary.rstrip(".")
    for parts in ([summary, f"{cname}({loc})" if loc else cname, "그치그치(GCHGCH STUDIO) 작업"],
                  [summary, cname, "그치그치 작업"],
                  [summary, "그치그치 작업"],
                  [summary]):
        text = ". ".join(p for p in parts if p) + "."
        if len(text) <= DESC_MAX:
            return text
    return summary[:DESC_MAX - 1] + "…"


def work_page(w, nxt):
    url = f"{SITE}/work/{w['slug']}/"
    cname, loc, scope = client_name(w), w.get("location") or "", w.get("type") or ""
    title = f"{w['title']} — {w.get('summary') or scope} | 그치그치 GCHGCH STUDIO"
    desc = page_desc(w.get("summary") or scope, cname, loc)
    image = absu(w["cover"]) if w.get("cover") else absu("assets/og.png")
    creative = {
        "@type": "CreativeWork", "@id": url + "#work", "name": w["title"], "headline": w.get("summary"),
        "description": text_of(w.get("body")) or desc, "url": url, "inLanguage": "ko",
        "genre": scope, "keywords": [k.strip() for k in scope.split("·") if k.strip()] + [CATS.get(w.get("category"), "")],
        "image": work_images(w),
        "creator": {"@id": ORG_ID}, "publisher": {"@id": ORG_ID}, "isPartOf": {"@id": SITE_ID},
        "sponsor": {"@type": "Organization", "name": cname},
    }
    if loc:
        creative["locationCreated"] = {"@type": "Place", "name": loc}
    crumbs = {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "그치그치", "item": SITE + "/"},
        {"@type": "ListItem", "position": 2, "name": w["title"], "item": url}]}
    ld = jsonld({"@context": "https://schema.org", "@graph": [org_ld(), website_ld(), creative, crumbs]})
    head = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="그치그치 GCHGCH STUDIO">
<meta property="og:locale" content="ko_KR">
<meta property="og:url" content="{url}">
<meta property="og:title" content="{esc(w['title'])} — 그치그치">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:image" content="{esc(image)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#FFFFFF">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<link rel="alternate icon" href="/assets/favicon.png">
<link rel="preconnect" href="https://cdn.jsdelivr.net">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">
<link rel="stylesheet" href="/css/style.css">
{ld}
</head>
<body>

{HEADER}

<main>
<article class="wrap wd" id="wd" data-screen-label="Work Detail" data-static="1">{detail_html(w, nxt)}</article>
"""
    return head + TAIL


def not_found_page(works):
    links = "".join(f'<li><a href="/work/{esc(w["slug"])}/">{esc(w["title"])}</a></li>' for w in works)
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>페이지를 찾을 수 없습니다 — 그치그치 GCHGCH STUDIO</title>
<meta name="robots" content="noindex, follow">
<meta name="theme-color" content="#FFFFFF">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<link rel="alternate icon" href="/assets/favicon.png">
<link rel="preconnect" href="https://cdn.jsdelivr.net">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">
<link rel="stylesheet" href="/css/style.css">
</head>
<body>

{HEADER}

<main>
<article class="wrap wd" id="wd" data-static="1">
<a href="/" class="wd__back mono">← Works</a>
<h1 class="wd__title">404</h1>
<div class="wd__text">
<h2>찾는 페이지가 없습니다.</h2>
<p>주소가 바뀌었거나 없어진 페이지입니다. 작업 목록이나 회사 소개에서 다시 찾아 주세요.</p>
<p><a href="/">작업 목록 보기 →</a><br><a href="/about.html">회사 소개 보기 →</a></p>
<h2>작업</h2>
<ul>{links}</ul>
</div>
</article>
"""  + TAIL


def redirect_page(works):
    links = "".join(f'<li><a href="/work/{esc(w["slug"])}/">{esc(w["title"])}</a></li>' for w in works)
    slugs = json.dumps([w["slug"] for w in works])
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>작업 — 그치그치 GCHGCH STUDIO</title>
<meta name="robots" content="noindex, follow">
<link rel="canonical" href="{SITE}/">
<script>(function(){{var s={slugs};var id=new URLSearchParams(location.search).get('id');location.replace(id&&s.indexOf(id)>-1?'/work/'+id+'/':'/');}})();</script>
</head>
<body>
<p>작업 페이지 주소가 바뀌었습니다. <a href="/">그치그치 작업 목록</a>으로 이동합니다.</p>
<ul>{links}</ul>
</body>
</html>
"""


def git(*args):
    try:
        r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    except OSError:
        return ""
    return r.stdout if r.returncode == 0 else ""


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def file_lastmod(*paths):
    """파일들이 마지막으로 커밋된 시각. 커밋 안 된 수정이 있으면 지금 시각."""
    if git("status", "--porcelain", "--", *paths).strip():
        return now_iso()
    return git("log", "-1", "--format=%cI", "--", *paths).strip() or None


def work_lastmods(works):
    """작업마다 works.json 안의 자기 내용이 마지막으로 바뀐 커밋 시각을 찾는다.
    한 작업만 고쳐도 다른 작업의 수정일은 그대로 남는다."""
    def key(w):
        return json.dumps(w, ensure_ascii=False, sort_keys=True)

    def by_slug(text):
        try:
            data = json.loads(text)
        except ValueError:
            return {}
        return {w.get("slug"): key(w) for w in (data if isinstance(data, list) else data.get("works", []))}

    cur = {w["slug"]: key(w) for w in works}
    out = {}
    log = [l.split(" ", 1) for l in git("log", "--format=%H %cI", "--", "data/works.json").splitlines() if " " in l]
    if not log:
        return out
    pending = set(cur)
    head = by_slug(git("show", "HEAD:data/works.json"))
    for slug in list(pending):
        if head.get(slug) != cur[slug]:  # 아직 커밋 안 된 수정
            out[slug] = now_iso()
            pending.discard(slug)
    for sha, date in log:
        if not pending:
            break
        snap = by_slug(git("show", f"{sha}:data/works.json"))
        for slug in list(pending):
            if snap.get(slug) == cur[slug]:
                out[slug] = date  # 더 오래된 커밋에서도 같으면 다음 차례에 덮어쓴다
            else:
                pending.discard(slug)
    return out


def sitemap(works):
    mods = work_lastmods(works)
    work_dates = [d for d in mods.values() if d]
    home = max([d for d in [file_lastmod("index.html")] + work_dates if d], default=None,
               key=lambda d: datetime.fromisoformat(d))
    pages = [(SITE + "/", home), (SITE + "/about.html", file_lastmod("about.html"))] + \
            [(f"{SITE}/work/{w['slug']}/", mods.get(w["slug"])) for w in works]
    body = "".join(f"  <url><loc>{u}</loc>" + (f"<lastmod>{d}</lastmod>" if d else "") + "</url>\n" for u, d in pages)
    return '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + body + "</urlset>\n"


def robots():
    groups = "".join(f"User-agent: {b}\nAllow: /\n\n" for b in AI_BOTS)
    return f"User-agent: *\nAllow: /\n\n{groups}Sitemap: {SITE}/sitemap.xml\n"


def llms(works):
    lines = [
        "# 그치그치 GCHGCH STUDIO",
        "",
        f"> {DESCRIPTION}",
        "",
        "## 회사 정보",
        "",
        f"- 상호: {COMPANY['name']} {COMPANY['name_en']}",
        f"- 대표: {COMPANY['ceo']}",
        f"- 사업자등록번호: {COMPANY['brn']}",
        f"- 업종: {COMPANY['industry']}",
        f"- 주소: {ADDRESS}",
        f"- 장애인기업: 중소벤처기업부 장애인기업 확인 {COMPANY['disabled_no']} "
        f"(유효기간 {COMPANY['disabled_from']} ~ {COMPANY['disabled_to']}, 근거 {COMPANY['disabled_law']}, "
        f"진위 확인 공공구매 종합정보망 {COMPANY['disabled_check']})",
        f"- 문의: {COMPANY['email']}, {COMPANY['phone']}",
        f"- 웹사이트: {SITE}/",
        f"- 회사 소개: {SITE}/about.html",
        "",
        "## 하는 일",
        "",
        "- " + ", ".join(SERVICES),
        "",
        "## 작업",
        "",
    ]
    for w in works:
        bits = [w.get("summary") or "", f"고객: {client_name(w)}"]
        if w.get("location"):
            bits.append(f"지역: {w['location']}")
        if w.get("type"):
            bits.append(f"범위: {w['type']}")
        lines.append(f"- [{w['title']}]({SITE}/work/{w['slug']}/): " + ". ".join(b for b in bits if b))
    return "\n".join(lines) + "\n"


def inject(path, marker, content):
    with open(path, encoding="utf-8") as f:
        src = f.read()
    tag = f"<!-- build:{marker} -->"
    if tag not in src:
        raise SystemExit(f"{os.path.basename(path)}에 {tag} 자리가 없습니다")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(src.replace(tag, content))


def main():
    draft = None
    if "--draft" in sys.argv:
        draft = os.path.join(ROOT, sys.argv[sys.argv.index("--draft") + 1])
    works = load_works(draft)
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    for name in COPY:
        s, d = os.path.join(ROOT, name), os.path.join(OUT, name)
        if os.path.isdir(s):
            shutil.copytree(s, d)
        elif os.path.exists(s):
            shutil.copy2(s, d)

    for i, w in enumerate(works):
        d = os.path.join(OUT, "work", w["slug"])
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "index.html"), "w", encoding="utf-8", newline="\n") as f:
            f.write(work_page(w, works[(i + 1) % len(works)]))

    item_list = {"@type": "ItemList", "name": "그치그치 작업", "itemListElement": [
        {"@type": "ListItem", "position": i, "url": f"{SITE}/work/{w['slug']}/", "name": w["title"]}
        for i, w in enumerate(works, 1)]}
    inject(os.path.join(OUT, "index.html"), "grid", grid_html(works))
    inject(os.path.join(OUT, "index.html"), "jsonld",
           jsonld({"@context": "https://schema.org", "@graph": [org_ld(), website_ld(), item_list]}))
    about = {"@type": "AboutPage", "@id": SITE + "/about.html", "url": SITE + "/about.html",
             "name": "회사 소개 — 그치그치 GCHGCH STUDIO", "inLanguage": "ko",
             "isPartOf": {"@id": SITE_ID}, "about": {"@id": ORG_ID}, "mainEntity": {"@id": ORG_ID}}
    inject(os.path.join(OUT, "about.html"), "jsonld",
           jsonld({"@context": "https://schema.org", "@graph": [org_ld(), website_ld(), about]}))

    for name, text in [("work.html", redirect_page(works)), ("sitemap.xml", sitemap(works)),
                       ("robots.txt", robots()), ("llms.txt", llms(works)), ("404.html", not_found_page(works)),
                       (".nojekyll", "")]:
        with open(os.path.join(OUT, name), "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    print(f"_site 생성: 작업 {len(works)}개" + (" (초안 포함)" if draft else ""))


if __name__ == "__main__":
    main()
