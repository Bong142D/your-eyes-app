# UI Analysis — Your Eyes (innostar-demo.vercel.app)

> Ứng dụng đồng hành với kính AI "Your Eyes" dành cho người khiếm thị và người thân của họ (quản lý thiết bị, gói dịch vụ/thanh toán, an toàn & SOS, cộng đồng, hồ sơ/trợ năng).
>
> **Phương pháp phân tích:** Đây là ứng dụng Expo (React Native Web), render 100% phía client (SPA, không SSR) — chỉ 1 file `index.html` + 1 bundle JS. Do đó nội dung dưới đây được trích xuất trực tiếp từ mã nguồn đã bundle (giải mã toàn bộ chuỗi văn bản, route, dữ liệu mẫu) thay vì đọc màn hình đã render, để đảm bảo đúng 100% với những gì server trả về. Toàn bộ text tiếng Việt, tên route, dữ liệu mẫu (mock data), thông điệp popup trong tài liệu này đều lấy nguyên văn từ bundle.

---

## 1. Bản đồ điều hướng (Routes)

| # | Route | Màn hình | Ghi chú |
|---|-------|----------|---------|
| — | `/` | Mở đầu (trùng `/welcome`) | `app/index.tsx` render lại `WelcomeScreen`, không phải PosterBoardScreen |
| — | `/overview` | **PosterBoardScreen** | Trang tổng quan dạng "poster" hiển thị bản xem trước thu nhỏ (preview) của cả 12 màn hình theo luồng — trang demo/tài liệu thiết kế, **không phải** màn hình sản phẩm thật cho người dùng cuối. |
| 1 | `/welcome` | Mở đầu | Chào mừng & giới thiệu |
| 2 | `/auth` | Đăng nhập | Số điện thoại / Google |
| 3 | `/register` | Đăng ký | Tạo tài khoản mới |
| 4 | `/otp` | Xác thực OTP | Chỉ dùng khi đăng ký bằng SĐT |
| 5 | `/link-glasses` | Liên kết kính | Quét QR hoặc nhập serial |
| 6 | `/packages` | Gói dịch vụ | Chọn gói phù hợp nhu cầu |
| 7 | `/payment` | Thanh toán / Gia hạn | Chọn phương thức thanh toán |
| 8 | `/subscription` | Trạng thái thuê bao | Theo dõi tình trạng gói |
| 9 | `/transactions` | Lịch sử giao dịch | Xem hóa đơn & trạng thái |
| 10 | `/device` | Quản lý thiết bị | Thông tin & bảo mật thiết bị |
| 11 | `/support` | Hỗ trợ người dùng | Trợ giúp và liên hệ |
| 12 | `/main/family` | **An Toàn & SOS** | Theo dõi & báo động khẩn cấp |
| — | `/main` (+ 4 route con) | Khu vực chính có Tab Bar | Xem mục 2 |
| — | `/_sitemap` | Route hệ thống của Expo Router | Tự sinh, chỉ phục vụ dev, không phải màn hình sản phẩm |

`/main` là một Tab Navigator chứa 5 route con: `index`, `features`, `family`, `community`, `profile`.

---

## 2. Tab Bar (điều hướng dưới cùng, trong `/main`)

Thanh tab hiển thị **nhãn tiếng Anh**, nhưng tiêu đề nội dung bên trong mỗi màn hình lại là **tiếng Việt**:

| Icon | Nhãn trên Tab Bar | Route | Tiêu đề màn hình (hiển thị trong nội dung) |
|---|---|---|---|
| Home | `Home` | `/main` (index) | "Home" |
| Sparkles | `Features` | `/main/features` | "Tính năng" |
| Users | `Family` | `/main/family` | **"AN TOÀN"** (component nội bộ tên `SafetyScreen`) |
| Users2 | `Community` | `/main/community` | "Cộng đồng" |
| User | `Profile` | `/main/profile` | "Hồ sơ" |

Tab đang chọn: icon nằm trong nền tròn màu xanh mint nhạt; màu chữ/icon chủ đạo khi active là cyan.

---

## 3. Thành phần dùng chung (áp dụng cho hầu hết màn hình)

- **ScreenShell**: khung màn hình chuẩn — có nút Back (mũi tên quay lại) ở góc trên trái (ẩn bằng `hideBack` trên 5 màn hình tab chính), tiêu đề ở giữa, và có thể có 1 icon action ở góc phải (`right`) như bộ lọc, Bluetooth...
- **RowCard**: item danh sách dạng hàng (icon + tiêu đề + phụ đề + tuỳ chọn control bên phải: mũi tên, radio, switch, checkmark). Toàn bộ danh sách chức năng trong app dùng lại component này.
- **SectionLabel**: nhãn tiêu đề của từng nhóm nội dung trong màn hình (vd. "Quản lý", "Gọi nhanh", "Theo dõi"...).
- **notify()**: cơ chế **popup/thông báo duy nhất** trong toàn app. **Đã đối chiếu với source code gốc (`src/ui.tsx`)**: đây thực chất là `Alert.alert(title, message)` — **hộp thoại hệ thống dạng modal** (chặn tương tác, có nút OK), **không phải** toast/snackbar nổi như suy đoán ban đầu từ bundle đã minify. Tất cả các hành động "demo" (đăng bài, gọi điện, thêm liên hệ...) đều phản hồi bằng notify() vì đây là bản demo chưa nối API thật.

