---
name: seo-geo-audit
description: Đo rồi sửa SEO và GEO (để trợ lý AI tìm thấy, hiểu đúng và trích dẫn) cho website mình vận hành, có số trước và sau, đưa lên web thật và kiểm lại. Dùng khi nói "tối ưu SEO", "tối ưu GEO", "SEO GEO", "audit SEO", "kiểm tra SEO", "web chưa lên Google", "Google chưa index", "AI không trích dẫn trang", "ChatGPT Perplexity không thấy web", "thêm JSON-LD", "schema markup", "structured data", "llms.txt", "hreflang", "canonical", "sitemap", "chặn bot AI", "AI crawler", "Search Console", "Bing Webmaster", "generative engine optimization", "AI search visibility", "SEO audit". Không dùng khi chỉ hỏi trang chậm, Core Web Vitals hay điểm Lighthouse mà không có mục tiêu tìm kiếm, gắn hoặc kiểm tracking, viết bài hay nghiên cứu từ khoá, chạy quảng cáo, hoặc audit site của người khác không có quyền vận hành.
---

# /seo-geo-audit

Đầu vào: domain đang chạy và repo của nó. Đầu ra: báo cáo số trước/sau, commit sửa lỗi, và danh sách việc người dùng phải tự bấm.

## Dùng khi nào
- Web đã chạy nhưng chưa rõ Google hoặc trợ lý AI thấy gì.
- Trước hoặc sau một đợt đổi cấu trúc trang, thêm ngôn ngữ, đổi tên miền.
- Muốn quyết định chặn hay mở bot AI dựa trên bằng chứng.

## Không dùng khi
- Chỉ cần tốc độ, không có mục tiêu tìm kiếm: dùng skill đo tốc độ trang nếu máy có, hoặc Lighthouse trực tiếp.
- Việc là viết nội dung, tìm từ khoá, hay mua link.

## Đọc trước
1. `AGENTS.md` hoặc `CLAUDE.md` của repo, cách deploy, file tiến độ.
2. `reference.md` cạnh file này: bẫy đã gặp, danh sách bot, mẫu báo cáo. Đọc trước bước 1.

## Các bước

### 1. Chốt phạm vi và đo mốc
- Làm: xác nhận người dùng vận hành site. Ghi `git status`, không đụng file đang sửa dở. Chạy, không sửa gì trước khi có số:
  `python -X utf8 "SKILL_DIR/scripts/audit_seo_geo.py" https://domain --sample 0 --out "OUT_DIR/audit.json"`
  `SKILL_DIR` là thư mục chứa file này. `OUT_DIR` là thư mục tạm ngoài repo, luôn đặt đường dẫn trong ngoặc kép. `--sample 0` đo mọi URL, dùng khi sitemap dưới khoảng 2.000 URL. Lớn hơn thì `--sample 300`, script tự giữ 50 URL nông nhất. Mẫu ngẫu nhiên từng bỏ sót một trang gốc ngôn ngữ.
- Đọc dòng cảnh báo đầu tiên. Có antivirus hoặc proxy chen giữa thì coi TTFB và dung lượng là số tương đối. Không có cảnh báo chưa chứng minh được là sạch: script chỉ thấy kết nối của Python, Chrome có thể bị chen khác đi, nên soát thêm request lạ trong Lighthouse ở bước 2.
- Xong khi: có JSON mốc và nhớ rõ URL nào đã đo, URL nào chưa.

### 2. Đo tốc độ, dữ liệu thật
- Làm: đọc mục đọc số trong `reference.md`, rồi chạy lệnh Lighthouse ở đó. Máy có skill đo tốc độ riêng như `bto-page-quality` thì đọc thêm. Mobile, ít nhất 3 lần mỗi URL, lấy trung vị, ghi độ dao động. Đo trang chủ, trang có HTML nặng nhất theo JSON của bước 1, một trang nội dung, một trang mỗi ngôn ngữ. Không build song song khi đang đo.
- Có script lạ do phần mềm chèn: chạy thêm một bộ chặn script đó, báo cả hai bộ số và nêu bộ nào dùng để so.
- CrUX, GA4, Search Console: dùng nếu có sẵn key hoặc quyền trong môi trường. Được thử gọi API công khai một lần không key. Không có thì ghi "chưa đo được, vì...". Không tự đăng nhập, không tạo tài khoản.
- Xong khi: mỗi nguồn có số hoặc lý do thiếu.

