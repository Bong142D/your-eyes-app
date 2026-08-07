# API Contract — Your Eyes Backend (billing-service)

> Tài liệu này dành cho **frontend/mobile team** tích hợp — khác với `BACKEND_FLOWS.md` (tài liệu nội bộ backend, có sơ đồ luồng/quyết định thiết kế). Đây là **hợp đồng API**: endpoint chính thức, request/response mẫu, mã lỗi, và **rõ ràng flow nào production-ready, flow nào còn mock**.
>
> Cập nhật lần cuối: 2026-07-31, khớp code `backend/billing/app.py`. Nếu code và tài liệu này lệch nhau, báo backend team ngay — đây phải luôn là nguồn đúng nhất cho frontend.

## Quy ước chung

| | |
|---|---|
| **Base URL (dev/local)** | `http://localhost:5005` (chạy qua `docker compose up billing-service`, xem `backend/docker-compose.yml`) |
| **Base URL (staging/production)** | **Chưa có** — repo mới chạy ở mức Docker Compose local, chưa deploy staging/prod. Khi có, cập nhật bảng này. |
| **Auth người dùng** | Header `Authorization: Bearer <token>` — token lấy từ `POST /accounts/verify-otp`. Hết hạn sau 30 ngày (`SESSION_TTL_SECONDS`, ENV). |
| **Auth admin** | Cùng cơ chế Bearer token người dùng, nhưng account phải có cờ `is_admin=true` (chưa có UI/API tự set — set tay qua backend). |
| **Auth service-to-service (S2S)** | Header `Authorization: Bearer <INTERNAL_API_KEY>` — dùng cho `/internal/api/*`. **Khác hoàn toàn** không gian giá trị với token người dùng dù chung tên header. |
| **Content-Type** | `application/json` cho mọi request có body. |
| **Định dạng lỗi** | `{"error": "<thông báo bằng tiếng Việt>"}` — **chưa chuẩn hoá mã lỗi dạng code** (xem mục "Việc cần làm thêm" cuối file). Đọc theo HTTP status code là chính. |
| **Định dạng thời gian** | ISO 8601 UTC, không có timezone suffix cố định (`datetime.utcnow().isoformat()`), vd. `"2026-08-30T07:16:43.985084"`. |

**Chú thích trạng thái mỗi endpoint:**
- ✅ **Production-ready** — logic nghiệp vụ thật, có test, không phụ thuộc dịch vụ ngoài chưa sẵn sàng.
- 🧪 **Mock** — trả kết quả giả lập (log, không gọi dịch vụ thật) hoặc phụ thuộc 1 service khác hiện chưa tồn tại/chưa sẵn sàng.

---

## 1. Auth Module

### `POST /accounts/register` ✅
Đăng ký tài khoản mới bằng SĐT — bước 1 (gửi OTP), chưa tạo account.
```json
// Request
{ "phone": "0912345678" }
// 200
{ "phone": "0912345678", "expires_in": 300, "otp": "715103" }
```
- `otp` **chỉ xuất hiện khi `BILLING_ENV != production`** 🧪 — vì chưa nối SMS provider thật. Production sẽ không có field này, OTP gửi qua SMS thật.
- Lỗi: `400` thiếu phone · `409` SĐT đã đăng ký · `429` gửi lại OTP quá sớm (cooldown 60s).

### `POST /accounts/login` ✅
Đăng nhập — cũng dùng OTP (chưa có mật khẩu). Giống hệt `/register` về response, khác là yêu cầu account đã tồn tại.
- Lỗi: `400` thiếu phone · `404` chưa có account · `429` cooldown.

### `POST /accounts/verify-otp` ✅
Xác thực OTP cho cả register và login — dùng chung endpoint, phân biệt bằng `purpose`.
```json
// Request
{ "phone": "0912345678", "code": "715103", "purpose": "register" }  // hoặc "login"
// 201 (register) / 200 (login)
{ "account_id": "4e3ef016...", "token": "Ov-k-qsPhR0..." }
```
- Lỗi: `400` thiếu field/purpose sai · `401` sai mã · `404` không có yêu cầu OTP · `410` OTP hết hạn · `429` sai quá số lần cho phép.