---

## 4. Chi tiết từng màn hình

### 4.0 PosterBoardScreen (`/overview`)
Trang tổng quan/demo, hiển thị 12 khung xem trước thu nhỏ nối tiếp nhau đại diện cho toàn bộ luồng ứng dụng (đánh số 1–12, mỗi khung có tiêu đề/phụ đề/link tới route thật — xem bảng mục 1). Dùng để review thiết kế, không phải nghiệp vụ cần dựng backend.

### 4.1 Mở đầu — Welcome (`/welcome`)
- Logo + 2 badge tính năng: "AI đồng hành" (icon Eye), "Voice Support" (icon Mic, tông màu success).
- Ảnh hero kính (glasses stage) có hiệu ứng vòng hào quang (halo).
- Tiêu đề: "Chào mừng đến với **Your Eyes**"; mô tả: "Trợ lý AI thông minh giúp nghe - nhận biết - hỗ trợ bạn trong cuộc sống hằng ngày."
- **Nút chính "Bắt đầu"** → điều hướng vào luồng đăng ký/đăng nhập.
- **Link text "Tôi đã có tài khoản"** → `/auth`.

### 4.2 Đăng nhập — Auth (`/auth`)
- Tiêu đề "Chào mừng bạn trở lại" / phụ đề "Trợ lý AI thông minh cho người khiếm thị".
- **Form nhập số điện thoại**: Người dùng nhập SĐT đã đăng ký.
- **Nút "Đăng nhập bằng số điện thoại"** (icon Phone) → gọi API `POST /accounts/login`. Nếu SĐT hợp lệ, điều hướng đến `/otp` với `purpose: 'login'`.
- **RowCard "Đăng nhập với Google"** (subtitle "Tiếp tục bằng Google", icon Mail, tông đỏ Google) → (Chưa tích hợp).
- **Link "Đăng ký ngay"** → `/register`.

### 4.3 Đăng ký — Register (`/register`)
- Tiêu đề "Tạo tài khoản Your Eyes" / phụ đề "Bắt đầu hành trình cùng trợ lý AI thông minh".
- **Form nhập số điện thoại**: Người dùng nhập SĐT mới.
- **Nút "Đăng ký bằng số điện thoại"** → gọi API `POST /accounts/register`. Nếu SĐT hợp lệ, điều hướng đến `/otp` với `purpose: 'register'`.
- **RowCard "Đăng ký với Google"** (subtitle "Tiếp tục bằng Google") → (Chưa tích hợp).
- **Link "Đăng nhập"** → `/auth`.

### 4.4 Xác thực OTP (`/otp`)
- Icon khiên khoá (LockKeyhole) trong gradient.
- Text: "Chúng tôi đã gửi mã OTP đến" + số điện thoại được truyền từ màn hình trước.
- **Form**: Ô nhập mã OTP gồm 6 chữ số.
- "Gửi lại mã sau" + đếm ngược.
- **Nút "Xác nhận"** → gọi API `POST /accounts/verify-otp` với SĐT, mã OTP và `purpose` ('login' hoặc 'register'). Nếu thành công, lưu token và vào `/main`.
- **Link "Đổi số điện thoại"** → quay lại màn hình trước.

### 4.5 Liên kết kính — Link Glasses (`/link-glasses`)
- Ảnh hero + "Chọn cách liên kết kính Your Eyes của bạn".
- **2 lựa chọn dạng thẻ chọn 1 (radio-card)**: "Quét QR" (subtitle "Quét mã QR trên kính") và "Nhập serial number" (subtitle "Nhập số serial của thiết bị").
  - Nếu chọn **Quét QR** → hiện khung quét camera với 4 góc ngắm + text "Đưa mã QR trên kính vào khung hình".
  - Nếu chọn **Nhập serial** → hiện **form nhập liệu**: label "Số serial (in ở gọng kính)", input text, placeholder **"VD: YE-2A4B-9F70"**.
- **Nút "Xác nhận liên kết"** → set trạng thái đã liên kết, vào `/main`.
- **Chốt luồng backend:** không cần thêm bước "nhập mã kích hoạt" riêng — mã QR in trên kính về bản chất chỉ là serial number được mã hoá thành QR để nhập nhanh hơn, nên backend chỉ cần 1 API xác thực theo `serial_number` dùng chung cho cả 2 cách nhập.

