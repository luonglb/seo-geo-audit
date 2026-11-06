# seo-geo-audit

Skill cho Claude Code: đo rồi sửa SEO và GEO của website bạn đang vận hành, có số trước và sau.

GEO (Generative Engine Optimization) là làm cho trợ lý AI như ChatGPT, Perplexity, Claude tìm thấy, hiểu đúng và trích dẫn trang của bạn.

*English: a Claude Code skill that audits and fixes SEO and GEO for a site you operate, with before and after numbers. The skill text is in Vietnamese; the audit script works on any site you run.*

## Skill làm gì

1. Đo mốc bằng script chỉ đọc, rồi đo tốc độ bằng Lighthouse.
2. Soát phần script không thấy, như code sinh metadata và ngôn ngữ thật của thân bài.
3. Xếp lỗi theo tác động, tách riêng dấu hiệu chưa xác nhận và thứ công cụ báo sai.
4. Sửa trong code, đo lại, viết báo cáo.
5. Chỉ deploy khi bạn duyệt, rồi kiểm lại trên web thật.

Skill dừng và hỏi trước khi push, deploy, đổi DNS hay CDN, chặn hoặc mở bot. Nó không tự đăng nhập Search Console hay GA4.

## Cài

Cần [Claude Code](https://claude.com/claude-code) và Python 3. Script chỉ dùng thư viện chuẩn. Muốn đo tốc độ thì cần thêm Node.js và Chrome hoặc Edge.

macOS, Linux:

```bash
git clone https://github.com/luonglb/seo-geo-audit.git ~/.claude/skills/seo-geo-audit
```

Windows PowerShell:

```powershell
git clone https://github.com/luonglb/seo-geo-audit.git "$env:USERPROFILE\.claude\skills\seo-geo-audit"
```

## Dùng

Trong Claude Code, gõ `/seo-geo-audit` hoặc nói "tối ưu SEO GEO cho web của tôi".

Chạy riêng script:

```bash
python -X utf8 scripts/audit_seo_geo.py https://your-site.example --sample 0 --out audit.json
```

`--sample 0` đo mọi URL trong sitemap. Site lớn thì dùng `--sample 300`.

## Script kiểm gì

- **Toàn site:** `robots.txt`, `llms.txt`, chuyển hướng `http` và `www`, HSTS, `lastmod`, cache.
- **Từng trang:** title, description, canonical, `noindex`, h1, Open Graph, JSON-LD, độ dày nội dung khi chưa chạy JS, dung lượng HTML.
- **Đa ngôn ngữ:** hreflang hai chiều, các bản ngôn ngữ có trùng thân bài không.
- **Bot AI:** so luật trong `robots.txt` với phản hồi thật khi gửi User-Agent của từng bot.

## Giới hạn

- ⚠️ **Chỉ dùng cho site bạn sở hữu hoặc vận hành.** Script gửi request GET bằng User-Agent của các bot AI.
- **User-Agent giả không có IP thật của bot,** nên kết quả bot chỉ là dấu hiệu. Cần xác nhận ở bảng điều khiển CDN.
- **Không hứa thứ hạng hay được AI trích dẫn.** `llms.txt` là chuẩn tự nguyện, chưa chắc bot nào đọc.
- **Phần mềm chen giữa kết nối,** như antivirus, làm sai số tốc độ. Nên đo lại bằng PageSpeed Insights từ máy khác.
- **Mới dùng thật trên 1 site.** Bước 1 đến 4 đã được một agent mới chạy thử trên site đó. Bước 5 đến 8 rút từ lần làm thật, chưa chạy thử độc lập theo file skill. Tên bot và menu CDN thay đổi theo thời gian, nên hãy kiểm lại với tài liệu gốc.

## Nguồn gốc

Dự án cá nhân, không chính thức, không do Anthropic phát hành hoặc bảo trợ. Ghi công bên thứ ba xem trong [LICENSE](LICENSE).

## Giấy phép

[MIT](LICENSE)