### `POST /accounts/logout` ✅
Header: `Authorization: Bearer <token>`. Thu hồi token hiện tại. → `204`. Lỗi: `401` thiếu token.

---

## 2. Device Management Module

### `POST /devices/link` ✅
Liên kết kính theo serial (quét QR hoặc nhập tay đều dùng API này — QR chỉ là serial mã hoá).
```json
// Request (cần token)
{ "serial_number": "YE-DEMO-0001" }
// 201
{ "device_id": "bcf5b1df...", "serial_number": "YE-DEMO-0001", "status": "active" }
```
- Lỗi: `401` thiếu/sai token · `400` thiếu serial · `404` serial không có trong catalog · `409` serial đã được liên kết.

### `GET /devices` ✅
Lấy danh sách các thiết bị đã liên kết với tài khoản. Cần token.
```json
// 200
[
  { "id": "bcf5b1df...", "account_id": "...", "serial_number": "YE-DEMO-0001", "status": "active",
    "battery": 82, "firmware": "v2.1.4", "last_seen_bluetooth_at": "...", "paired_at": "..." }
]
```
- Lỗi: `401` thiếu/sai token.

### `GET /devices/{device_id}` ✅
Thông tin đầy đủ thiết bị (cho màn Quản lý thiết bị). Cần token, phải là chủ thiết bị.
```json
// 200
{ "id": "...", "account_id": "...", "serial_number": "...", "status": "active",
  "battery": null, "firmware": null, "last_seen_bluetooth_at": null,
  "last_seen_cellular_at": null, "last_reset_at": null, "paired_at": "..." }
```
- Lỗi: `401` · `403` không phải chủ thiết bị · `404`.

### `POST /devices/{device_id}/request-action-otp` ✅
Xin OTP xác thực lại trước hành động nhạy cảm (Khoá/Báo mất/Đổi kính). Cần token, chủ thiết bị.
```json
// 200
{ "expires_in": 300, "otp": "123456" }  // otp chỉ có ở dev, giống /register
```

### `POST /devices/{device_id}/lock` ✅ · `POST .../report-lost` ✅ · `POST .../replace` ✅
Cần token (chủ thiết bị) **+** `otp_code` lấy từ `request-action-otp` ở trên.
```json
// Request /lock, /report-lost
{ "otp_code": "123456" }
// Request /replace
{ "otp_code": "123456", "new_serial_number": "YE-DEMO-0002" }
```
- `/lock` → `200 {device_id, status:"locked"}` (chỉ từ `active`, khác → `409`)
- `/report-lost` → `200 {device_id, status:"lost"}` (từ `active`/`locked`, khác → `409`)
- `/replace` → `201 {device_id: <id mới>, status:"active"}` — kính cũ chuyển `replaced` vĩnh viễn, không link lại được.
- Lỗi OTP dùng chung mã như `/accounts/verify-otp` (400/401/404/410/429).

### `POST /devices/{device_id}/unlock` ✅ · `POST .../recover` ✅ · `POST .../reset` ✅
Cần token (chủ thiết bị), **không cần** `otp_code` (ít nhạy cảm hơn nhóm trên).
- `/unlock`: `locked`→`active` (khác → `409`). `/recover`: `lost`→`active` (khác → `409`). `/reset`: factory reset, không đổi status/serial, luôn `200`.

### `POST /devices/{device_id}/seen` ✅ — device-to-backend, **không cần token**
Kính/điện thoại tự báo cáo kết nối định kỳ.
```json
{ "channel": "bluetooth", "battery": 77, "firmware": "v2.2.0" }  // channel: "bluetooth"|"cellular"
```
→ `204`. Lỗi: `400` channel sai · `404` thiết bị không tồn tại.

### `GET /devices/{device_id}/status` ✅ — device-to-backend, **không cần token**
Dùng bởi AI-gateway (Server Kính) để biết quota/quyền hạn trước khi xử lý AI.
```json
// 200
{ "tier": "pro", "subscription_valid": true, "quota_remaining": 2000,
  "allowed_intents": ["DOC_CHU","MO_TA_CANH"], "device_status": "active" }
```
- Lỗi: `404` không tìm thấy thiết bị.