### 4.6 Home (`/main`, tab "Home")
- Lời chào "Chào bạn 👋" + "Truy cập nhanh các chức năng của Your Eyes".
- Nếu **chưa liên kết kính**: thẻ cảnh báo "Bạn chưa liên kết kính Your Eyes" + mô tả + **nút "Liên kết kính ngay"** → `/link-glasses`.
- **Section "Quản lý"** — danh sách RowCard điều hướng:
  | Tiêu đề | Phụ đề | Route |
  |---|---|---|
  | Quản lý thiết bị | Pin, kết nối & bảo mật kính | `/device` |
  | Gói dịch vụ | Xem & nâng cấp gói đang dùng | `/packages` |
  | Trạng thái thuê bao | Theo dõi ngày hết hạn | `/subscription` |
  | Lịch sử giao dịch | Hóa đơn & thanh toán | `/transactions` |
  | Hỗ trợ | Hotline & câu hỏi thường gặp | `/support` |

### 4.7 Tính năng — Features (`/main/features`)
- Tiêu đề "Tính năng nổi bật" / phụ đề "Trợ lý AI Your Eyes đồng hành cùng bạn mỗi ngày".
- Danh sách 5 thẻ tính năng (không tương tác — mang tính giới thiệu):
  1. **Nhận biết môi trường** — AI mô tả vật thể, người quen và không gian xung quanh theo thời gian thực.
  2. **Tìm kiếm định vị** — Định vị vị trí hiện tại và dẫn đường an toàn đến điểm đến.
  3. **Tiếp cận thông tin** — Đọc to văn bản, biển báo, nhãn sản phẩm và tài liệu.
  4. **Di chuyển an toàn** — Cảnh báo chướng ngại vật, bậc thang và nguy hiểm phía trước.
  5. **Sinh hoạt cá nhân** — Nhận diện tiền, màu sắc và vật dụng trong sinh hoạt hằng ngày.

### 4.8 "AN TOÀN" — Safety / SOS (`/main/family`, tab "Family")
> **Đây là màn hình được yêu cầu chỉnh sửa — xem chi tiết & thay đổi ở mục 7.**

- Tiêu đề màn hình: **"AN TOÀN"**.
- **Nút SOS**: hình tròn lớn, gradient hồng→đỏ (`#FF8A8A` → đỏ cảnh báo), icon dấu sao (Asterisk), chữ "SOS" ở giữa.
  - Khi nhấn (demo: `onPress`, không phải giữ) → hiện **popup (Alert.alert)**: *"Đã gửi tín hiệu SOS và vị trí của bạn cho người thân!"* (tiêu đề hộp thoại: "SOS").
  - **Chú thích dưới nút**: "Nhấn 3 lần để báo động" *(đã sửa từ "Giữ 3 giây để báo động" trong bản demo gốc)*.
  - **Chốt luồng backend (không có app/màn hình riêng cho người thân):** "gửi cho người thân" = gửi **SMS + push notification** kèm link xem vị trí tới các số điện thoại trong danh sách liên hệ khẩn cấp (mục "Người thân & liên hệ khẩn cấp" ở Profile). Người thân không cần tài khoản/app riêng để nhận SOS.
- **Section "Gọi nhanh"** — 3 RowCard gọi nhanh:
  | Tiêu đề | Phụ đề | Ghi chú |
  |---|---|---|
  | Gọi Mẹ | Số điện thoại chính | tông cyan |
  | Gọi Anh | Liên hệ khẩn cấp | tông cyan |
  | Gọi 115 | Cấp cứu y tế | tông đỏ, viền đỏ |

  → khi nhấn, hiện popup "Đang gọi {Mẹ/Anh/115}...".
- **Section "Theo dõi"**:
  - Thẻ **"VỊ TRÍ HIỆN TẠI"** (icon ghim bản đồ): địa chỉ mẫu "123 Đường Trần Hưng Đạo, Quận 1, TP.HCM"; trạng thái "Đang di chuyển" kèm chấm tròn trạng thái; thời điểm cập nhật "2 phút trước".
  - Thẻ **"NHẬT KÝ HOẠT ĐỘNG HÔM NAY"**: danh sách mốc hoạt động, mỗi dòng có icon (dấu tick nếu xong / dấu chân nếu đang diễn ra) + tiêu đề + giờ:
    - "Đã tới Công viên" — 08:30 (hoàn thành)
    - "Bắt đầu đi dạo" — 08:00 (đang diễn ra)

### 4.9 Cộng đồng — Community (`/main/community`)
- Hero banner gradient xanh: icon Users2, "Cộng đồng Your Eyes", "12.500 thành viên đang kết nối".
- **Nút "Đăng bài mới"** (icon Plus) → popup "Đăng bài đang được phát triển".
- **Section "Nhóm hỗ trợ"** — 3 RowCard nhóm (nhấn để tham gia → popup `Đã tham gia nhóm "{tên nhóm}"`):
  | Nhóm | Thành viên |
  |---|---|
  | Người mới dùng kính | 1.240 thành viên |
  | Mẹo sử dụng hàng ngày | 890 thành viên |
  | Dành cho người thân | 540 thành viên |