### 3. Soát phần script không thấy
- Làm: đọc code sinh metadata, sitemap, i18n. Lấy mẫu không bắt hết trùng lặp. Mở thử trang mỗi ngôn ngữ, gồm cả trang danh sách: phần lớn thân bài trong `<main>` phải đúng ngôn ngữ khai ở `lang` và `hreflang`.
- GEO: nội dung có trong HTML khi chưa chạy JS; câu trả lời đứng gần đầu trang, tính theo thứ tự trong HTML vì bot không thấy bố cục (cột `before_h1` trên 150 từ thì tìm nguyên nhân trong code); nguồn, tác giả, ngày, giấy phép hiện rõ; bot tìm kiếm AI vào được.
- Cột `words` có thể tính cả mục lục trong thân bài, nên trang không bị báo mỏng chưa chắc đủ nội dung.
- Thử lại bằng `curl.exe` các điểm Lighthouse báo xấu trước khi coi là lỗi, xem bảng báo sai trong `reference.md`.
- Xong khi: mỗi lỗi có URL hoặc `file:dòng` làm bằng chứng.

### 4. Xếp việc theo tác động
- Trước hết là lỗi khiến trang không vào được hay bị hiểu sai (`noindex`, canonical, trùng lặp, chặn bot), rồi dữ liệu có cấu trúc, tiếp đến tốc độ, cuối cùng là title và description.
- Mỗi lỗi ghi: mức độ (đã xác nhận hay mới là dấu hiệu), bằng chứng, có gì đang giảm nhẹ không. Ví dụ `www` trả 200 nhưng canonical đúng thì xếp thấp hơn. User-Agent giả chỉ là dấu hiệu, phải xác nhận ở bảng điều khiển CDN.
- Ghi riêng mục "Không phải lỗi": thứ công cụ báo nhưng kiểm lại không đúng.
- Không sửa thứ số đo cho thấy đã ổn. Tăng điểm nhỏ hơn độ dao động thì không gọi là cải thiện.
- Xong khi: có bảng lỗi xếp hạng, và bảng "Không phải lỗi". Chỉ được yêu cầu audit thì dừng ở đây, viết báo cáo theo mẫu trong `reference.md`.

### 5. Sửa trong code
- JSON-LD chỉ khai điều có nguồn trong repo. Thêm `llms.txt` nếu sinh được từ dữ liệu thật.
- Mỗi loại lỗi một commit, và **mỗi commit tự build được**: chạy build sau từng commit hoặc không tách bằng công cụ tự động.
- File xác minh tên miền đặt trong thư mục tĩnh của repo, không chỉ chép tay lên server.
- Thêm test cho JSON-LD và metadata theo mẫu test sẵn có.
- Xong khi: typecheck, test, build đều xanh, và máy kiểm JSON-LD 0 lỗi.

### 6. Đo lại và báo cáo
- Làm: đo lại cùng URL, cùng điều kiện. Ghi rõ số cục bộ hay số web thật. Viết báo cáo theo mẫu trong `reference.md`.
- Việc cần người dùng quyết: đưa lên bàn duyệt của dự án nếu có, kèm gợi ý nên chọn gì.
- Xong khi: báo cáo mở được, và người dùng biết rõ web thật chưa đổi.

### 7. Đưa lên, chỉ khi người dùng duyệt
- **Dừng, hỏi trước:** push, deploy, sửa DNS, Cloudflare, chặn hay mở bot, sửa lịch sử git.
- Dựng gói **sau thay đổi cuối cùng**. Kiểm trong gói có đúng file mới rồi mới đưa lệnh. Cập nhật mọi mã kiểm tra (md5) trong tài liệu deploy.
- Lệnh deploy và lệnh quay lại để hai khối tách hẳn. Khối quay lại ghi rõ "chỉ chạy khi lỗi", và chỉ đưa lệnh có tên bản sao lưu thật.
- Trước push: kiểm remote đúng, độ công khai của repo đúng, quét secret và file nặng phần sắp đẩy. Không `git add -A`.