### `POST /devices/{device_id}/consume` ✅ — device-to-backend, **không cần token**
Trừ 1 lượt quota AI. → `200 {quota_remaining: N}`. Lỗi: `403` thiết bị đang khoá/mất · `404`.

⚠️ **Chưa production-ready 100%**: `/status`, `/consume`, `/seen` chưa có xác thực riêng cho thiết bị (device secret/API key) — hiện ai cũng gọi được nếu biết `device_id`. Cần bổ sung trước khi lên production thật.

---

## 3. Subscription & Packages Module

### `GET /packages` ✅ — không cần token
```json
[
  { "tier": "free", "monthly_price": 0, "yearly_price": 0, "quota_limit": 20, "allowed_intents": ["DOC_CHU"] },
  { "tier": "basic", "monthly_price": 99000, "yearly_price": 1188000, "quota_limit": 200, "allowed_intents": ["DOC_CHU","MO_TA_CANH"] },
  { "tier": "pro", "monthly_price": 199000, "yearly_price": 2388000, "quota_limit": 2000, "allowed_intents": ["DOC_CHU","MO_TA_CANH"] }
]
```

### `GET /subscription` ✅ — cần token
```json
{ "tier": "pro", "purchased_tier": "pro", "expires_at": "2026-08-30T07:16:43", "status": "active" }
// status: "active" | "expiring_soon" (≤7 ngày) | "expired" (tier hạ về "free" ngay)
```
Lỗi: `401` · `404` chưa có subscription (không nên xảy ra — mọi account có subscription mặc định từ lúc tạo).

---

## 4. Payment/Billing Module

### `POST /payment/checkout` ✅ (bản thân logic thật) — cần token
```json
// Request
{ "tier": "pro", "billing_cycle": "monthly", "discount_code": "SALE20" }  // discount_code optional
// 201
{ "transaction_id": "...", "amount": 199000, "gateway_ref": "MOCKPAY-a19ca823a70b4565" }
```
- Lỗi: `401` · `400` tier/billing_cycle/discount_code sai.

### `POST /payment/webhook` 🧪 **Mock — chưa có cổng thanh toán thật**
Mô phỏng callback cổng thanh toán — **không cần token**, hiện phải gọi tay hoặc từ script test.
```json
{ "gateway_ref": "MOCKPAY-a19ca823a70b4565", "status": "paid" }  // hoặc "failed"
// 200
{ "transaction_id": "...", "status": "paid", "already_processed": false }
```
⚠️ **Chưa xác minh chữ ký webhook** — ai biết `gateway_ref` đều gọi được. Bắt buộc phải làm trước khi có gateway thật. Idempotent theo `gateway_ref` (gọi lại → `already_processed: true`).
- Lỗi: `400` thiếu field · `404` không tìm thấy giao dịch.

### `POST /admin/transactions/{id}/refund` ✅ — cần token admin
Trong vòng 7 ngày kể từ thanh toán. → `200 {transaction_id, status:"refunded"}`. Lỗi: `401`/`403` không phải admin · `404` · `409` không đủ điều kiện refund (chưa paid/đã refund/quá hạn).

### `GET /admin/transactions/stale-pending` ✅ — cần token admin
Liệt kê giao dịch `pending` quá 30 phút (nghi lỡ webhook) — dạng đối soát thu hẹp, chưa có gateway thật để đối soát 2 chiều đầy đủ.

---

## 5. Giao tiếp Server-to-Server (S2S) với Server Kính