- **Section "Bài viết nổi bật"** — thẻ bài viết (tác giả · thời gian, tiêu đề, đoạn trích, **nút "Nghe bài viết"** (icon loa) → popup "Đang đọc: {tiêu đề}"):
  1. Cô Lan · 2 giờ trước — "Cách chỉnh giọng đọc dễ nghe hơn"
  2. Anh Minh · Hôm qua — "Kính giúp mình tự đi xe buýt"
  3. Chị Hoa (người thân) · 2 ngày trước — "Mẹo giúp người thân yên tâm hơn"
- **Section "Sự kiện sắp tới"** — RowCard sự kiện (nhấn → popup "Đã lưu sự kiện: {tên sự kiện}"):
  | Sự kiện | Thời gian | Địa điểm |
  |---|---|---|
  | Hướng dẫn sử dụng kính Your Eyes | Thứ 7, 26/07 · 09:00 | Trực tuyến qua Zoom |
  | Gặp mặt cộng đồng TP.HCM | Chủ nhật, 03/08 · 14:00 | Q.1, TP.HCM |

### 4.10 Hồ sơ — Profile (`/main/profile`)
- Header: avatar, tên mẫu **"Nguyễn Văn A"**, số điện thoại mẫu **"090 123 4567"**, **nút "Sửa"** → popup "Chỉnh sửa hồ sơ đang được phát triển".
- **Section "Trợ năng"** (Accessibility):
  - **Cỡ chữ** — chọn 1 trong 3: Nhỏ / Vừa / To (segmented control).
  - **Giọng đọc** — chọn 1 trong 2: Giọng Nữ / Giọng Nam (segmented control).
  - **Tương phản cao** — công tắc bật/tắt (switch).
  - **Phản hồi rung** — công tắc bật/tắt (switch).
- **Section "Người thân & liên hệ khẩn cấp"** — danh sách liên hệ mẫu: **"Mẹ" — 090 111 2222**, **"Anh" — 090 333 4444** *(đã sửa lại đúng theo source — 2 số này khác với số điện thoại của chính chủ tài khoản ở header)*, nhấn vào 1 liên hệ → popup "Chỉnh sửa liên hệ {tên}". **Nút "Thêm liên hệ"** (icon Plus) → popup "Thêm liên hệ khẩn cấp đang được phát triển".
- **Section "Tài khoản"** — RowCard điều hướng: "Gói dịch vụ" → `/packages`, "Thiết bị liên kết" → `/device`, "Hỗ trợ" → `/support`.
- **Nút "Đăng xuất"** → popup "Đã đăng xuất" **rồi điều hướng về `/auth`** (đã xác nhận qua source: `notify('Đã đăng xuất'); router.push('/auth')`).

### 4.11 Gói dịch vụ — Packages (`/packages`)
- **Tab chọn chu kỳ**: "Tháng" / "Năm".
- **3 gói dịch vụ** (thẻ, nhấn vào 1 gói → `/payment`):
  | Gói | Giá/tháng | Tháng đầu | Tính năng |
  |---|---|---|---|
  | Free | Miễn phí | — | Tính năng cơ bản; Giới hạn số lần dùng mỗi ngày |
  | Basic *(nổi bật)* | 99.000đ | 29.000đ | Bao gồm tính năng gói cơ bản; Tăng giới hạn số lần dùng mỗi ngày; Ưu tiên xử lý AI; Hỗ trợ trong ngày |
  | Pro | 199.000đ | 49.000đ | Bao gồm tất cả tính năng gói Basic; Ưu tiên sử dụng các tính năng mới ra mắt; Không giới hạn số lần dùng mỗi ngày; Ưu tiên xử lý AI |
- Giá hiển thị đổi theo chu kỳ Tháng/Năm (Năm = giá tháng × 12), có ghi chú "Thanh toán hàng tháng"/"Thanh toán hàng năm"/"Miễn phí sử dụng".
- **Link "So sánh chi tiết tính năng ›"** → popup "Bảng so sánh chi tiết đang được phát triển".
- **Chốt luồng backend (đặt tên gói):** giữ nguyên **Free / Basic / Pro** làm 3 gói hiển thị cho người dùng cá nhân trên UI (không đổi theo APP.md). **B2B Licensing** (APP.md) là một **kênh kinh doanh riêng ở tầng backend** — doanh nghiệp/tổ chức tài trợ mua gói Pro/Premium cho người dùng theo chương trình từ thiện — không cần màn hình chọn gói riêng cho người dùng cuối, chỉ cần backend hỗ trợ gán gói qua kênh B2B (vd. mã tài trợ, `sponsor_org_id`).
- **⚠️ Lỗi cần sửa trong sản phẩm (không phải do backend):** Payment, Subscription và Transactions đang hard-code tên gói là **"Premium Subscription"** bất kể người dùng chọn Free/Basic/Pro ở màn này — cần sửa để hiển thị đúng tên gói đã chọn.

