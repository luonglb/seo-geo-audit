# Tham khảo cho seo-geo-audit

Mở ở bước 1 của `SKILL.md`. Rút từ một ca thật (11/2026, site nội dung tĩnh Next.js, Cloudflare, tự deploy lên VPS, vài trăm trang).

## Bẫy đã gặp

| Bẫy | Chuyện đã xảy ra | Làm gì |
|---|---|---|
| Antivirus chen giữa TLS | Kaspersky đổi chứng chỉ, chèn script từ `kaspersky-labs.com` (dấu hiệu này chắc hơn giao thức, vì HTTP/1.1 hay `h2` có lúc khác nhau). Điểm trang mục 50, sau khi chặn script là 72 | Xem `tls_issuer` và request lạ trong Lighthouse (cùng máy đó, Python vẫn thấy chứng chỉ thật, nên một nguồn sạch chưa đủ), chặn script chèn thêm, coi số là tương đối, nhờ người dùng đo lại trên PageSpeed |
| Lỗi quyền bị đọc thành kết luận | PageSpeed API trả 429, CrUX trả 403 | Ghi "chưa đo được, lý do", không kết luận về traffic |
| Bản dịch giả | Hàng trăm trang `/en/` giao diện tiếng Anh, thân bài tiếng Việt, khai hreflang là bản dịch | Trỏ canonical về bản gốc, bỏ hreflang, bỏ khỏi sitemap. Báo người dùng: trang đó sẽ dần ra khỏi Google |
| `robots.txt` cho phép nhưng mạng chặn | PerplexityBot trả 403 dù `robots.txt` không cấm | So cả hai cột. User-Agent giả không có IP thật, nên ghi kết quả là dấu hiệu rồi kiểm ở bảng điều khiển |
| Robots do CDN chèn | Cloudflare tự thêm luật, `robots.ts` trong repo không phản ánh web thật | Luôn đọc `robots.txt` trên web thật |
| Mẫu bỏ sót trùng lặp | Mẫu chỉ thấy vài chục cặp trùng, code cho thấy mọi trang cùng loại đều trùng | Đọc thêm code sinh metadata |
| Danh sách lớn nhúng trong HTML | Mục lục hơn 2 MB vì nhúng dữ liệu tìm kiếm của toàn bộ nội dung, mọi trang tải trước phần đó | Gửi phần đầu, tải phần còn lại khi cần. Sau sửa: dưới 200 KB |
| Tách commit bằng công cụ | 4 commit không tự build được, phải thêm commit sửa | Build sau từng commit |
| Test ghi đè file đang sửa dở | Playwright ghi đè ảnh chụp đang sửa dở của người khác | Sao lưu, chép lại, so md5, không đưa vào commit |
| Gói deploy cũ | `out.tgz` vẫn là bản trước, md5 trong tài liệu vẫn khớp nên kiểm tra báo đúng | Dựng lại sau thay đổi cuối, kiểm tên file mới trong gói |
| File xác minh bị xoá | `rsync --delete` sẽ xoá file chép tay lên server | Đặt trong thư mục tĩnh của repo |
| Người dùng dán cả khối quay lại | Dán luôn lệnh rollback có `YYYYMMDD-HHMM`, may là lệnh lỗi trước khi chép | Khối rollback để riêng, ghi rõ "chỉ chạy khi lỗi", dùng tên bản sao lưu thật |
| Đo và build cùng lúc | Máy bận làm sai số | Đo xong mới build |
| Cache HTML ở CDN | Bật cache làm mỗi lần deploy phải xoá bộ đệm, App Router có thể lẫn RSC | Chỉ gợi ý kèm chi phí đó. Với App Router, kiểm request RSC không nhận nhầm HTML đã cache và có đường quay lại |

## Đọc số tốc độ

- Một lần Lighthouse không phải phép đo. Chạy nhiều lần, chênh lệch nhỏ hơn độ dao động thì không tính.
- CrUX không có dòng cho một trang hay quốc gia nghĩa là chưa đủ dữ liệu công khai, không có nghĩa là nhanh. Lỗi API là lỗi đo, không phải kết luận.
- Số đo người dùng thật có thể bị bot headless hoặc chính người vận hành kéo lệch ở trang ít traffic. Lọc trước khi kết luận.

## Lệnh Lighthouse

Chạy ngoài repo, không cài vào repo. Bash:

```bash
npx --yes lighthouse@latest "https://domain/" --only-categories=performance,seo,best-practices,accessibility \
  --output=json --output-path="OUT_DIR/home-1.json" --quiet --chrome-flags="--headless=new"
```

