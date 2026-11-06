#!/usr/bin/env python3
"""Read-only SEO and GEO audit for a site you operate. Standard library only.

Usage:
  python -X utf8 audit_seo_geo.py https://example.com --sample 0 --out audit.json

Sends GET requests only. Pretends to be each AI bot's User-Agent on two URLs, so run it
only on sites you own or operate. Prints a Markdown summary and writes full JSON.
A source that cannot be read is reported as an error, never as zero.
"""
import argparse, collections, concurrent.futures as cf, gzip, html.parser, json, random, re, socket, ssl, statistics, sys, time
import urllib.error, urllib.parse, urllib.request, urllib.robotparser, xml.etree.ElementTree as ET, zlib

UA = "seo-geo-audit/1.0"
# (User-Agent token, role). Roles: search, user-fetch, train, or token (robots.txt only, sends no requests).
BOTS = [("Googlebot", "search"), ("Bingbot", "search"), ("OAI-SearchBot", "search"), ("Claude-SearchBot", "search"),
        ("PerplexityBot", "search"), ("Applebot", "search"), ("DuckAssistBot", "search"),
        ("ChatGPT-User", "user-fetch"), ("Claude-User", "user-fetch"), ("Perplexity-User", "user-fetch"),
        ("GPTBot", "train"), ("ClaudeBot", "train"), ("CCBot", "train"), ("Bytespider", "train"), ("Amazonbot", "train"),
        ("Google-Extended", "token"), ("Applebot-Extended", "token")]