### 4.12 Thanh toán / Gia hạn — Payment (`/payment`)
- Thẻ tóm tắt: "Gói đã chọn" — **"Premium Subscription"**, giá **"990.000đ /năm"**.
- **Form mã giảm giá**: ô nhập "Mã giảm giá" (placeholder "Nhập mã giảm giá") + **nút "Áp dụng"** → popup "Đã áp dụng mã giảm giá".
- **Section "Phương thức thanh toán"** — chọn 1 trong 4 (radio):
  1. Thẻ tín dụng / Ghi nợ — Visa, Mastercard
  2. MoMo — Ví điện tử
  3. ZaloPay — Thanh toán nhanh
  4. Chuyển khoản ngân hàng — Internet banking
- **Nút "Chuyển sang cổng thanh toán"** → `/subscription`.
- Dòng chú thích bảo mật: "Giao dịch được bảo mật với SSL 256-bit".

### 4.13 Trạng thái thuê bao — Subscription (`/subscription`)
- 3 thẻ trạng thái mẫu (minh hoạ 3 trạng thái khả dĩ của gói):
  | Trạng thái | Ngày | Số/đơn vị |
  |---|---|---|
  | Còn hạn | Hết hạn vào 20/07/2025 | 28 còn lại |
  | Sắp hết hạn | Hết hạn vào 04/07/2025 | 3 còn lại |
  | Quá hạn | Hết hạn từ 15/05/2025 | -10 ngày |
- **"Nhắc nhở gia hạn"** — công tắc bật/tắt + mô tả "Chúng tôi sẽ gửi thông báo trước khi gói gần hết hạn." (mặc định bật).
- **Nút "Vào ứng dụng"** → `/main`.

### 4.14 Lịch sử giao dịch — Transactions (`/transactions`)
- Icon bộ lọc ở góc phải header → popup "Bộ lọc nâng cao đang được phát triển".
- **Nút lọc "Tất cả ⌄"** → popup "Bộ lọc: Tất cả trạng thái".
- Danh sách giao dịch (nhấn 1 dòng → popup hiện `{tên gói} · {số tiền}`):
  | Mã hoá đơn | Gói | Số tiền | Ngày | Trạng thái |
  |---|---|---|---|---|
  | INV-2025-000123 | Premium Subscription / năm | 990.000đ | 23/06/2025 12:00 | Đã thanh toán |
  | INV-2025-000122 | Premium Subscription / năm | 990.000đ | 22/06/2025 10:31 | Đã thanh toán |
  | INV-2025-000121 | One Day Premium | 247.500đ | 21/06/2025 08:18 | Đang xử lý |
  | INV-2025-000120 | Premium Upgrade | 990.000đ | 20/06/2025 18:05 | Thất bại |
  | INV-2025-000119 | Trial Activation | 0đ | 19/06/2025 09:00 | Miễn phí |
- **Link "Kéo xuống để tải thêm"** → popup "Đã tải thêm giao dịch" (mô phỏng phân trang / infinite scroll).

### 4.15 Quản lý thiết bị — Device (`/device`)
- Icon Bluetooth ở góc phải header → popup "Đang tìm thiết bị Bluetooth...".
- Thẻ thiết bị: tên **"Kính Your Eyes"**, trạng thái "● Đã kết nối", pin **82%**, ảnh kính, "Serial: YE-2A4B-9F70 · Firmware: v2.1.4".
- 3 chỉ số nhanh: Pin 82% / Bluetooth ON / Bảo mật OK.
- **Lưới 5 hành động nhanh** (mỗi nút → popup theo tiêu đề tương ứng):
  | Hành động | Mô tả |
  |---|---|
  | Định vị | Tìm kính gần nhất |
  | Khóa thiết bị | Ngăn truy cập trái phép |
  | Báo mất | Kích hoạt cảnh báo |
  | Đặt lại thiết bị | Khôi phục cấu hình (factory reset — không đổi thiết bị vật lý) |
  | **Đổi kính** *(bổ sung theo APP.md)* | Chuyển quyền sở hữu tài khoản sang kính vật lý mới; set `device_status = replaced` cho kính cũ |
- **Section "Bảo mật"**:
  - "Mã hóa dữ liệu" — "Đảm bảo sự riêng tư tuyệt đối" (đã bật, có dấu tick) → nhấn: popup "Mã hóa dữ liệu đang bật".
  - "Xác thực 2 lớp" — "Tăng cường bảo vệ tài khoản" (đã bật, có dấu tick) → nhấn: popup "Xác thực 2 lớp đang bật".
- **Chốt luồng backend (kết nối thiết bị):** demo chỉ hiển thị trạng thái **Bluetooth** (kính ghép đôi qua điện thoại), nhưng theo quyết định sản phẩm, kính cần có **SIM/4G riêng** để SOS/định vị hoạt động độc lập không phụ thuộc điện thoại ở gần. Màn hình này cần bổ sung thêm 1 chỉ số "Kết nối mạng (SIM/4G)" bên cạnh Bluetooth, và backend cần lưu `sim_status`, `last_seen_at` như APP.md mô tả.