### `POST /internal/api/v1/sos/trigger` ✅ (logic) — Auth: `Authorization: Bearer <INTERNAL_API_KEY>`
**Server Kính gọi backend này** khi phát hiện đủ 3 lần nhấn SOS ở kính.
```json
// Request
{ "device_id": "YE-DEMO-0001", "location": {"latitude": 10.776889, "longitude": 106.700833},
  "timestamp_utc": "2026-08-01T10:00:00Z" }
// 202
{ "status": "accepted" }
```
- `device_id` = **serial_number** (đã chốt, không phải ID nội bộ).
- Lỗi: `401` sai/thiếu key · `400` thiếu field · `404` device_id không tồn tại (chưa từng link).
- 🧪 **Bên trong mock**: SMS/Push/Robo-call chỉ là log giả lập (`SIMULATING_SMS`, `PUSH_NOTIFICATION_SENT`, `SIMULATING_ROBO_CALL`), chưa nối Twilio/Firebase thật.

### API do **Server Kính cung cấp** (backend này GỌI RA — Server Kính cần tự xây, xem `BACKEND_FLOWS.md §5.1d`)
🧪 **Phụ thuộc bên ngoài — hiện luôn thất bại vì Server Kính (`ocr-server-service`) chưa tồn tại trong hệ thống.** Backend tự động retry qua hàng đợi (`/admin/notifications/failed`, `/admin/notifications/retry-failed`), **không** làm hỏng request chính (pairing/thanh toán/refund vẫn trả về đúng dù notify thất bại).

| Endpoint (phía Server Kính) | Backend gọi khi nào |
|---|---|
| `POST /internal/api/v1/devices/subscription-status` `{device_id, subscription:{plan_id, status, expires_at}}` | Thanh toán `paid` → `status:"active"`; refund → `"cancelled"`; phát hiện hết hạn (lần đọc `/subscription` hoặc `/status` kế tiếp) → `"expired"` |
| `POST /internal/api/v1/devices/link-status` `{device_id, link_status:{status, changed_at}}` | `/devices/link` → `"linked"`; `/devices/{id}/replace` → `"unlinked"` (serial cũ) rồi `"linked"` (serial mới) |

---

## 6. Emergency Contacts

### `GET /emergency-contacts` ✅ · `POST /emergency-contacts` ✅ · `PATCH /emergency-contacts/{id}` ✅ · `DELETE /emergency-contacts/{id}` ✅
Tất cả cần token.
```json
// POST/PATCH request
{ "name": "Mẹ", "phone": "0911111111", "is_primary": true }
// GET response (mảng)
[{ "id": "...", "name": "Mẹ", "phone": "0911111111", "is_primary": true }]
```
- Chỉ 1 liên hệ là `is_primary=true` tại 1 thời điểm — đánh dấu người mới sẽ tự bỏ primary người cũ.
- `POST` → `201 {contact_id}`. `PATCH`/`DELETE` → `204`. Lỗi: `401` · `400` (POST thiếu name/phone) · `404` (không tìm thấy/không phải của mình).

---

## 7. SOS / Safety (App điện thoại)

### `POST /devices/{device_id}/sos/press` ✅ — cần token (chủ thiết bị)
Gọi lại mỗi lần người dùng nhấn nút SOS trên app — backend tự đếm.
```json
// 200 (chưa đủ 3 lần)
{ "press_count": 2, "triggered": false }
// 200 (đủ 3 lần trong 10 giây)
{ "press_count": 3, "triggered": true, "sos_event_id": "...", "location_token": "...",
  "deliveries": [{"contact_name":"Mẹ","phone":"...","channel":"sms","status":"sent"}, ...] }
```
🧪 Cửa sổ "3 lần/10 giây" là placeholder (ENV `SOS_PRESS_THRESHOLD`, `SOS_PRESS_WINDOW_SECONDS`), chưa phải số liệu sản phẩm chính thức. SMS/push mock như mục 5.

### `GET /sos/{location_token}` ✅ — **công khai, không cần token**
Người thân bấm link từ SMS để xem vị trí SOS.
```json
{ "id": "...", "lat": 10.776889, "lng": 106.700833, "status": "triggered", "created_at": "..." }
```
Hết hạn sau 24h (`LOCATION_LINK_TTL_HOURS`) → `404` giống hệt token sai (không phân biệt, tránh dò token).

---

## 8. Location & Activity Log

### `POST /devices/{device_id}/location` ✅ — device-to-backend, không cần token
`{"lat": 10.77, "lng": 106.70}` → `204`. Lỗi: `400` thiếu lat/lng · `404`.