- Không thấy Chrome thì đặt biến `CHROME_PATH` tới Chrome hoặc Edge.
- Chặn script do phần mềm chèn: thêm `--blocked-url-patterns="*kaspersky-labs.com*"` (thay bằng host thấy trong network).
- Ghi phiên bản Lighthouse vào báo cáo. So trước và sau phải cùng phiên bản.
- Trong PowerShell 5.1, `curl` là bí danh của `Invoke-WebRequest`, phải gõ `curl.exe`.

## Lighthouse báo nhưng phải kiểm lại

| Báo | Có thể sai vì | Kiểm bằng |
|---|---|---|
| HTML không nén | Antivirus giải nén rồi mới đưa cho Chrome | `curl.exe -sI -H "Accept-Encoding: br, gzip" URL`, xem `content-encoding` |
| `robots-txt` trừ điểm SEO | Lighthouse không hiểu dòng `Content-Signal` do Cloudflare chèn | Đọc mục lỗi trong JSON; chỉ có dòng đó thì không phải lỗi crawl |
| Lỗi CORS của beacon CDN | Có thể do phần mềm chen giữa | Gọi trực tiếp tệp đó, xem header |

## Content-Signal

Dòng do Cloudflare chèn trong `robots.txt`. `search` là lập chỉ mục tìm kiếm, `ai-input` là đưa vào mô hình để trả lời theo thời gian thực, `ai-train` là huấn luyện. Không khai giá trị nào thì không cho phép cũng không cấm dùng theo giá trị đó. Đây là tín hiệu, bot có thể không tuân theo, và không thay cho luật chặn.

## Bot AI (kiểm 06/11/2026, xem lại tài liệu gốc khi đã cũ)

Tài liệu gốc: https://platform.openai.com/docs/bots · https://docs.perplexity.ai/guides/bots · https://developers.google.com/search/docs/crawling-indexing/google-common-crawlers . Tên bot không có trong bảng, như `meta-externalagent`, `GoogleOther`, thì tra tài liệu của hãng, không đoán vai trò.

| Loại | Tên | Ý nghĩa khi chặn |
|---|---|---|
| Tìm kiếm | Googlebot, Bingbot, OAI-SearchBot, Claude-SearchBot, PerplexityBot, Applebot, DuckAssistBot | Khó xuất hiện và được trích dẫn trên công cụ đó |
| Mở trang theo yêu cầu | ChatGPT-User, Claude-User, Perplexity-User | Trợ lý không đọc được trang khi người dùng hỏi |
| Huấn luyện | GPTBot, ClaudeBot, CCBot, Bytespider, Amazonbot | Nội dung ít vào mô hình hơn, thường không ảnh hưởng bot tìm kiếm |
| Chỉ là tên trong robots | Google-Extended, Applebot-Extended | Không phải bot gửi request riêng, chỉ khai báo trong `robots.txt` |

Gợi ý mặc định: mở bot tìm kiếm và bot mở trang; bot huấn luyện để người dùng quyết. Đây là quyết định kinh doanh và bản quyền, không tự đổi.

## JSON-LD

- Chỉ chọn loại đúng với trang: `WebSite`, `Organization`, `BreadcrumbList`, `Article`, `Book`, `Chapter`, `Product`...
- `author`, `translator`, `datePublished`, `dateModified`, `license` phải có nguồn: file trong repo hoặc git log. Thiếu thì bỏ trường, không đoán.
- Có JSON-LD đúng cú pháp không có nghĩa Google sẽ hiện kết quả đặc biệt. Sau deploy chạy Rich Results Test.

## Mẫu báo cáo

```markdown
# Báo cáo SEO GEO: <domain>
Ngày đo: <ngày>. Trạng thái: <chỉ audit, chưa sửa / commit trên máy / đã deploy>.

## 1. Kết luận (5 dòng): SEO, GEO, tốc độ, việc tác động lớn nhất, giới hạn số đo
## 2. Bảng số
- Điều kiện đo (công cụ, phiên bản, số lần, máy, có gì chen giữa)
- Web thật trước sửa | Cục bộ trước và sau | Dung lượng | Crawl | Bot | Nguồn chưa đo được và lý do
## 3. Lỗi phát hiện, xếp theo tác động: mức độ (xác nhận / dấu hiệu), bằng chứng, giảm nhẹ, trạng thái (đã sửa + commit / chưa sửa)
## 3b. Không phải lỗi: công cụ báo gì, kiểm lại thấy gì
## 3c. Kết quả test nếu có sửa code
## 4. Chưa làm được và vì sao; đề xuất về nội dung
## 5. Việc người dùng cần làm, xếp theo tác động, có nơi bấm cụ thể
```