### 4.16 Hỗ trợ — Support (`/support`)
- Banner gradient "Hotline 24/7" — số **"1900 1234"** — "Hỗ trợ nhanh chóng mọi lúc" → nhấn: popup "Đang gọi 1900 1234...".
- Danh sách hỗ trợ (RowCard, mỗi dòng có nhãn hành động riêng, nhấn → popup `{phụ đề}` với tiêu đề `{hành động}: {tiêu đề}`):
  | Tiêu đề | Phụ đề | Nhãn nút |
  |---|---|---|
  | Hướng dẫn sử dụng | Tìm hiểu cách sử dụng kính Your Eyes hiệu quả | Mở |
  | Câu hỏi thường gặp (FAQ) | Giải đáp các thắc mắc phổ biến | Xem |
  | Phản hồi lỗi | Báo cáo lỗi thường gặp hoặc cảnh báo | Gửi |
  | Gửi yêu cầu hỗ trợ | Đội ngũ hỗ trợ sẽ liên hệ sớm nhất | Tạo |

---

## 5. Tổng hợp — Tabs

| Vị trí | Tabs |
|---|---|
| Tab Bar chính (`/main`) | Home · Features · Family · Community · Profile |
| Tab phụ trong "Gói dịch vụ" | Tháng · Năm |

## 6. Tổng hợp — Nút bấm (Buttons) chính theo màn hình

| Màn hình | Nút / hành động |
|---|---|
| Welcome | Bắt đầu; "Tôi đã có tài khoản" |
| Auth | Đăng nhập bằng số điện thoại; Đăng nhập với Google |
| Register | Đăng ký bằng số điện thoại; Đăng ký với Google |
| OTP | Xác nhận; Đổi số điện thoại |
| Link Glasses | Quét QR / Nhập serial number (chọn 1); Xác nhận liên kết |
| Home | Liên kết kính ngay; 5 RowCard "Quản lý" |
| AN TOÀN (Family) | **Nút SOS**; 3 nút "Gọi nhanh" (Gọi Mẹ/Anh/115) |
| Community | Đăng bài mới; 3 nút tham gia nhóm; 3 nút "Nghe bài viết"; 2 nút lưu sự kiện |
| Profile | Sửa (hồ sơ); Thêm liên hệ; Đăng xuất; các RowCard Tài khoản |
| Packages | Chọn gói (x3); So sánh chi tiết tính năng |
| Payment | Áp dụng (mã giảm giá); chọn phương thức (x4); Chuyển sang cổng thanh toán |
| Subscription | Vào ứng dụng |
| Transactions | Tất cả (bộ lọc); icon bộ lọc nâng cao; Kéo xuống để tải thêm |
| Device | icon Bluetooth; 5 hành động nhanh (gồm **Đổi kính**); Mã hóa dữ liệu; Xác thực 2 lớp |
| Support | Hotline 24/7; Mở / Xem / Gửi / Tạo (4 mục) |

## 7. Tổng hợp — Form (nhập liệu)

| Màn hình | Trường nhập liệu |
|---|---|
| OTP | 6 ô số OTP (demo tĩnh) |
| Link Glasses | Ô nhập "Số serial" — placeholder "VD: YE-2A4B-9F70" |
| Payment | Ô nhập "Mã giảm giá" — placeholder "Nhập mã giảm giá" |
| Profile | Segmented control "Cỡ chữ" (Nhỏ/Vừa/To); Segmented control "Giọng đọc" (Nữ/Nam); Switch "Tương phản cao"; Switch "Phản hồi rung" |
| Subscription | Switch "Nhắc nhở gia hạn" |

## 8. Tổng hợp — Popup (cơ chế `notify()` = `Alert.alert`)

Toàn bộ phản hồi trong app dùng **1 cơ chế duy nhất**: hộp thoại hệ thống `Alert.alert(title, message)` (modal, chặn thao tác, có nút OK) — xem lại mục 3.

| Thông điệp popup | Xuất hiện tại |
|---|---|
| Đã gửi tín hiệu SOS và vị trí của bạn cho người thân! | AN TOÀN — nhấn nút SOS |
| Đang gọi {Mẹ/Anh/115}... | AN TOÀN — Gọi nhanh |
| Đã tải thêm giao dịch | Transactions |
| Bộ lọc: Tất cả trạng thái / Bộ lọc nâng cao đang được phát triển | Transactions |
| {tên gói} · {số tiền} | Transactions — nhấn 1 giao dịch |
| Đang tìm thiết bị Bluetooth... | Device |
| Mã hóa dữ liệu đang bật / Xác thực 2 lớp đang bật | Device |
| {phụ đề hành động} (vd. "Tìm kính gần nhất") | Device — 4 hành động nhanh |
| Đang gọi 1900 1234... | Support |
| {phụ đề}: {hành động}: {tiêu đề} | Support — 4 mục hỗ trợ |
| Bảng so sánh chi tiết đang được phát triển | Packages |
| Đã áp dụng mã giảm giá | Payment |
| Đăng bài đang được phát triển | Community |
| Đã tham gia nhóm "{tên nhóm}" | Community — Nhóm hỗ trợ |
| Đang đọc: {tiêu đề}, tiêu đề hộp thoại "Nghe bài viết" | Community — Bài viết nổi bật |
| Đã lưu sự kiện: {tên sự kiện} | Community — Sự kiện sắp tới |
| Chỉnh sửa hồ sơ đang được phát triển | Profile |
| Chỉnh sửa liên hệ {tên} | Profile — Người thân & liên hệ khẩn cấp |
| Thêm liên hệ khẩn cấp đang được phát triển | Profile |
| Đã đăng xuất (sau đó điều hướng về `/auth`) | Profile — Đăng xuất |