### 8. Kiểm trên web thật rồi mở nguồn dữ liệu
- Làm: chạy lại script trên web thật. So từng lỗi đã sửa. Báo phần không kiểm được, ví dụ thao tác giao diện.
- Hướng dẫn người dùng: Search Console (loại Domain, bản ghi TXT, gửi sitemap), Bing Webmaster, PageSpeed Insights từ máy không có antivirus chen giữa, Rich Results Test.
- Xong khi: số web thật khớp bản dựng, hoặc từng chỗ lệch được ghi rõ.

## Không làm
- Không gọi số cục bộ là số web thật. Ca thật: antivirus chen giữa làm điểm trang chủ tụt từ 81 xuống 67.
- Không suy "chưa đủ traffic" từ lỗi API. Ca thật: CrUX trả 403 vì thiếu key, không phải vì ít dữ liệu.
- Không chế `FAQPage`, đánh giá, số sao, tác giả, ngày để lấy rich result.
- Không sửa nội dung, câu chữ y tế, pháp lý để "dễ trích". Đưa vào đề xuất.
- Không hứa thứ hạng hay được AI trích dẫn. `llms.txt` là chuẩn tự nguyện, ghi rõ chưa chắc bot nào đọc.
- Không in hay ghi API key, token, mật khẩu. Người dùng gõ mật khẩu máy chủ ở terminal của họ, không gửi vào chat.
- Không quét site người khác bằng User-Agent giả.

## Xong khi
- Báo cáo có bảng trước/sau ghi nguồn và ngày, lỗi đã sửa kèm commit, phần chưa đo được, việc của người dùng xếp theo tác động.
- Nếu đã deploy: script chạy lại trên web thật không còn các lỗi đã báo là đã sửa.

## Eval

| Chỉ số | Cách đo | Đích |
|---|---|---|
| Gọi đúng lúc | 5 câu nên gọi + 5 câu nghe giống nhưng không nên gọi | ≥ 9/10 |
| Lỗi thật được bắt | Chạy trên site có lỗi đã biết, đếm lỗi tìm ra | 100% lỗi đã biết |
| Báo sai | Đếm lỗi báo nhưng kiểm lại không đúng | 0 lỗi nghiêm trọng |
| Lỗi đã sửa còn trên web thật | Chạy lại script sau deploy | 0 |
| Chỗ người dùng phải sửa tay hoặc hỏi lại | Đếm mỗi lần chạy | Giảm dần, về 0 |

## Sổ feedback

| Ngày | Chuyện gì xảy ra | Đã sửa gì |
|---|---|---|
| 06/11/2026 | Agent mới chạy thử bước 1 đến 4: tự tìm ra các lỗi đã biết và thêm vài lỗi mới. Lộ ra: mẫu 200 bỏ sót một trang gốc ngôn ngữ, thiếu lệnh Lighthouse, lỗi cấp site dễ bị bỏ qua, mẫu báo cáo không hợp ca chỉ audit | v2: `--sample 0`, thêm lệnh, mục lỗi cấp site, báo sai, mẫu báo cáo |
| 06/11/2026 | Tạo từ một ca thật. Mới có 1 lần chạy thật, người dùng yêu cầu làm skill ngay | v1 |

## Skill này phải tự tốt lên
1. **Eval sau mỗi lần chạy.** Thiếu bước nào thì sửa thẳng file này và thêm một dòng sổ.
2. **Thi thoảng lookup để update.** Tên bot, tên menu Cloudflare, loại rich result Google hỗ trợ đổi theo thời gian. Danh sách đã vài tháng tuổi thì kiểm lại ở tài liệu gốc.
3. **Có model mạnh hơn thì chạy lại ca thử.** Dòng nào không còn cần thì bỏ.
4. **Không biết thì hỏi người**, đừng đoán.