PROXY_WORDS = ("kaspersky", "anti-virus", "antivirus", "avast", "avg ", "bitdefender", "eset", "fortinet", "zscaler", "netskope")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def fetch(url, ua=UA, follow=True, timeout=25):
    """Return dict(status, headers, body, url, error). HTTP error codes are results, not exceptions."""
    op = urllib.request.build_opener() if follow else urllib.request.build_opener(NoRedirect)
    req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept-Encoding": "gzip, deflate", "Accept": "*/*"})
    t0 = time.monotonic()
    try:
        r = op.open(req, timeout=timeout)
    except urllib.error.HTTPError as e:
        r = e
    except Exception as e:
        return {"status": None, "headers": {}, "body": b"", "url": url, "error": f"{type(e).__name__}: {e}"}
    ttfb = round((time.monotonic() - t0) * 1000)
    try:
        raw = r.read()
    except Exception as e:
        return {"status": getattr(r, "code", None), "headers": {}, "body": b"", "url": url, "error": str(e)}
    h = {k.lower(): v for k, v in r.headers.items()}
    enc = h.get("content-encoding", "")
    try:
        body = gzip.decompress(raw) if enc == "gzip" else zlib.decompress(raw) if enc == "deflate" else raw
    except Exception:
        body = raw
    return {"status": r.code, "headers": h, "body": body, "url": getattr(r, "url", url), "error": None, "wire": len(raw), "ttfb_ms": ttfb}


class Page(html.parser.HTMLParser):
    SKIP = {"script", "style", "noscript", "template", "svg"}
    CHROME = {"nav", "header", "footer", "aside"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title, self.desc, self.robots, self.canonical, self.lang = "", None, "", None, None
        self.alternates, self.ld, self.scripts, self.words = {}, [], [], []
        self.h1, self.before_h1, self.og = 0, 0, set()
        self._skip, self._chrome, self._in_title, self._ld = 0, 0, False, None

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        if tag == "html":
            self.lang = a.get("lang")
        elif tag == "meta":
            n = a.get("name", "").lower()
            if a.get("property", "").lower() in ("og:title", "og:image"):
                self.og.add(a["property"].lower())
            if n == "description":
                self.desc = a.get("content", "")
            elif n == "robots":
                self.robots = a.get("content", "").lower()
        elif tag == "link":
            rel = a.get("rel", "").lower()
            if rel == "canonical":
                self.canonical = a.get("href")
            elif rel == "alternate" and a.get("hreflang"):
                self.alternates[a["hreflang"].lower()] = a.get("href")
        elif tag == "title":
            self._in_title = True
        elif tag == "h1":
            self.h1 += 1
        elif tag == "script":
            if a.get("type", "") == "application/ld+json":
                self._ld = ""
            elif a.get("src"):
                self.scripts.append(a["src"])
        if tag in self.SKIP:
            self._skip += 1
        if tag in self.CHROME:
            self._chrome += 1

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag == "script" and self._ld is not None:
            self.ld.append(self._ld)
            self._ld = None
        if tag in self.SKIP and self._skip:
            self._skip -= 1
        if tag in self.CHROME and self._chrome:
            self._chrome -= 1

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif self._ld is not None:
            self._ld += data
        elif not self._skip:
            w = re.findall(r"\w+", data)
            if not self.h1:
                self.before_h1 += len(w)
            if not self._chrome:
                self.words.extend(x.lower() for x in w)


def ld_types(node, out):
    if isinstance(node, list):
        for x in node:
            ld_types(x, out)
    elif isinstance(node, dict):
        t = node.get("@type")
        out.update(t if isinstance(t, list) else [t] if t else [])
        for v in node.values():
            ld_types(v, out)


ARTICLE_TYPES = {"Article", "BlogPosting", "NewsArticle"}


def ld_gaps(node, out):
    """Collect fields an Article node lacks. Report only; never invent the values."""
    if isinstance(node, list):
        for x in node:
            ld_gaps(x, out)
    elif isinstance(node, dict):
        t = node.get("@type")
        if set(t if isinstance(t, list) else [t]) & ARTICLE_TYPES:
            out.update(k for k in ("author", "datePublished", "dateModified") if k not in node)
        for v in node.values():
            ld_gaps(v, out)


def norm(u, base=None):
    u = urllib.parse.urljoin(base or "", u or "")
    p = urllib.parse.urlsplit(u)
    return urllib.parse.urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path or "/", p.query, ""))


SM = {"lastmod": 0}


def sitemap_urls(url, seen=None, errors=None):
    seen = set() if seen is None else seen
    if url in seen:
        return []
    seen.add(url)
    r = fetch(url)
    if r["status"] != 200:
        errors.append(f"{url}: {r['status'] or r['error']}")
        return []
    try:
        root = ET.fromstring(r["body"])
    except ET.ParseError as e:
        errors.append(f"{url}: XML lỗi {e}")
        return []
    locs = [e.text.strip() for e in root.iter() if e.tag.endswith("loc") and e.text]
    SM["lastmod"] += sum(1 for e in root.iter() if e.tag.endswith("lastmod"))
    if root.tag.endswith("sitemapindex"):
        return [u for s in locs for u in sitemap_urls(s, seen, errors)]
    return locs


def audit_page(url):
    r = fetch(url)
    d = {"url": url, "status": r["status"], "error": r["error"], "final": r["url"], "flags": []}
    if r["status"] != 200:
        d["flags"].append(f"không trả 200 ({r['status'] or r['error']})")
        return d, None
    p = Page()
    p.feed(r["body"].decode("utf-8", "replace"))
    types, bad_ld, gaps = set(), 0, set()
    for block in p.ld:
        try:
            node = json.loads(block)
            ld_types(node, types)
            ld_gaps(node, gaps)
        except ValueError:
            bad_ld += 1
    canon = norm(p.canonical, url) if p.canonical else None
    d.update(title=p.title.strip(), desc=p.desc, lang=p.lang, canonical=canon, alternates=p.alternates,
             noindex="noindex" in p.robots, h1=p.h1, words=len(p.words), before_h1=p.before_h1,
             bytes=len(r["body"]), wire=r.get("wire"), jsonld=sorted(types), bad_jsonld=bad_ld, scripts=p.scripts,
             cache=r["headers"].get("cf-cache-status"), cache_control=r["headers"].get("cache-control"),
             encoding=r["headers"].get("content-encoding"), ttfb_ms=r.get("ttfb_ms"), hsts=r["headers"].get("strict-transport-security"))
    f = d["flags"]
    if norm(r["url"]) != norm(url):
        f.append(f"sitemap chứa URL chuyển hướng tới {r['url']}")
    if d["noindex"]:
        f.append("sitemap chứa trang noindex")
    if not canon:
        f.append("thiếu canonical")
    elif canon != norm(url):
        f.append(f"canonical trỏ nơi khác: {canon}")
    if not d["title"]:
        f.append("thiếu title")
    elif len(d["title"]) > 65:
        f.append("title trên 65 ký tự")
    if not p.desc:
        f.append("thiếu description")
    elif len(p.desc) > 160:
        f.append("description trên 160 ký tự")
    if p.h1 != 1:
        f.append(f"có {p.h1} thẻ h1")
    if len(p.words) < 80:
        f.append("trang mỏng dưới 80 từ khi chưa chạy JS")
    if p.before_h1 > 150:
        f.append(f"{p.before_h1} từ đứng trước h1")
    if len(r["body"]) > 500_000:
        f.append(f"HTML nặng {len(r['body']) // 1000} KB")
    if not types:
        f.append("không có JSON-LD")
    if gaps:
        f.append("Article thiếu " + ", ".join(sorted(gaps)))
    for og in sorted({"og:title", "og:image"} - p.og):
        f.append(f"thiếu {og}")
    if bad_ld:
        f.append(f"{bad_ld} khối JSON-LD không parse được")
    return d, set(p.words)


def check_locale_pairs(pages, word_sets, limit=200):
    """Hreflang must be reciprocal, and locale versions must really differ in body text."""
    pairs, issues, checked = 0, [], set()
    for d in sorted(pages, key=lambda x: x["url"].count("/")):
        for lang, alt in (d.get("alternates") or {}).items():
            alt = norm(alt, d["url"])
            key = tuple(sorted((norm(d["url"]), alt)))
            if lang == "x-default" or alt == norm(d["url"]) or key in checked or pairs >= limit:
                continue
            checked.add(key)
            pairs += 1
            r = fetch(alt)
            if r["status"] != 200:
                issues.append(f"{d['url']}: hreflang {lang} trả {r['status'] or r['error']}")
                continue
            q = Page()
            q.feed(r["body"].decode("utf-8", "replace"))
            back = {norm(v, alt) for v in q.alternates.values()}
            if norm(d["url"]) not in back:
                issues.append(f"{d['url']}: hreflang {lang} không hai chiều")
            a, b = word_sets.get(d["url"]) or set(), set(q.words)
            if a and b and len(a & b) / len(a | b) > 0.8:
                issues.append(f"{d['url']} và {alt}: thân bài gần như trùng dù khai là bản {lang}")
    return pairs, issues


def tls_issuer(host):
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((host, 443), timeout=15) as s, ctx.wrap_socket(s, server_hostname=host) as t:
            for rdn in t.getpeercert().get("issuer", ()):
                for k, v in rdn:
                    if k in ("organizationName", "commonName"):
                        return v
    except Exception as e:
        return f"lỗi: {e}"
    return None


def flag_kind(f):
    """Group a page flag by type: drop the URL or count that varies per page."""
    for pat, label in ((r"^không trả 200", "không trả 200"), (r"^có \d+ thẻ h1", "số thẻ h1 khác 1"),
                       (r"^\d+ từ đứng trước h1", "trên 150 từ đứng trước h1"), (r"^HTML nặng", "HTML trên 500 KB"),
                       (r"^\d+ khối JSON-LD", "JSON-LD không parse được")):
        if re.match(pat, f):
            return label
    return f if f.startswith("thiếu og:") else f.split(":")[0]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("base")
    ap.add_argument("--sample", type=int, default=200, help="số URL lấy mẫu từ sitemap, 0 là tất cả")
    ap.add_argument("--out", default="audit-seo-geo.json")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--deep-url", help="URL nội dung để thử bot, mặc định lấy từ mẫu")
    a = ap.parse_args()
    base = a.base.rstrip("/")
    u = urllib.parse.urlsplit(base)
    out = {"base": base, "errors": []}

    # Site level
    if u.scheme == "https":
        out["tls_issuer"] = tls_issuer(u.hostname)
    rb = fetch(base + "/robots.txt")
    out["robots_status"] = rb["status"] or rb["error"]
    text = rb["body"].decode("utf-8", "replace") if rb["status"] == 200 else ""
    out["robots_sitemaps"] = re.findall(r"(?im)^sitemap:\s*(\S+)", text)
    out["robots_managed_by_cloudflare"] = "Cloudflare Managed" in text
    out["content_signal"] = re.findall(r"(?im)^content-signal:\s*(.+)$", text)
    llms = fetch(base + "/llms.txt")
    out["llms_txt"] = llms["status"] or llms["error"]
    redirects = {}
    host = u.netloc
    bare = host[4:] if host.startswith("www.") else host
    for name, test in (("http", f"http://{host}/"), ("www", f"{u.scheme}://www.{bare}/"), ("apex", f"{u.scheme}://{bare}/")):
        r = fetch(test, follow=False)
        redirects[name] = {"status": r["status"] or r["error"], "location": r["headers"].get("location")}
    out["redirects"] = redirects

    # Pages
    sm_errors = []
    urls = []
    for s in out["robots_sitemaps"] or [base + "/sitemap.xml"]:
        urls += sitemap_urls(s, errors=sm_errors)
    urls = list(dict.fromkeys(urls))
    out["sitemap_count"], out["sitemap_errors"] = len(urls), sm_errors
    if not urls:
        out["errors"].append("không đọc được URL nào từ sitemap, phần trang KHÔNG được đo")
        urls = [base + "/"]
    rng = random.Random(42)
    must = [base + "/"]
    rest = [x for x in urls if norm(x) != norm(base + "/")]
    if not a.sample or a.sample >= len(rest):
        sample = rest
    else:
        # Random sampling alone misses rare page types, so always keep the shallowest URLs (lists, locale roots).
        shallow = sorted(rest, key=lambda x: (x.count("/"), x))[:50]
        others = [x for x in rest if x not in set(shallow)]
        sample = shallow + rng.sample(others, max(0, min(a.sample - len(shallow), len(others))))
    with cf.ThreadPoolExecutor(a.workers) as ex:
        results = list(ex.map(audit_page, must + sample))
    pages = [d for d, _ in results]
    word_sets = {d["url"]: w for d, w in results if w}
    pairs, locale_issues = check_locale_pairs(pages, word_sets)
    out["locale_pairs_checked"], out["locale_issues"] = pairs, locale_issues
    out["pages"] = pages

    dup = {}
    for key in ("title", "desc"):
        g = collections.defaultdict(list)
        for d in pages:
            if d.get(key):
                g[d[key].strip()].append(d["url"])
        dup[key] = {k: v for k, v in g.items() if len(v) > 1}
    out["duplicates"] = dup

    # Bots: a spoofed User-Agent shows User-Agent rules only, not rules keyed on the bot's real IP.
    deep = a.deep_url or max((d for d in pages if d.get("status") == 200), key=lambda d: d.get("words", 0), default={"url": base + "/"})["url"]
    rp = urllib.robotparser.RobotFileParser()
    rp.parse(text.splitlines())
    bots = []
    for name, role in BOTS:
        row = {"bot": name, "role": role, "robots_allows": rp.can_fetch(name, deep) if text else None}
        if role != "token":
            codes = [fetch(x, ua=f"Mozilla/5.0 (compatible; {name}/1.0)")["status"] for x in (base + "/", deep)]
            row["network"] = codes
            row["conflict"] = bool(row["robots_allows"]) and any(c in (401, 403, 429, 503) for c in codes)
        bots.append(row)
    out["bots"] = bots

    # Site-level issues
    issues = []
    home = pages[0]
    if u.scheme == "https" and redirects["http"]["status"] == 200:
        issues.append("http trả 200, không chuyển sang https")
    other = "www" if not host.startswith("www.") else "apex"
    if redirects[other]["status"] == 200:
        issues.append(f"bản {other} trả 200, không chuyển về tên miền chính")
    if u.scheme == "https" and not home.get("hsts"):
        issues.append("thiếu HSTS")
    if not out["robots_sitemaps"]:
        issues.append("robots.txt không khai Sitemap")
    if urls and not SM["lastmod"]:
        issues.append(f"sitemap không có lastmod (0/{len(urls)})")
    if out["llms_txt"] != 200:
        issues.append("chưa có llms.txt (chuẩn tự nguyện, tác động chưa chắc)")
    if home.get("cache") == "DYNAMIC":
        issues.append("HTML không được cache ở CDN (DYNAMIC)")
    for path in ("/index.html", "/index.txt"):
        r = fetch(base + path, follow=False)
        if r["status"] == 200 and "x-robots-tag" not in r["headers"]:
            issues.append(f"{path} trả 200 ({r['headers'].get('content-type', '?')}), không chuyển hướng hay chặn index")
    same = [urllib.parse.urljoin(base + "/", s) for s in home.get("scripts") or []]
    same = [s for s in same if urllib.parse.urlsplit(s).netloc == host and "/_next/static/" in s]
    if same:
        cc = fetch(same[0])["headers"].get("cache-control", "")
        m = re.search(r"max-age=(\d+)", cc)
        if "immutable" not in cc and (not m or int(m.group(1)) < 2592000):
            issues.append(f"JS có mã băm cache ngắn ({cc or 'không khai'})")
    for b in bots:
        if b.get("conflict"):
            issues.append(f"DẤU HIỆU, cần xác nhận ở CDN: {b['bot']} được robots cho phép nhưng mạng trả {b['network']}")
    out["site_issues"] = issues

    hosts = collections.Counter()
    for d in pages:
        for s in d.get("scripts") or []:
            h = urllib.parse.urlsplit(urllib.parse.urljoin(d["url"], s)).netloc
            if h and h != u.netloc:
                hosts[h] += 1
    out["third_party_scripts"] = hosts.most_common()
    proxy = [x for x in [str(out.get("tls_issuer", ""))] + list(hosts) if any(w in x.lower() for w in PROXY_WORDS)]
    out["measurement_warning"] = proxy

    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # Summary
    ok = [d for d in pages if d.get("status") == 200]
    flags = collections.Counter(flag_kind(f) for d in pages for f in d["flags"])
    print(f"# Audit {base}\n")
    if proxy:
        print(f"⚠️ Phần mềm chen giữa kết nối: {proxy}. Số TTFB, dung lượng và điểm tốc độ từ máy này không đáng tin.\n")
    for e in out["errors"] + sm_errors:
        print(f"⚠️ LỖI ĐO: {e}")
    print(f"- TLS issuer: {out.get('tls_issuer')}")
    print(f"- robots.txt: {out['robots_status']}, Sitemap: {out['robots_sitemaps'] or 'KHÔNG KHAI'}, Cloudflare quản lý: {out['robots_managed_by_cloudflare']}")
    print(f"- Content-Signal: {out['content_signal'] or 'không có'}")
    print(f"- llms.txt: {out['llms_txt']}")
    print(f"- Chuyển hướng: {json.dumps(redirects, ensure_ascii=False)}")
    print(f"- Sitemap: {len(urls)} URL, đã đo {len(pages)} ({len(ok)} trả 200)")
    print(f"- JSON-LD: {sum(1 for d in ok if d.get('jsonld'))}/{len(ok)}; loại: {sorted({t for d in ok for t in d.get('jsonld', [])})}")
    ttfbs = [d["ttfb_ms"] for d in ok if d.get("ttfb_ms")]
    print(f"- TTFB trung vị từ máy này: {statistics.median(ttfbs) if ttfbs else 'không đo được'} ms (gồm kết nối, chỉ để so tương đối)")
    print(f"- Trang chủ: {pages[0].get('bytes')} byte, cache {pages[0].get('cache')}, cache-control {pages[0].get('cache_control')}, nén {pages[0].get('encoding')}")
    print(f"- Script bên thứ ba trong HTML Python nhận: {out['third_party_scripts']} (Chrome có thể thấy thêm, xem Lighthouse)")
    print(f"- Title trùng: {len(dup['title'])} nhóm; description trùng: {len(dup['desc'])} nhóm (mẫu có thể bỏ sót, soát thêm code sinh metadata)")
    print(f"- Cặp ngôn ngữ đã kiểm: {pairs}, lỗi: {len(locale_issues)}\n")
    print("## Lỗi cấp site\n")
    for i in issues:
        print(f"- {i}")
    print()
    print("## Lỗi theo loại\n\n| Lỗi | Số trang |\n|---|---:|")
    for k, v in flags.most_common():
        print(f"| {k} | {v} |")
    for i in locale_issues[:15]:
        print(f"- {i}")
    print("\n## Bot (User-Agent giả, không phải IP thật)\n\n| Bot | Vai trò | robots cho phép | Mạng (trang chủ, trang nội dung) | Mâu thuẫn |\n|---|---|---|---|---|")
    for b in bots:
        print(f"| {b['bot']} | {b['role']} | {b['robots_allows']} | {b.get('network', '-')} | {'CÓ' if b.get('conflict') else ''} |")
    print(f"\nChi tiết: {a.out}")
    return 1 if out["errors"] or sm_errors else 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