## 9. Tổng hợp — Luồng người dùng (User Flows)

**Luồng 1 — Onboarding (người dùng mới):**
`Welcome → Auth/Register → (OTP nếu đăng ký bằng SĐT) → Link Glasses (Quét QR / Nhập serial) → /main`

**Luồng 2 — Đăng ký gói dịch vụ / gia hạn:**
`Home hoặc Profile → Packages (chọn Tháng/Năm, chọn gói) → Payment (mã giảm giá, chọn phương thức) → Subscription ("Vào ứng dụng") → /main`

**Luồng 3 — SOS khẩn cấp (màn hình "AN TOÀN"):**
`Tab Family → nhấn nút SOS → backend gửi SMS + push notification kèm vị trí tới các số điện thoại liên hệ khẩn cấp (hộp thoại Alert xác nhận trong app)`
Luồng phụ: `Tab Family → Gọi nhanh → chọn liên hệ (Mẹ/Anh/115) → thực hiện cuộc gọi`
*(Người thân nhận SOS qua SMS/push, không cần đăng nhập app riêng.)*

**Luồng 4 — Theo dõi an toàn (bị động, chỉ xem):**
`Tab Family → xem "Vị trí hiện tại" + "Nhật ký hoạt động hôm nay"` (dữ liệu do kính/điện thoại người dùng gửi lên, xem mục 10 gợi ý backend).

**Luồng 5 — Quản lý thiết bị:**
`Home/Profile → Device → xem trạng thái pin/kết nối → thực hiện Định vị / Khóa thiết bị / Báo mất / Đặt lại thiết bị / Đổi kính`

**Luồng 6 — Xem lịch sử & hoá đơn:**
`Home/Profile → Transactions → lọc theo trạng thái → xem chi tiết từng hoá đơn → tải thêm (phân trang)`

**Luồng 7 — Tương tác cộng đồng:**
`Tab Community → tham gia nhóm hỗ trợ / nghe bài viết (text-to-speech) / lưu sự kiện / đăng bài mới`

**Luồng 8 — Tuỳ chỉnh trợ năng cá nhân:**
`Tab Profile → Trợ năng → chỉnh Cỡ chữ / Giọng đọc / Tương phản cao / Phản hồi rung` (áp dụng toàn app, dùng cho người khiếm thị/thị lực yếu)

**Luồng 9 — Quản lý liên hệ khẩn cấp:**
`Tab Profile → Người thân & liên hệ khẩn cấp → sửa/thêm liên hệ` (đây chính là danh sách hiển thị ở "Gọi nhanh" trong màn AN TOÀN)

**Luồng 10 — Đăng xuất:**
`Tab Profile → Đăng xuất`

---

## 10. Gợi ý dữ liệu/API cho backend (dựa trên UI quan sát được)

> Chỉ nêu những gì có bằng chứng rõ trong UI/dữ liệu mẫu — không suy đoán thêm ngoài phạm vi quan sát.