### `GET /location/current` ✅ — cần token
```json
{ "lat": 10.776889, "lng": 106.700833, "status": "Đang di chuyển", "updated_at": "..." }
// status: "Đang di chuyển" | "Đứng yên", tính bằng khoảng cách 2 điểm gần nhất (ngưỡng 20m)
```
Lỗi: `401` · `404` chưa có dữ liệu vị trí.

### `POST /devices/{device_id}/activity-log` ✅ — device-to-backend
`{"title": "Bắt đầu đi dạo"}` → `204`. **Ghi thủ công, chưa auto-detect điểm đến (geofencing).**

### `GET /activity-log` ✅ — cần token
Mảng `[{title, recorded_at}]`, mới nhất trước.

---

## 9. Community Module

| Endpoint | Auth | Ghi chú |
|---|---|---|
| `GET /community/groups` | Không cần | `[{id, name, description, member_count}]` |
| `POST /community/groups/{id}/join` | Token | Tự do tham gia, không cần duyệt. `204`/`404` |
| `GET /community/posts` | Không cần | Mới nhất trước |
| `POST /community/posts` | Token | `{author_name, title, content}` → `201 {post_id}`. **Hiển thị ngay, không kiểm duyệt trước** |
| `GET /community/events` | Không cần | `[{id, title, event_time, location}]` |
| `POST`/`DELETE /community/events/{id}/save` | Token | `204`/`404`. **Không có nhắc nhở tự động** |
| `GET /community/events/saved` | Token | Sự kiện đã lưu của chính mình |

Tất cả ✅ production-ready logic (dữ liệu nhóm/sự kiện do admin nạp qua script `seed_content.py`, không phải API).

---

## 10. Support Module

| Endpoint | Auth | Ghi chú |
|---|---|---|
| `GET /support/articles?kind=guide\|faq` | Không cần | Nội dung tĩnh (nạp qua `seed_content.py`) |
| `POST /support/tickets` | Token | `{category: "bug_report"\|"support_request", description}` → `201 {ticket_id}` |
| `GET /support/tickets` | Token | Ticket của chính mình |
| `POST /support/hotline/call-log` | Không bắt buộc | Log lượt bấm gọi hotline |
| `GET /admin/support/tickets?status=` | Admin | Xem tất cả ticket |
| `PATCH /admin/support/tickets/{id}/status` | Admin | `{status: "open"\|"in_progress"\|"resolved"}` → `204` |

⚠️ Ticket **chưa gửi thông báo lại cho người dùng** khi đổi trạng thái (spec gốc có yêu cầu, chưa wire).

---

## 11. Admin — Hàng đợi thông báo Server Kính

### `GET /admin/notifications/failed` ✅ · `POST /admin/notifications/retry-failed` ✅ — cần token admin
Xem/gửi lại các lần báo Server Kính bị lỗi (mục 5). **Chưa có cron tự động** — phải gọi tay hoặc lên lịch riêng.

---

## Việc cần làm thêm trước khi coi là "production-ready" toàn diện

1. **Chuẩn hoá error response** — hiện tất cả chỉ là `{"error": "<message>"}` không có `code` — frontend đang phải so sánh chuỗi tiếng Việt để phân biệt lỗi, dễ vỡ khi đổi câu chữ. Đề xuất: `{"error": {"code": "PHONE_ALREADY_REGISTERED", "message": "..."}}`.
2. **Rate limit** cho `/accounts/register|login` (ngoài cooldown OTP đã có), `/support/tickets`, `/devices/{id}/request-action-otp`.
3. **Auth riêng cho thiết bị** (`/status`, `/consume`, `/seen`, `/location`, `/activity-log`) — hiện không cần token nào, chỉ cần biết `device_id`.
4. **Base URL staging/production** — chưa deploy ngoài Docker Compose local.
5. Xem thêm danh sách đầy đủ các điểm ❓ còn để ngỏ trong `BACKEND_FLOWS.md` mục 9 và 5.1e (checklist với Server Kính).
