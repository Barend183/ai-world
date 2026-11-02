"""The computer on the AI's desk: web search and page reading, no API keys needed."""
import ipaddress
import json
import re
import socket
import urllib.parse
import urllib.request
from html import unescape
from html.parser import HTMLParser

BOT_UA = "AIWorld/1.0 (a hobby AI that teaches itself; personal project)"
IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
SKIP_TAGS = {"script", "style", "noscript", "svg", "nav", "footer", "header", "form", "aside", "iframe", "button"}
BLOCK_TAGS = {"p", "div", "li", "br", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "section", "article", "blockquote", "pre"}


def _fetch(url, data=None, timeout=20, limit=3_000_000):
    # Wikimedia asks bots to say who they are; everyone else gets an ordinary browser.
    ua = BOT_UA if re.search(r"(wikipedia|wikimedia)\.org", url) else UA
    req = urllib.request.Request(url, data=data, headers={"User-Agent": ua, "Accept-Language": "en"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(limit), r.headers.get_content_type(), r.headers.get_content_charset() or "utf-8"


def _get(url, data=None, timeout=20, limit=3_000_000):
    raw, ctype, charset = _fetch(url, data, timeout, limit)
    return raw.decode(charset, errors="replace"), ctype


def _pdf_text(raw, max_chars):
    try:
        import io
        from pypdf import PdfReader
    except ImportError:
        raise ValueError("can't read PDF files on this computer (pypdf isn't installed)")
    pdf = PdfReader(io.BytesIO(raw))
    # (max_chars here is how far into the document the reader wants to get)
    title = (pdf.metadata.title if pdf.metadata and pdf.metadata.title else "") or ""
    text = ""
    for page in pdf.pages[:120]:
        text += (page.extract_text() or "") + "\n"
        if len(text) > max_chars * 1.5:
            break
    if len(text.strip()) < 200:
        raise ValueError("that PDF has no readable text (it may be scanned images)")
    return title, text


# Pages that are really a bot check or a block notice, not the article.
BLOCKED = re.compile(r"client challenge|just a moment|verify you are (a )?human|enable javascript|captcha|access denied|"
                     r"are you a robot|unusual traffic|checking your browser", re.I)


def _is_public(url):
    """Only let the AI visit the public internet, never this machine or the local network."""
    parts = urllib.parse.urlparse(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        return False
    try:
        for info in socket.getaddrinfo(parts.hostname, None):
            ip = ipaddress.ip_address(info[4][0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
                return False
    except (socket.gaierror, ValueError):
        return False
    return True


class _Text(HTMLParser):
    def __init__(self, base=""):
        super().__init__(convert_charrefs=True)
        self.out, self.title, self._skip, self._in_title = [], "", 0, False
        self.base, self.images, self.links, self._link = base, [], [], None

    def handle_starttag(self, tag, attrs):
        if tag == "a" and not self._skip:
            href = dict(attrs).get("href") or ""
            if href and not href.startswith(("#", "javascript:", "mailto:", "tel:")):
                self._link = [urllib.parse.urljoin(self.base, href).split("#")[0], ""]
        if tag == "img" and not self._skip:
            a = dict(attrs)
            src = a.get("src") or a.get("data-src") or ""
            small = any(str(a.get(k) or "").isdigit() and int(a[k]) < 80 for k in ("width", "height"))
            if src and not src.startswith("data:") and not src.lower().endswith((".svg", ".gif")) and not small:
                self.images.append((urllib.parse.urljoin(self.base, src), (a.get("alt") or "").strip()[:100]))
        if tag in SKIP_TAGS:
            self._skip += 1
        elif tag == "title":
            self._in_title = True
        if tag in BLOCK_TAGS:
            self.out.append("\n")

    def handle_endtag(self, tag):
        if tag == "a" and self._link:
            url, label = self._link[0], " ".join(self._link[1].split())
            junk = re.search(r"log ?in|sign ?(in|up)|share|cookie|privacy|subscribe|cart|account|addtoany|facebook|twitter|x\.com|instagram", label + " " + url, re.I)
            if len(label) > 3 and url.startswith("http") and not junk:
                self.links.append((url, label[:90]))
            self._link = None
        if tag in SKIP_TAGS and self._skip:
            self._skip -= 1
        elif tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif not self._skip:
            self.out.append(data)
            if self._link:
                self._link[1] += data


def html_to_text(html, base=""):
    p = _Text(base)
    p.feed(html)
    text = re.sub(r"[ \t\r\f\v]+", " ", "".join(p.out))
    lines = [ln.strip() for ln in text.split("\n")]
    # Drop menu crumbs: very short lines are mostly navigation.
    lines = [ln for ln in lines if len(ln) > 30 or (ln and ln[-1] in ".:?!")]
    seen, images = set(), []
    for src, alt in p.images:
        if src not in seen:
            seen.add(src)
            images.append((src, alt))
    seen_links, links = {base.split("#")[0]}, []
    for url, label in p.links:
        if url not in seen_links:
            seen_links.add(url)
            links.append((url, label))
    return p.title.strip(), "\n".join(lines), images[:8], links[:40]


def _duckduckgo(query, n):
    html, _ = _get("https://html.duckduckgo.com/html/", data=urllib.parse.urlencode({"q": query}).encode())
    results = []
    for m in re.finditer(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>(.*?)class="result__snippet"[^>]*>(.*?)</a>', html, re.S):
        href, title, _, snippet = m.groups()
        href = unescape(href)
        if "uddg=" in href:
            href = urllib.parse.unquote(urllib.parse.parse_qs(urllib.parse.urlparse(href).query)["uddg"][0])
        if "duckduckgo.com/y.js" in href:  # adverts
            continue
        strip = lambda s: unescape(re.sub(r"<[^>]+>", "", s)).strip()
        results.append({"title": strip(title), "url": href, "snippet": strip(snippet)})
        if len(results) >= n:
            break
    return results


def _duckduckgo_lite(query, n):
    html, _ = _get("https://lite.duckduckgo.com/lite/", data=urllib.parse.urlencode({"q": query}).encode())
    strip = lambda t: unescape(re.sub(r"<[^>]+>", "", t)).strip()
    return [{"title": strip(m.group(2)), "url": unescape(m.group(1)), "snippet": strip(m.group(3))}
            for m in re.finditer(r"<a[^>]+href=\"([^\"]+)\"[^>]+class='result-link'>(.*?)</a>.*?<td class='result-snippet'>(.*?)</td>", html, re.S)
            if "duckduckgo.com/y.js" not in m.group(1)][:n]


def papers(query, n=6):
    """Research papers from OpenAlex (free, no key), with a link to the full text when it's free to read."""
    q = urllib.parse.urlencode({"search": query, "per-page": n, "select": "title,doi,publication_year,open_access,abstract_inverted_index,primary_location"})
    data = json.loads(_get(f"https://api.openalex.org/works?{q}")[0])
    out = []
    for w in data.get("results", []):
        words = {}
        for word, places in (w.get("abstract_inverted_index") or {}).items():
            for p in places:
                words[p] = word
        abstract = " ".join(words[i] for i in sorted(words))[:300]
        url = (w.get("open_access") or {}).get("oa_url") or w.get("doi") or ((w.get("primary_location") or {}).get("landing_page_url"))
        if url:
            free = "free to read" if (w.get("open_access") or {}).get("oa_url") else "may be paywalled"
            out.append({"title": f"{w.get('title')} ({w.get('publication_year')}, {free})", "url": url, "snippet": abstract})
    return out


def _wikipedia(query, n):
    q = urllib.parse.urlencode({"action": "query", "list": "search", "srsearch": query, "format": "json", "srlimit": n})
    data = json.loads(_get(f"https://en.wikipedia.org/w/api.php?{q}")[0])
    return [{
        "title": h["title"] + " (Wikipedia)",
        "url": "https://en.wikipedia.org/wiki/" + urllib.parse.quote(h["title"].replace(" ", "_")),
        "snippet": unescape(re.sub(r"<[^>]+>", "", h["snippet"])),
    } for h in data["query"]["search"]]


def search(query, n=6, kind="web"):
    if kind == "papers":
        try:
            return papers(query, n), []
        except Exception as e:
            return [], [f"openalex: {e}"]
    results, errors = [], []
    for engine in (_duckduckgo, _duckduckgo_lite, _wikipedia):
        try:
            for r in engine(query, n):
                if r["url"] not in {x["url"] for x in results}:
                    results.append(r)
        except Exception as e:
            errors.append(f"{engine.__name__.strip('_')}: {e}")
        if len(results) >= n:
            break
    return results[: n + 2], errors


def _wikipedia_article(url):
    title = urllib.parse.unquote(url.split("/wiki/", 1)[1].split("#")[0])
    q = urllib.parse.urlencode({"action": "query", "prop": "extracts", "explaintext": 1, "titles": title,
                                "format": "json", "redirects": 1})
    pages = json.loads(_get(f"https://en.wikipedia.org/w/api.php?{q}")[0])["query"]["pages"]
    page = next(iter(pages.values()))
    images = []
    try:   # the article's photos, as 800 px versions
        q = urllib.parse.urlencode({"action": "query", "generator": "images", "titles": title, "gimlimit": 15, "redirects": 1,
                                    "prop": "imageinfo", "iiprop": "url|mime", "iiurlwidth": 800, "format": "json"})
        for p in json.loads(_get(f"https://en.wikipedia.org/w/api.php?{q}")[0]).get("query", {}).get("pages", {}).values():
            info = (p.get("imageinfo") or [{}])[0]
            if info.get("mime") in ("image/jpeg", "image/png") and info.get("thumburl"):
                images.append((info["thumburl"], p["title"].replace("File:", "").rsplit(".", 1)[0][:100]))
    except Exception:
        pass
    return page.get("title", title), page.get("extract", ""), images[:6]


def read(url, max_chars, part=1):
    """Reads a public web page, PDF, text or JSON. Long pages come in parts of max_chars.
    Returns a dict: title, text, images, links, part, parts."""
    if not _is_public(url):
        raise ValueError("that address isn't on the public internet")
    if re.match(r"https?://en\.wikipedia\.org/wiki/", url):
        title, text, images = _wikipedia_article(url)
        links = []
    else:
        raw, ctype, charset = _fetch(url, limit=15_000_000)
        images, links = [], []
        if ctype == "application/pdf" or raw[:5] == b"%PDF-":
            title, text = _pdf_text(raw, max_chars * part)
        elif "html" in ctype:
            title, text, images, links = html_to_text(raw.decode(charset, errors="replace"), url)
            if BLOCKED.search(title + " " + text[:600]) and len(text) < 2500:
                raise ValueError("the site showed a bot check instead of the page; try another source")
        elif ctype.startswith("text/") or "json" in ctype:
            title, text = url, raw.decode(charset, errors="replace")
        else:
            raise ValueError(f"can't read {ctype} files")
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    parts = max(1, -(-len(text) // max_chars))
    part = min(max(1, int(part)), parts)
    chunk = text[(part - 1) * max_chars: part * max_chars]
    if part < parts:
        chunk += f" [...continues: part {part} of {parts}]"
    return {"title": title or url, "text": chunk, "images": images, "links": links, "part": part, "parts": parts}


def fetch_image(url, limit=6_000_000):
    """Downloads a picture so the AI can look at it: (mime type, bytes)."""
    if not _is_public(url):
        raise ValueError("that address isn't on the public internet")
    ua = BOT_UA if re.search(r"(wikipedia|wikimedia)\.org", url) else UA
    req = urllib.request.Request(url, headers={"User-Agent": ua})
    with urllib.request.urlopen(req, timeout=30) as r:
        mime = r.headers.get_content_type()
        data = r.read(limit + 1)
    if mime not in IMAGE_TYPES:
        raise ValueError(f"that isn't a photo I can look at ({mime})")
    if len(data) > limit:
        raise ValueError("that picture is too big")
    return mime, data


def spark(seed):
    """Something from the wider world to notice on waking (a newspaper on the doorstep): a random
    article, today's featured article, something that happened on this day, or the picture of the day.
    It's only there to be noticed; following it is up to the AI. Returns text, or None."""
    from datetime import datetime, timezone
    import random
    rng = random.Random(seed)
    today = datetime.now(timezone.utc)
    kinds = ["random", "featured", "onthisday", "picture"]
    rng.shuffle(kinds)
    for kind in kinds:
        try:
            if kind == "random":
                q = urllib.parse.urlencode({"action": "query", "generator": "random", "grnnamespace": 0, "prop": "extracts",
                                            "exintro": 1, "explaintext": 1, "exchars": 400, "format": "json"})
                page = next(iter(json.loads(_get(f"https://en.wikipedia.org/w/api.php?{q}")[0])["query"]["pages"].values()))
                return (f"A random encyclopedia page caught your eye: \"{page['title']}\". {page.get('extract', '')}"
                        f" (https://en.wikipedia.org/wiki/{urllib.parse.quote(page['title'].replace(' ', '_'))})")
            feed = json.loads(_get(f"https://en.wikipedia.org/api/rest_v1/feed/featured/{today:%Y/%m/%d}")[0])
            if kind == "featured" and feed.get("tfa"):
                a = feed["tfa"]
                return (f"Today's featured encyclopedia article is \"{a.get('normalizedtitle')}\": {a.get('extract', '')[:400]}"
                        f" ({a.get('content_urls', {}).get('desktop', {}).get('page', '')})")
            if kind == "onthisday" and feed.get("onthisday"):
                e = rng.choice(feed["onthisday"])
                return f"On this day in {e.get('year')}: {e.get('text')}"
            if kind == "picture" and feed.get("image"):
                img = feed["image"]
                return (f"Today's picture of the day: {(img.get('description') or {}).get('text', '')[:300]}"
                        f" (picture: {(img.get('thumbnail') or {}).get('source', '')})")
        except Exception:
            continue
    return None