- **Auth**: đăng nhập/đăng ký bằng số điện thoại hoặc Google; xác thực OTP (mã 6 số, có hẹn giờ gửi lại).
- **Account/Profile**: tên, số điện thoại, avatar; cài đặt trợ năng (cỡ chữ: Nhỏ/Vừa/To; giọng đọc: Nữ/Nam; tương phản cao: bool; phản hồi rung: bool).
- **Emergency Contacts**: danh sách liên hệ khẩn cấp (tên, số điện thoại, vai trò/ghi chú) — dùng chung cho cả Profile và "Gọi nhanh" ở màn AN TOÀN. Số "115" có vẻ là hằng số hệ thống (cấp cứu y tế), không phải liên hệ do người dùng thêm. **Đây là danh bạ để gửi SMS/push, không phải tài khoản có quyền đăng nhập** — không cần role/app riêng cho "người thân".
- **SOS / Safety**: endpoint gửi tín hiệu SOS kèm toạ độ vị trí hiện tại → **gửi SMS + push notification** tới các số trong Emergency Contacts (không phải gửi qua 1 app/dashboard caregiver riêng); log vị trí realtime (địa chỉ, trạng thái "đang di chuyển"/"đứng yên", thời điểm cập nhật); nhật ký hoạt động theo mốc thời gian trong ngày (loại mốc: đã hoàn thành / đang diễn ra).
- **Device**: thông tin thiết bị kính (tên, serial, firmware, % pin, trạng thái kết nối Bluetooth **và SIM/4G riêng** để SOS/định vị hoạt động độc lập không cần điện thoại ở gần — theo APP.md), `last_seen_at`, `device_status` (active/locked/lost/**replaced**); hành động: định vị thiết bị, khoá từ xa, báo mất, đặt lại cấu hình (factory reset), **đổi kính** (chuyển sang thiết bị vật lý mới); cờ bảo mật (mã hoá dữ liệu, xác thực 2 lớp).
- **Subscription/Packages**: 3 gói hiển thị cho người dùng — Free/Basic/Pro — với giá theo tháng và ưu đãi tháng đầu, tính năng theo gói, chu kỳ Tháng/Năm; trạng thái thuê bao (còn hạn/sắp hết hạn/quá hạn) kèm số ngày còn lại/quá hạn; cờ "nhắc nhở gia hạn" (renewal_status = **Manual**, không auto-charge — người dùng tự bấm gia hạn qua Payment khi gần hết hạn). **B2B Licensing** là kênh gán gói Pro/Premium riêng cho tổ chức tài trợ, xử lý ở backend, không có UI chọn gói riêng.
- **Payment**: danh sách phương thức thanh toán (thẻ, MoMo, ZaloPay, chuyển khoản), áp mã giảm giá, tích hợp cổng thanh toán ngoài.
- **Transactions**: danh sách hoá đơn có phân trang (mã hoá đơn, tên gói, số tiền, ngày giờ, trạng thái: Đã thanh toán/Đang xử lý/Thất bại/Miễn phí), lọc theo trạng thái.
- **Community**: nhóm hỗ trợ (tên, số thành viên, trạng thái đã tham gia); bài viết (tác giả, thời gian, tiêu đề, nội dung, hỗ trợ đọc bằng giọng nói/text-to-speech); sự kiện (tên, thời gian, địa điểm/link online, trạng thái đã lưu); đăng bài mới.
- **Support**: hotline; danh sách mục hỗ trợ (hướng dẫn sử dụng, FAQ, báo lỗi, gửi yêu cầu hỗ trợ) — có thể cần một hệ ticket đơn giản cho "Gửi yêu cầu hỗ trợ" và "Phản hồi lỗi".

---

## 11. Đối chiếu với APP.md (các quyết định đã chốt)

APP.md là tài liệu spec ban đầu (chưa hoàn chỉnh), UI Analysis.md dựa trên bản demo UI thực tế — hai tài liệu có vài điểm lệch nhau, đã được rà soát và chốt hướng xử lý như sau:

| Điểm lệch | APP.md | Demo/UI Analysis (trước sửa) | Quyết định |
|---|---|---|---|
| Vai trò người thân/caregiver | Đề xuất thêm role "người thân/người hỗ trợ" | Không có màn hình/role nào cho người thân | **Không tạo app/role riêng** — SOS gửi qua SMS + push notification tới số điện thoại trong Emergency Contacts |
| Tên gói dịch vụ | Freemium / Premium Subscription / B2B Licensing | Free / Basic / Pro | **Giữ Free/Basic/Pro** trên UI; B2B Licensing là kênh backend riêng, không cần UI chọn gói |
| Kết nối thiết bị | Có `sim/4G status` (kết nối độc lập) | Chỉ có Bluetooth (phụ thuộc điện thoại) | **Bổ sung SIM/4G riêng** cho kính, độc lập với Bluetooth |
| Hành động thiết bị | `device_status` có giá trị `replaced` | Chỉ có Định vị/Khóa/Báo mất/Đặt lại (reset) | **Bổ sung hành động "Đổi kính"**, tách biệt với "Đặt lại thiết bị" (factory reset) |
| Liên kết kính | Serial number + **mã kích hoạt** | Quét QR + Nhập serial | **Giữ nguyên Quét QR + Nhập serial** — QR chỉ là serial được mã hoá, không cần mã kích hoạt riêng |

Các mục 4.5, 4.8, 4.11, 4.15 và mục 10 ở trên đã được cập nhật theo các quyết định này.

---

## 12. Ghi chú giới hạn

Đây là **bản demo tĩnh** (front-end only), tất cả dữ liệu (giao dịch, thiết bị, liên hệ, bài viết cộng đồng...) đều là dữ liệu mẫu hard-code trong mã nguồn, mọi thao tác chỉ hiện popup xác nhận chứ chưa gọi API thật. Danh sách trên phản ánh đúng những gì bản demo thể hiện tại thời điểm phân tích (30/07/2026).

Đã xác nhận trực tiếp qua repo nguồn (`vision-care-app-demo`, xem `docs/superpowers/specs/2026-07-22-family-safety-sos-design.md`): bản demo **chủ động không có** backend, geolocation thật hay logic gesture thật — đúng như tài liệu này mô tả, chỉ mang tính minh hoạ UI/UX.

**→ Tài liệu này không đủ để dựng backend một mình.** Các luồng nghiệp vụ thật, state machine, quy tắc, và danh sách điểm cần chốt được đặc tả riêng ở [BACKEND_FLOWS.md](backend/docs/BACKEND_FLOWS.md) (trong thư mục `backend/`, cùng với code backend thật — xem mục 11).
