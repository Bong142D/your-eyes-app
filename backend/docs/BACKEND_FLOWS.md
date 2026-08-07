# Backend Flows — Your Eyes

> **Vai trò của tài liệu này:** [UI Analysis.md](../../UI%20Analysis.md) mô tả *bản demo UI tĩnh* (đã xác nhận qua repo `vision-care-app-demo`: không có backend, không có logic thật, toàn bộ dữ liệu hard-code — xem `docs/superpowers/specs/2026-07-22-family-safety-sos-design.md` trong repo đó). Tài liệu này đặc tả **luồng nghiệp vụ thật** mà backend cần hiện thực hoá đằng sau các màn hình đó — kế thừa khung màn hình từ UI Analysis.md, khung module từ [APP.md](APP.md), và các quyết định đã chốt giữa 2 tài liệu.
>
> Quy ước: mỗi mục có **State machine** (nếu có), **Quy tắc nghiệp vụ**, **Trường hợp biên**, và **❓ Cần chốt** (những điểm chưa có đủ thông tin để quyết — không tự suy đoán số liệu cụ thể).

## Cấu trúc repo

```
your-eyes-project/
├── UI Analysis.md          ← chỉ tham khảo luồng/UI, KHÔNG phải nguồn sự thật cho logic
├── vision-care-app-demo/   ← app demo (frontend-only, xem UI Analysis.md), chỉ để tham khảo
└── backend/                ← nơi build backend THẬT, dựa trên tài liệu trong backend/docs/
    ├── docs/
    │   ├── APP.md            ← spec ban đầu (ý định thật của sản phẩm)
    │   └── BACKEND_FLOWS.md  ← tài liệu này — luồng nghiệp vụ thật, chi tiết
    ├── billing/               ← service thật đầu tiên: account/device/tier/quota (Flask + SQLite)
    └── docker-compose.yml
```

**Nguyên tắc:** khi code trong `backend/` xung đột với những gì `vision-care-app-demo/` hiển thị, **luôn ưu tiên tài liệu trong `backend/docs/`** — demo chỉ minh hoạ UI/luồng tham khảo, không phải đặc tả nghiệp vụ.

---

## 1. Auth Module

> **Trạng thái: ĐÃ CODE (Task 1, hoàn thành 2026-07-30).** Toàn bộ mục 1.1–1.4 dưới đây đã có code + test chạy thật trong `backend/billing/` (29/29 test pass). Phần 1.5 (Roles) chưa code, vẫn là spec.

### 1.0 File liên quan & vai trò của từng file

| File | Vai trò |
|---|---|
| `backend/billing/schema.sql` | Định nghĩa 3 bảng dùng cho Auth: `account` (phone), `otp_request` (mã OTP đang chờ xác thực), `session` (token đăng nhập còn hiệu lực). |
| `backend/billing/models.py` | Toàn bộ logic dữ liệu: tạo/tra `account` theo `phone`, sinh & xác thực OTP (`generate_otp`, `verify_otp`), tạo/tra/thu hồi session (`create_session`, `get_account_id_by_token`, `revoke_session`). Các hằng số OTP/session (TTL, số lần sai tối đa, cooldown...) khai báo ngay đầu file, đọc từ biến môi trường, có giá trị mặc định. |
| `backend/billing/app.py` | Route Flask expose ra HTTP: `POST /accounts/register`, `POST /accounts/login`, `POST /accounts/verify-otp`, `POST /accounts/logout`; đồng thời `POST /accounts/{id}/devices` (pairing) đã được gắn kiểm tra token ở đây. |
| `backend/billing/tiers.py` | Không thuộc Auth, nhưng được `models.py` gọi để gán gói mặc định (`tier=free`) ngay khi 1 account mới được tạo. |
| `backend/billing/tests/test_accounts.py` | Test HTTP end-to-end cho register/login/verify-otp/logout: luồng thành công + các lỗi (thiếu SĐT, trùng SĐT, sai OTP, 429 do gửi lại quá sớm). |
| `backend/billing/tests/test_otp.py` | Test trực tiếp `models.py` cho các trường hợp biên của riêng OTP: cooldown gửi lại, không tìm thấy yêu cầu OTP, hết hạn, sai quá số lần cho phép, dùng lại OTP đã tiêu (phải bị từ chối). |
| `backend/billing/tests/test_models.py` | Test trực tiếp `models.py` cho `account` + `session` (tạo, tra theo token, thu hồi). |
| `backend/billing/tests/test_devices.py` | Test pairing thiết bị có yêu cầu token: 401 nếu thiếu token, 403 nếu token thuộc account khác. |

### 1.1 Luồng Đăng ký (Register) — đã code

```
[App]                                    [Backend]
  |-- POST /accounts/register {phone} -------->|
  |                                             |  1) phone đã có account? --> 409
  |                                             |  2) generate_otp(phone, purpose="register")
  |                                             |     - còn OTP cũ trong lúc cooldown? --> 429
  |<-- 200 {phone, expires_in, otp*} -----------|
  |                                             |
  |-- POST /accounts/verify-otp --------------->|
  |   {phone, code, purpose:"register"}         |  verify_otp(): sai mã-->401, hết hạn-->410,
  |                                             |  quá số lần sai-->429, không có yêu cầu-->404
  |                                             |  đúng --> tạo account + subscription mặc định
  |                                             |           (tier=free) --> tạo session
  |<-- 201 {account_id, token} -----------------|
```
`*otp`: chỉ có trong response khi `BILLING_ENV != production` (mặc định dev) — xem 1.9.

**Quy tắc đã code:**
- 1 số điện thoại = 1 account (unique trên `account.phone`).
- OTP 6 số; sinh bằng `secrets.randbelow` (không đoán được).
- Gửi lại OTP trong lúc cooldown → lỗi rõ ràng `429`, không âm thầm bỏ qua hay lặng lẽ resend.
- OTP dùng 1 lần: xác thực đúng → đánh dấu `consumed_at`; gọi verify lại với cùng mã sẽ nhận `404` (not found), không dùng lại được.
- Tạo account thành công → tự tạo `subscription` mặc định tier `free`, hạn 30 ngày (logic có sẵn từ trước Task 1, không đổi).

**Trường hợp biên đã có test:**
- Đăng ký lại SĐT đã có account (đã xác thực xong) → `409`.
- Gửi `/register` 2 lần liên tiếp cho cùng SĐT **chưa xác thực xong** → `429` (cooldown), không phải `409` (vì account chưa thực sự được tạo cho tới khi verify-otp thành công).
- Nhập sai OTP quá `OTP_MAX_ATTEMPTS` lần → `429`, phải xin gửi lại mã mới.

### 1.2 Luồng Đăng nhập (Login) — đã code

```
[App]                                    [Backend]
  |-- POST /accounts/login {phone} ------------>|
  |                                             |  1) phone chưa có account? --> 404
  |                                             |  2) generate_otp(phone, purpose="login")
  |<-- 200 {phone, expires_in, otp*} -----------|
  |                                             |
  |-- POST /accounts/verify-otp --------------->|
  |   {phone, code, purpose:"login"}            |  verify_otp() (như trên) + tìm account theo phone
  |                                             |  --> tạo session mới (KHÔNG xoá session cũ)
  |<-- 200 {account_id, token} -----------------|
```

**Quyết định đã chốt cùng người dùng (thay cho ❓ cũ):** login dùng lại cơ chế OTP giống hệt register (tạm thời, cho tới khi có SMS provider thật và muốn đổi sang password/biometric — đổi sau không ảnh hưởng schema).

- Đăng nhập Google (OAuth) — **chưa code**, giữ nguyên mô tả spec: map theo email Google, chưa có account thì tạo mới như luồng register.

### 1.3 Đăng xuất (Logout) & Session/Token — đã code

```
POST /accounts/logout
Header: Authorization: Bearer <token>
  --> models.revoke_session(token): session.revoked_at = now()
  --> 204 No Content        (thiếu token trong header --> 401)
```

- **Token**: chuỗi ngẫu nhiên `secrets.token_urlsafe(32)`, lưu trong bảng `session` — **không phải JWT** (đơn giản, đủ dùng cho quy mô Flask + SQLite hiện tại; nâng cấp JWT là việc của tương lai, không thuộc Task 1).
- Chưa tách access/refresh token riêng — 1 token duy nhất cho mỗi lần đăng nhập thành công.
- Hỗ trợ **nhiều phiên đăng nhập cùng lúc**: mỗi lần verify-otp (register hoặc login) thành công tạo 1 session mới, không thu hồi session cũ — người dùng có thể đăng nhập trên nhiều thiết bị.
- Token bị thu hồi (logout) → `get_account_id_by_token()` trả `None` ngay từ lần gọi tiếp theo → mọi endpoint có kiểm tra token tự động chặn truy cập.

### 1.4 Bảo vệ endpoint bằng token — đã code (áp dụng cho pairing thiết bị)

*(Cập nhật 2026-08-02: route pairing thật từ Task 2 là `POST /devices/link {serial_number}` — lấy `account_id` từ token, không nhận qua URL — xem mục 2.1. Đoạn dưới mô tả nguyên tắc bảo vệ-bằng-token, vẫn đúng tinh thần dù route đã đổi.)*

`POST /devices/link` (pairing) hiện **bắt buộc** header `Authorization: Bearer <token>`:
- Thiếu token hoặc token không hợp lệ/hết hạn/đã bị thu hồi → `401`.
- `account_id` lấy từ chính token, không thể pairing hộ tài khoản khác.

**Cố tình CHƯA áp dụng cho** `/devices/{id}/status`, `/devices/{id}/consume`, `/devices/{id}/seen`, `/devices/{id}/location`, `/devices/{id}/activity-log` — đây là các cuộc gọi từ **thiết bị/kính** (device-to-backend), khác bản chất với token đăng nhập của người dùng trên điện thoại. Ép dùng token người dùng ở đây là 1 quyết định kiến trúc riêng (thiết bị cần cơ chế xác thực riêng, ví dụ device secret/API key). **Vẫn CHƯA quyết định tính đến 2026-08-02** — không tự ý đổi vì cần phối hợp với Server Kính (thiết bị cần biết secret ở đâu ra), xem `CONTRACT_SERVER_KINH.md` mục "Yêu cầu quan trọng" #4 và mục 9 checklist bên dưới.

### 1.5 Bảng dữ liệu đã tạo (`schema.sql`)

| Bảng | Cột chính | Ghi chú |
|---|---|---|
| `account` | `id (PK), phone (unique), created_at` | đổi từ `email` sang `phone` so với bản code cũ trước Task 1 |
| `otp_request` | `phone, purpose, code, attempts, created_at, expires_at, consumed_at` | PK = `(phone, purpose)` — mỗi SĐT chỉ có tối đa 1 OTP đang hiệu lực cho mỗi mục đích (register/login); gửi lại sẽ ghi đè (nếu qua cooldown) |
| `session` | `token (PK), account_id, created_at, expires_at, revoked_at` | `revoked_at` khác NULL nghĩa là đã đăng xuất |

### 1.6 API Endpoints đã code

*(Cập nhật 2026-08-02 — bảng dưới trước đó liệt kê sai route pairing (`/accounts/{account_id}/devices`, đã đổi thành `/devices/link` từ Task 2) và sai mã trạng thái `logout` (`204`→thực tế `200` kèm message); đã sửa lại đúng code hiện tại + bổ sung endpoint mới.)*

| Method | Path | Request body | Thành công | Lỗi |
|---|---|---|---|---|
| POST | `/accounts/register` | `{phone}` | `200 {phone, expires_in, otp*}` | `400` thiếu phone · `409` đã có account · `429` đang cooldown |
| POST | `/accounts/login` | `{phone}` | `200 {phone, expires_in, otp*}` | `400` thiếu phone · `404` chưa có account · `429` đang cooldown |
| POST | `/accounts/verify-otp` | `{phone, code, purpose}` | `201` (register) / `200` (login) `{account_id, token}` | `400` thiếu field · `401` sai mã · `404` không có yêu cầu OTP · `410` hết hạn · `429` sai quá số lần |
| POST | `/accounts/logout` | *(không cần body)* + header token | `200 {message}` | `401` thiếu token |
| GET | `/account` | *(không cần body)* + header token — **mới 2026-08-02** | `200 {id, phone, created_at, is_admin}` | `401` thiếu/sai token |
| POST | `/devices/link` | `{serial_number}` + header token | `201 {device_id, serial_number, status}` | `401` thiếu/sai token · `400` thiếu serial · `404` serial chưa xuất xưởng · `409` đã liên kết |

`*otp`: field này **chỉ xuất hiện khi `BILLING_ENV != production`** — độc lập với việc SMS thật có gửi hay không (xem cập nhật Twilio ở mục 5 và bảng ENV ở mục 1.8): kể cả khi Twilio đã cấu hình thật, field này vẫn hiện ở dev để tiện test không cần cầm điện thoại.

### 1.7 Roles — CHƯA code, giữ nguyên spec
Role admin/support chưa cần code ngay — nó chỉ phục vụ 2 việc: duyệt nội dung Community và xử lý ticket ở Hỗ trợ, tức là thuộc phạm vi Task 5/6 (Community, Support) — cuối lộ trình. Task 2/3/4 (Device, Subscription/Payment, SOS) đều chỉ thao tác trên role user, không đụng tới admin/support, nên để đó chưa ảnh hưởng gì.

- `user` (người khiếm thị — vai trò chính, duy nhất có trong UI hiện tại).
- `admin`, `support` — vai trò nội bộ vận hành (duyệt nội dung Community, xử lý ticket ở màn Hỗ trợ) — không có UI khách hàng tương ứng, chỉ cần ở backend/admin panel.
- **Không có role "caregiver/người thân"** (đã chốt ở UI Analysis.md mục 11) — người thân chỉ là **dữ liệu** (Emergency Contacts), nhận SOS qua SMS/push, không đăng nhập vào hệ thống.

### 1.8 Tham số cấu hình (đã có giá trị mặc định để chạy được, không phải quyết định sản phẩm chính thức)

| Tham số | Mặc định trong code | Đổi qua ENV |
|---|---|---|
| Độ dài OTP | 6 số | *(cố định, không đổi qua ENV)* |
| TTL của OTP | 300 giây (5 phút) | `OTP_TTL_SECONDS` |
| Số lần nhập sai OTP tối đa | 5 lần | `OTP_MAX_ATTEMPTS` |
| Cooldown gửi lại OTP | 60 giây | `OTP_RESEND_COOLDOWN_SECONDS` |
| TTL session token | 30 ngày | `SESSION_TTL_SECONDS` |

Đây là số liệu kỹ thuật hợp lý tạm thời để hệ thống chạy được ngay — có thể đổi bất cứ lúc nào bằng biến môi trường, không cần sửa code, và không nên coi là đã "chốt" về mặt sản phẩm cho tới khi có quyết định chính thức.

**Twilio (SMS + robo-call thật, mới 2026-08-02)** — dùng chung cho OTP (mục 1) và SOS (mục 5.1/5.1b):

| Biến ENV | Mặc định | Ghi chú |
|---|---|---|
| `TWILIO_ACCOUNT_SID` | *(rỗng)* | Chưa cấu hình → tự fallback mock/log, không lỗi. |
| `TWILIO_AUTH_TOKEN` | *(rỗng)* | Phải có đủ cả 3 biến SID/TOKEN/FROM_NUMBER mới coi là "đã cấu hình" (`models._twilio_configured()`). |
| `TWILIO_FROM_NUMBER` | *(rỗng)* | Số Twilio đã mua, dùng làm `from` cho cả SMS lẫn call. |
| `TWILIO_DEFAULT_COUNTRY_CODE` | `+84` | Dùng để đổi SĐT nội địa (`0912345678`) sang E.164 (`+84912345678`) trước khi gửi Twilio. |

**Tại thời điểm 2026-08-02: môi trường demo CHƯA có tài khoản Twilio thật** — toàn bộ vẫn chạy ở nhánh mock/log (`SIMULATING_SMS`, `SIMULATING_ROBO_CALL`), hành vi giống hệt trước khi tích hợp. Chỉ cần điền đủ 3 biến ENV, KHÔNG cần sửa code, là chuyển sang gửi thật ngay.

### 1.9 Cách tự test lại luồng này
```bash
cd backend/billing
python -m pytest -v          # 191 test toàn bộ backend/billing (cập nhật 2026-08-02);
                              # lệnh này chạy CẢ repo, không chỉ mục Auth — lọc riêng Auth:
                              # python -m pytest -v tests/test_accounts.py tests/test_models.py tests/test_otp.py

# hoặc test thủ công qua HTTP (cần chạy: python app.py):
curl -X POST http://localhost:5005/accounts/register -H "Content-Type: application/json" -d "{\"phone\":\"0912345678\"}"
curl -X POST http://localhost:5005/accounts/verify-otp -H "Content-Type: application/json" -d "{\"phone\":\"0912345678\",\"code\":\"<otp nhận được>\",\"purpose\":\"register\"}"
```

---

## 2. Device Management Module

> **Trạng thái: ĐÃ CODE (Task 2, hoàn thành 2026-07-30).** Toàn bộ 2.1–2.3 dưới đây đã có code + test chạy thật trong `backend/billing/` (41/41 test pass, gồm cả Task 1). Serial catalog vẫn seed thủ công (script), chưa có quy trình nhập hàng thật.

### 2.0 File liên quan & vai trò của từng file

| File | Vai trò |
|---|---|
| `backend/billing/schema.sql` | Thêm bảng `device_catalog` (serial đã xuất xưởng); mở rộng `device` với `serial_number, status, battery, firmware, last_seen_bluetooth_at, last_seen_cellular_at, last_reset_at`. |
| `backend/billing/models.py` | Toàn bộ logic: `add_catalog_serial`, `link_device` (pairing), `get_device`, `lock_device`/`unlock_device`/`report_lost`/`recover_device`/`factory_reset_device`/`replace_device` (state machine), `report_device_seen` (kết nối §2.3). Sửa `get_device_status` (thêm `device_status`) và `consume_quota` (chặn nếu thiết bị không `active`). |
| `backend/billing/app.py` | Route: `POST /devices/link`, `GET /devices/{id}`, `POST /devices/{id}/request-action-otp`, `.../lock`, `.../unlock`, `.../report-lost`, `.../recover`, `.../reset`, `.../replace`, `.../seen`. Sửa `.../status` và `.../consume` (đã có từ Task 1) để phản ánh trạng thái thiết bị. |
| `backend/billing/seed_catalog.py` | Script chạy tay để nạp serial mẫu (`YE-DEMO-0001..0005`) vào `device_catalog` cho môi trường dev — thay cho quy trình nhập hàng thật (xem ❓ cuối 2.1). |
| `backend/billing/tests/conftest.py` | Fixture `db_path`/`client` giờ tự seed sẵn `YE-TEST-0001..0005` vào catalog cho **mọi** test — không cần seed lại thủ công trong từng test. |
| `backend/billing/tests/test_devices.py` | Test pairing: link theo serial thành công, thiếu token (401), serial không có trong catalog (404), serial đã bị pairing (409), quyền sở hữu khi xem `GET /devices/{id}` (403 nếu không phải chủ). |
| `backend/billing/tests/test_device_lifecycle.py` | Test toàn bộ state machine: khoá/mở khoá, báo mất/khôi phục, đặt lại thiết bị, đổi kính, báo cáo kết nối (`/seen`) — bao gồm việc khoá/báo mất **chặn** `/consume` (403). |
| `backend/billing/tests/test_status.py`, `test_consume.py` | Cập nhật để pairing qua `/devices/link` (route mới) thay vì route cũ đã bỏ. |

### 2.1 Liên kết kính (Pairing) — đã code

```
[App]                                          [Backend]
  |-- POST /devices/link {serial_number} ----->|  Header: Authorization: Bearer <token>
  |                                            |  1) serial có trong device_catalog? --> 404 nếu không
  |                                            |  2) serial đã có device khác dùng? --> 409 nếu có
  |                                            |  3) tạo device: account_id = chủ token, status="active"
  |<-- 201 {device_id, serial_number, status} -|
```

**Quy tắc đã code:**
- QR chỉ là serial được mã hoá — dùng chung **1 API duy nhất** `POST /devices/link {serial_number}` cho cả quét QR lẫn nhập tay (đã chốt ở UI Analysis.md mục 11) — quyết định app quét QR rồi tự điền `serial_number` vào field này, backend không phân biệt nguồn nhập.
- `account_id` lấy từ **token đăng nhập** (`Authorization: Bearer`), không nhận qua body/URL — không thể pairing hộ tài khoản khác (khác hẳn route cũ trước Task 2 vốn nhận `account_id` qua URL).
- Serial phải có trong `device_catalog` mới pairing được (`SerialNotProvisionedError` → 404) — **đã chốt cách nạp catalog cho giai đoạn hiện tại**: seed thủ công qua `seed_catalog.py`, chưa nối với hệ thống nhà sản xuất thật.
- 1 serial chỉ thuộc 1 device tại 1 thời điểm (`SerialAlreadyLinkedError` → 409).

**❓ Còn để ngỏ (chưa đổi so với bản spec gốc):** quy trình nhập catalog thật từ nhà sản xuất (khi nào, ai nạp — hiện chỉ có script seed tay); có cần xác minh sở hữu vật lý bổ sung (mã trên hộp) không.

### 2.2 Device state machine — đã code

```
                    link                    lock                  report-lost
   (chưa có) ────────────▶ [active] ───────────────▶ [locked] ┐         │
                              │  ▲                              │        report-lost
                              │  └──────── unlock ───────────────┘        ▼
                              │                                        [lost]
                              │                                          │ recover
                              │◀─────────────────────────────────────────┘
                              │
                              ├── reset ──▶ [active]  (không đổi status/serial — chỉ ghi last_reset_at)
                              │
                              └── replace(new_serial) ──▶ device cũ: [replaced] (vĩnh viễn, không thể link lại)
                                                          + tạo device MỚI [active] với new_serial, cùng account
```

**Quy tắc đã code (mỗi hành động là 1 hàm trong `models.py`, kiểm tra đúng trạng thái nguồn mới cho chuyển — sai thì `InvalidTransitionError` → `409`):**

| Hành động | Endpoint | Điều kiện trạng thái nguồn | Cần OTP re-auth? |
|---|---|---|---|
| Khoá | `POST /devices/{id}/lock` | phải đang `active` | **Có** |
| Mở khoá | `POST /devices/{id}/unlock` | phải đang `locked` | Không |
| Báo mất | `POST /devices/{id}/report-lost` | đang `active` hoặc `locked` | **Có** |
| Khôi phục (tìm lại) | `POST /devices/{id}/recover` | phải đang `lost` | Không |
| Đặt lại thiết bị (factory reset) | `POST /devices/{id}/reset` | bất kỳ (không đổi status) | Không |
| Đổi kính | `POST /devices/{id}/replace` | không phải `replaced` | **Có** |

- **Đặt lại thiết bị ≠ Đổi kính** (đã phân biệt đúng như UI Analysis.md mục 4.15): `reset` chỉ ghi nhận `last_reset_at`, không đổi `status`/`serial_number`, không tạo device mới — vì backend hiện chưa lưu "cấu hình cá nhân" nào khác để thực sự xoá. `replace` thì đóng vĩnh viễn device cũ (`status=replaced`, serial cũ không bao giờ pairing lại được) và tạo device mới hoàn toàn với serial mới, cùng `account_id`.
- **Khoá/Báo mất/Đổi kính bắt buộc xác thực lại bằng OTP** (quyết định đã chốt cùng người dùng, khác dự định "chưa cần" ban đầu): gọi `POST /devices/{id}/request-action-otp` lấy mã (purpose nội bộ `"device_action"`, dùng lại đúng cơ chế OTP của Auth Module — xem mục 1), rồi gửi kèm `otp_code` trong body của lock/report-lost/replace. Thiếu `otp_code` → `400`; sai/hết hạn/quá số lần → cùng bộ mã lỗi như verify-otp ở mục 1.6.
- **Khoá thiết bị chặn tính năng AI thật sự**: `consume_quota()` (dùng bởi `/devices/{id}/consume`) giờ kiểm tra `device.status`, nếu khác `active` → `DeviceNotActiveError` → app trả `403 "Thiết bị đang bị khoá/báo mất, không thể sử dụng tính năng AI."`. `/devices/{id}/status` cũng trả thêm field `device_status` để app biết lý do.
- Toàn bộ endpoint trên (trừ `/seen`) đều qua `_require_own_device()`: thiếu/sai token → `401`, token đúng nhưng không phải chủ thiết bị → `403`, không tìm thấy thiết bị → `404`.

**❓ Còn để ngỏ:** hành vi chính xác của "Báo mất" ngoài việc đổi status + chặn AI — có cần thêm hành động cứng trên phần cứng (âm thanh, gửi vị trí cuối) không, đây là việc của SOS/Safety Module (mục 5) khi làm tới.

### 2.3 Kết nối & giám sát thiết bị — đã code

```
[Kính/thiết bị]                          [Backend]
  |-- POST /devices/{id}/seen -------------->|   (KHÔNG cần token người dùng — device-to-backend,
  |   {channel: "bluetooth"|"cellular",      |    giống /status và /consume ở mục 1.4)
  |    battery?, firmware?}                  |
  |                                          |   cập nhật last_seen_bluetooth_at HOẶC
  |                                          |   last_seen_cellular_at (theo channel),
  |                                          |   + battery/firmware nếu có gửi kèm
  |<-- 204 No Content ------------------------|
```

**Quy tắc đã code:**
- 2 kênh kết nối lưu **tách biệt**: `last_seen_bluetooth_at` và `last_seen_cellular_at` — đúng tinh thần "kính có SIM/4G riêng, độc lập với điện thoại" (đã chốt ở UI Analysis.md mục 11). `channel` không hợp lệ (khác `"bluetooth"`/`"cellular"`) → `400`.
- `battery`, `firmware` là optional trong mỗi lần gọi `/seen` — chỉ cập nhật nếu thiết bị gửi kèm, không bắt buộc mỗi lần.
- `GET /devices/{id}` trả về đầy đủ cả 2 mốc `last_seen_*`, `battery`, `firmware` để màn Quản lý thiết bị hiển thị.

**❓ Còn để ngỏ (chưa code, vì cần quyết định hạ tầng thật):** tần suất gọi `/seen` (thiết bị tự poll định kỳ hay backend cần cơ chế real-time/push riêng); có cần cảnh báo chủ động khi pin thấp hoặc khi 1 kênh kết nối im lặng quá lâu (nghi ngờ offline hẳn) không — hiện `/seen` chỉ lưu dữ liệu, chưa có logic cảnh báo.

### 2.4 Cách tự test lại luồng này
```bash
cd backend/billing
python -m pytest -v tests/test_devices.py tests/test_device_lifecycle.py -v   # 15 test riêng cho Device

# hoặc test thủ công (cần: python app.py, và python seed_catalog.py để có serial hợp lệ):
curl -X POST http://localhost:5005/devices/link -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" -d "{\"serial_number\":\"YE-DEMO-0001\"}"
```

---

## 3. Subscription & Packages Module

> **Trạng thái: ĐÃ CODE phần lõi (Task 3, hoàn thành 2026-07-31).** 3.1–3.4 dưới đây đã có code + test (58/58 test pass toàn bộ `backend/billing/`). Refund/Đối soát nằm ở mục 4.2–4.3, đang làm ở **Task 3b**.

### 3.0 File liên quan & vai trò của từng file

| File | Vai trò |
|---|---|
| `backend/billing/tiers.py` | Thêm `PRICING` (giá tháng mỗi tier) + `get_price(tier, billing_cycle)` (năm = tháng × 12). |
| `backend/billing/schema.sql` | Thêm bảng `discount_code`, `payment_transaction`. |
| `backend/billing/models.py` | `create_checkout`, `handle_payment_webhook`, `get_subscription_status`, `add_discount_code`, `_apply_discount`, `_effective_tier` (helper dùng chung để tính tier thật sau khi xét hết hạn). |
| `backend/billing/app.py` | Route: `GET /packages`, `POST /payment/checkout`, `POST /payment/webhook`, `GET /subscription`. |
| `backend/billing/tests/test_payment.py` | Test checkout (giá đúng, tier sai, thiếu token), mã giảm giá (đúng/sai), webhook (paid/failed/idempotent/không tìm thấy), nâng cấp gói mở khoá quota cao hơn ngay. |
| `backend/billing/tests/test_subscription.py` | Test 3 trạng thái active/expiring_soon/expired, và **hạ tier về free ngay khi hết hạn** kể cả ở tầng AI-gateway (`get_device_status`). |

### 3.1 Gói dịch vụ — đã code
- 3 gói hiển thị cho người dùng cá nhân: **Free (0đ) / Basic (99.000đ/tháng) / Pro (199.000đ/tháng)** — giữ nguyên tên demo (đã chốt). Giá năm = giá tháng × 12 (`tiers.get_price`).
- `GET /packages` (không cần token) trả về danh sách gói kèm giá tháng/năm, `quota_limit`, `allowed_intents` — dữ liệu tĩnh từ `tiers.py`, không cần DB.
- **B2B Licensing**: vẫn **chưa code** — kênh backend riêng cho tổ chức tài trợ, để dành cho sau (không có UI khách hàng tương ứng nên không cấp bách).

### 3.2 Giới hạn sử dụng gói Free — đã có định nghĩa (từ code nền tảng trước Task 1, giữ nguyên)
- **1 "lần dùng"** = 1 lần gọi `POST /devices/{id}/consume` (mỗi lần thiết bị/kính gọi AI gateway).
- Giới hạn: Free = 20 lần/ngày, Basic = 200, Pro = 2000 (xem `tiers.TIERS`).
- Mốc reset: theo `_today_period()` = ngày UTC (`YYYY-MM-DD`) — tức reset lúc **00:00 UTC**, không phải giờ địa phương.
- **⚠️ Chưa thực sự "chặn"**: `consume_quota()` vẫn cho phép gọi vượt quá giới hạn — chỉ trả `quota_remaining=0` (không âm), **không raise lỗi**. Việc có chặn hẳn hành động AI hay không là quyết định của service gọi quota (dự kiến `ocr-server`, chưa build trong repo này) — billing-service hiện chỉ đóng vai trò **báo cáo số liệu trung thực**, chưa tự ý chặn. Cần quyết định rõ khi build `ocr-server`.

### 3.3 Subscription state machine — đã code
```
[account mới tạo] --> [active, tier=free, 30 ngày] (mặc định khi register, xem mục 1.1)
   [active] --còn > 7 ngày--> status="active"
   [active] --còn <= 7 ngày (SUBSCRIPTION_EXPIRING_SOON_DAYS)--> status="expiring_soon" (tier CHƯA đổi, vẫn dùng tier đã mua)
   [bất kỳ] --qua expires_at--> status="expired" --> tier hiệu lực HẠ NGAY về free (tính khi đọc, không cần job nền)
   [bất kỳ] --thanh toán thành công (webhook paid)--> tier=gói mới, expires_at = hôm nay + 30/365 ngày
```
**Quy tắc đã code:**
- `GET /subscription` (theo token) trả `{tier, purchased_tier, expires_at, status}` — `tier` là **tier hiệu lực** (đã hạ về free nếu hết hạn), `purchased_tier` là gói đã mua gần nhất (giữ lại để hiển thị lịch sử dù đã hết hạn).
- Ngưỡng "Sắp hết hạn" = **7 ngày** trước `expires_at` (`SUBSCRIPTION_EXPIRING_SOON_DAYS`, đã chốt, có thể chỉnh qua ENV).
- Hết hạn thì **hạ về free ngay lập tức** (đã chốt) — tính toán tại thời điểm đọc (`_effective_tier()`), không cần cron/job nền riêng.
- **Đồng bộ với AI-gateway**: `_effective_tier()` dùng chung cho cả `get_subscription_status` (hiển thị app) lẫn `get_device_status`/`consume_quota` (mục 2) — sửa 1 lỗi có từ trước Task 3: trước đây subscription hết hạn vẫn được dùng quota Pro/Basic vô thời hạn vì 2 nơi tính tier khác nhau.
- Gia hạn thủ công (`renewal_status = Manual`, đã chốt): không lưu thẻ, không auto-charge — mỗi lần gia hạn là 1 `payment_transaction` mới qua mục 4.1.

### 3.4 Upgrade/downgrade — đã code
- Đổi gói giữa kỳ (vd. Basic → Pro trước khi hết hạn Basic): **đã chốt = bắt đầu chu kỳ mới hoàn toàn**, không cộng dồn/prorate ngày còn lại của gói cũ. Thanh toán `paid` → `expires_at` tính lại từ **thời điểm thanh toán**, `tier` đổi thẳng sang gói mới (xem `handle_payment_webhook`).

---

## 4. Payment/Billing Module

> **Trạng thái: ĐÃ CODE toàn bộ 4.1–4.3 (Task 3 + Task 3b, hoàn thành 2026-07-31).** 67/67 test pass toàn bộ `backend/billing/`.

### 4.0 File liên quan
Xem bảng ở mục 3.0 cho phần checkout/webhook. Riêng Refund & Đối soát (Task 3b):

| File | Vai trò |
|---|---|
| `backend/billing/schema.sql` | Thêm cột `account.is_admin` (cờ tạm, xem 4.2). |
| `backend/billing/models.py` | `is_account_admin`, `set_is_admin`, `refund_transaction`, `find_stale_pending_transactions`. |
| `backend/billing/app.py` | `_require_admin()` (helper gate quyền), `POST /admin/transactions/{id}/refund`, `GET /admin/transactions/stale-pending`. |
| `backend/billing/tests/test_refund.py` | Test refund (thành công, ngoài cửa sổ 7 ngày, đã refund rồi, chưa paid, thiếu quyền admin) + đối soát giao dịch pending quá hạn. |

### 4.1 Luồng thanh toán — đã code
```
[App]                                       [Backend]
  |-- POST /payment/checkout --------------->|  Header: Authorization: Bearer <token>
  |   {tier, billing_cycle, discount_code?}  |  1) tier không hợp lệ --> 400
  |                                          |  2) áp discount_code (nếu có): sai/hết hạn/hết lượt --> 400
  |                                          |  3) tạo payment_transaction(status="pending"),
  |                                          |     gateway_ref giả lập (MOCKPAY-xxxx)
  |<-- 201 {transaction_id, amount, gateway_ref} --|
  |                                          |
  | ... (chưa có cổng thanh toán thật để redirect) ...
  |                                          |
  |-- POST /payment/webhook ------------------>|  (mô phỏng callback cổng thanh toán — KHÔNG cần
  |   {gateway_ref, status: "paid"|"failed"}  |   token người dùng, giống cách gateway thật gọi)
  |                                          |  - status != pending trước đó? --> trả kết quả cũ,
  |                                          |    KHÔNG xử lý lại (idempotent)
  |                                          |  - "paid": cộng used_count discount code (nếu có),
  |                                          |    tạo/ghi đè subscription: tier=gói mới,
  |                                          |    expires_at = hôm nay + 30 (tháng) / 365 (năm) ngày
  |<-- 200 {transaction_id, status, already_processed} --|
```
**Quy tắc đã code:**
- `payment_transaction` tạo với `status="pending"` **ngay khi checkout**, trước khi có kết quả thanh toán thật — có bản ghi kể cả khi người dùng bỏ ngang (đúng như spec gốc).
- **Idempotent theo `gateway_ref`**: gọi webhook 2 lần cho cùng `gateway_ref` → lần 2 trả `already_processed: true`, không cộng tiền/không gia hạn 2 lần (có test `test_webhook_is_idempotent`).
- Chỉ khi webhook báo `paid` mới cập nhật `subscription` — webhook `failed` không đụng gì tới subscription.
- Mã giảm giá: kiểm tra tồn tại + chưa hết hạn (`expires_at`) + chưa dùng hết lượt (`used_count < max_uses`) trước khi tính giá cuối; tăng `used_count` khi thanh toán thành công (không tăng nếu `failed`).

**Trạng thái `payment_transaction.status`:** `pending` → `paid` hoặc `failed`. `refunded` **chưa có** — sẽ thêm ở Task 3b (mục 4.2 bên dưới).

**⚠️ Giới hạn đã biết (chưa có gateway thật):**
- Chưa có bước **xác minh chữ ký webhook** (đánh dấu TODO trong code) — vì chưa có gateway thật để lấy khoá bí mật; bắt buộc làm trước khi lên production, nếu không ai cũng gọi được `/payment/webhook` giả mạo thanh toán thành công.
- Không có bước redirect cổng thanh toán thật — `POST /payment/webhook` hiện được gọi **thủ công** (bởi tester, hoặc script) để mô phỏng, đã chốt cùng người dùng.

### 4.2 Hoàn tiền (Refund) — đã code
```
[Admin]                                     [Backend]
  |-- POST /admin/transactions/{id}/refund ->|  Header: Authorization: Bearer <token của account is_admin=True>
  |                                          |  1) không phải admin? --> 403; thiếu/sai token --> 401
  |                                          |  2) transaction không tồn tại --> 404
  |                                          |  3) status != "paid" (chưa trả tiền/đã refund) --> 409
  |                                          |  4) quá REFUND_WINDOW_DAYS kể từ paid_at --> 409
  |                                          |  5) OK: transaction.status = "refunded",
  |                                          |     subscription hạ về free NGAY (expires_at = now)
  |<-- 200 {transaction_id, status: "refunded"} --|
```
**Quy tắc đã code (đã chốt cùng người dùng ở Task 3b):**
- **Điều kiện refund**: giao dịch phải đang `status="paid"` **và** trong vòng `REFUND_WINDOW_DAYS` (mặc định **7 ngày**, ENV override) kể từ `paid_at` — quá hạn hoặc giao dịch chưa/không thể thanh toán → `409`.
- **Hiệu lực refund**: hạ subscription về `free` **ngay lập tức** (không chờ hết hạn tự nhiên) — set `expires_at = thời điểm refund` để `_effective_tier()` (mục 3.3) tính đúng luôn, không cần thêm logic riêng.
- **Cơ chế "admin"**: vì Roles module (mục 1.7) chưa code, dùng **cờ tạm `account.is_admin`** (mặc định `False`), set thủ công qua `models.set_is_admin(db_path, account_id, True)` (chưa có API set qua HTTP — chỉ set tay/qua script, tránh lỗ hổng tự phong admin). Khi có Roles module thật, thay cờ này bằng bảng role đầy đủ mà không cần đổi logic `refund_transaction`.
- Idempotent tự nhiên: gọi refund 2 lần cho cùng giao dịch → lần 2 `status` đã là `refunded` (≠ `paid`) → `409`, không refund 2 lần.

### 4.3 Đối soát (Reconciliation) — đã code (dạng thu hẹp)
```
GET /admin/transactions/stale-pending  (cần quyền admin, giống 4.2)
  --> liệt kê payment_transaction đang "pending" quá STALE_PENDING_MINUTES (mặc định 30 phút)
```
- **Đã chốt cùng người dùng**: vì chưa có cổng thanh toán thật để lấy "báo cáo từ gateway" đối chiếu 2 chiều như spec gốc mô tả, Task 3b làm dạng **thu hẹp**: báo cáo giao dịch `pending` bất thường lâu (nghi ngờ lỡ webhook) — vẫn có giá trị vận hành thật ngay cả khi chưa có gateway.
- Khi có gateway thật: mở rộng thành đối soát 2 chiều đầy đủ (so với báo cáo gateway) là việc của tương lai, chưa nằm trong `find_stale_pending_transactions()` hiện tại.

---

## 5. SOS / Safety Module

> **Trạng thái: ĐÃ CODE (Task 4, hoàn thành 2026-07-31).** Module **rủi ro cao nhất** (an toàn tính mạng) — 92/92 test pass toàn bộ `backend/billing/` tại thời điểm đó. 4 quyết định kiến trúc đã chốt cùng người dùng: mock SMS/push (giống payment gateway), link xem vị trí công khai không cần đăng nhập, ghi vị trí liên tục định kỳ, nhật ký hoạt động ghi thủ công (chưa auto-detect).
>
> **Cập nhật 2026-08-02 — kênh SMS/robo-call giờ có thể THẬT:** đã tích hợp Twilio (`models._send_sms`/`_make_robocall`) cho cả OTP (mục 1) và SOS. Tự động dùng Twilio thật nếu đủ 3 biến ENV `TWILIO_ACCOUNT_SID`/`TWILIO_AUTH_TOKEN`/`TWILIO_FROM_NUMBER`, **tự fallback về mock/log y hệt hành vi cũ nếu chưa cấu hình** (môi trường demo hiện tại chưa có tài khoản Twilio thật, xem mục 1.8). `sos_delivery.status` giờ phản ánh đúng kết quả gửi thật (`"sent"`/`"failed"`) thay vì luôn hardcode `"sent"` như trước — nhưng **vẫn chưa có cơ chế tự động retry khi gửi SOS thất bại** (khác với hàng đợi retry Server Kính ở 5.1d, cơ chế đó có retry).

### 5.0 File liên quan & vai trò của từng file

| File | Vai trò |
|---|---|
| `backend/billing/schema.sql` | Bảng: `emergency_contact` (có `is_primary`), `sos_press`, `sos_event`, `sos_delivery`, `location_log`, `activity_log_entry`, `outbound_notification` (hàng đợi retry S2S, Task 6). `subscription` thêm 2 cột ở Task 7: `billing_cycle` (để dựng `plan_id` khi báo hết hạn) và `expiry_notified_at` (chống báo trùng — xem 5.1d mục "hết hạn tự nhiên"). Phần 3 (5.1e): `device_push_token` (1 token/device, khoá theo `device.id` nội bộ), `kinh_action_request` (1 dòng/lần `dispatch`, có `dispatch_status`), `kinh_action_report` (nhiều dòng/`request_id`, lịch sử report từ app — không ghi đè). |
| `backend/billing/requirements.txt` | Thêm `requests` (Task 6) — gọi HTTP ra Server Kính. |
| `backend/billing/models.py` | 5 nhóm hàm: **Emergency Contacts** (`add/update/list/delete_emergency_contact`, `_unset_other_primary_contacts`); **SOS** — 2 luồng song song: `press_sos_button` (luồng cũ) và `trigger_sos_from_device` (luồng Server Kính, tra theo `serial_number` — đổi ở Task 7), cùng `get_sos_event_by_token`; **Location & Activity** (`report_location`, `get_current_location`, `purge_old_location_logs`, `add_activity_log_entry`, `get_activity_log`) + `_haversine_meters`; **Giao tiếp S2S** — `notify_glasses_subscription_status`, `notify_glasses_link_status` (**mới Task 7**), `_queue_and_send_notification`/`_attempt_send_notification` (tổng quát hoá theo `kind` — Task 7), `retry_failed_notifications`, `list_failed_notifications`, `get_active_device_serials_for_account`/`get_active_device_ids_for_account` (serial vs ID nội bộ — Task 7 + mới 2026-08-01), `_plan_id`, `_check_and_flag_expiry`, `_notify_expiry_all_channels`, `scan_and_notify_expired_subscriptions`, `_push_subscription_expired_to_app` (mới 2026-08-01, xem 5.1d mục "hết hạn tự nhiên"); **Server Kính điều khiển hành động** (Phần 3, mục 5.1e, mới) — `register_push_token`, `dispatch_kinh_action` (idempotent theo `request_id`), `report_kinh_action_result` (ghi nhiều lần, giữ lịch sử), `get_kinh_action_result`. |
| `backend/billing/app.py` | Route: `GET/POST/PATCH/DELETE /emergency-contacts(/{id})`, `POST /devices/{id}/sos/press` (luồng cũ), `POST /internal/api/v1/sos/trigger` (luồng Server Kính), `GET /sos/{location_token}` (public), `POST /devices/{id}/location`, `GET /location/current`, `POST /devices/{id}/activity-log`, `GET /activity-log`, `GET /admin/notifications/failed`, `POST /admin/notifications/retry-failed`, `POST /admin/subscriptions/check-expiry` (mới 2026-08-01, xem 5.1d), `POST /devices/{id}/push-token`, `POST /internal/api/v1/actions/dispatch`, `POST /devices/{id}/actions/{request_id}/report`, `GET /internal/api/v1/actions/{request_id}/result` (4 route cuối = Phần 3, mục 5.1e). Middleware `@app.before_request _enforce_internal_api_auth` bảo vệ mọi route `/internal/api/*` — **tạm không enforce ở `BILLING_ENV=dev`** (quyết định demo-first 2026-08-01). |
| `backend/billing/tests/conftest.py` | **Cập nhật Task 7**: fixture `autouse=True` `_no_real_network_to_glasses_server` — mock `models.requests.post` mặc định cho **mọi** test (trả 200 giả lập), vì `link_device`/thanh toán/refund giờ đều tự bắn notify ra Server Kính; nếu không mock, test sẽ gọi mạng thật ra `localhost:5004` (chậm + treo). Test nào cần giả lập thất bại/retry tự `monkeypatch` đè lên trong thân test. |
| `backend/billing/tests/test_emergency_contacts.py` | CRUD liên hệ khẩn cấp, cách ly giữa các account, đánh dấu/đổi `is_primary` (chỉ 1 primary tại 1 thời điểm). |
| `backend/billing/tests/test_sos.py` | Luồng cũ: đếm số lần nhấn, kích hoạt đúng lúc đủ 3 lần, reset bộ đếm, xem vị trí qua link công khai. |
| `backend/billing/tests/test_sos_internal.py` | Luồng Server Kính: xác thực `Authorization: Bearer <key>` (và bypass đúng khi `BILLING_ENV=dev`, mới 2026-08-01), token người dùng bị từ chối, validate payload, `device_id` = **serial_number** (Task 7), SMS+push tới tất cả liên hệ, **robo-call chỉ tới liên hệ `is_primary`**. |
| `backend/billing/tests/test_glasses_notifications.py` | Gọi Server Kính thành công/thất bại (mock `requests.post`), retry, webhook `paid`/refund kích hoạt `subscription-status` đúng payload (device_id=serial), **`link_device`/`replace_device` kích hoạt `link-status` đúng thứ tự unlinked→linked** (mới Task 7), route admin yêu cầu quyền. |
| `backend/billing/tests/test_subscription.py` | Trạng thái active/expiring_soon/expired, hạ tier khi hết hạn. **Mới 2026-08-01**: `scan_and_notify_expired_subscriptions` phát hiện đúng + idempotent + không báo trùng với đường lazy, báo đúng Server Kính, push app đúng khi có/không có push token, endpoint `check-expiry` yêu cầu admin. |
| `backend/billing/tests/test_kinh_actions.py` | Phần 3 (5.1e): đăng ký push token (401 thiếu token, 400 thiếu field), `dispatch` (401 thiếu key và bypass đúng khi dev, 400 thiếu field theo từng action, 404 device/liên hệ không có, 200 `no_push_token`, 202 `dispatched`, idempotent theo `request_id`), `report` (401/400/404, gọi nhiều lần cho `book_grab`), `GET .../result` (401, 404, lịch sử report đúng thứ tự). |
| `backend/billing/tests/test_location.py` | Báo cáo vị trí, tính "Đang di chuyển"/"Đứng yên" theo khoảng cách 2 điểm gần nhất, retention (xoá log cũ). |
| `backend/billing/tests/test_activity_log.py` | Ghi/đọc nhật ký hoạt động, thứ tự mới nhất trước. |
| `backend/billing/tests/test_sms_provider.py` | **Mới 2026-08-02**: `_to_e164`, `_send_sms`/`_make_robocall` fallback mock khi chưa cấu hình Twilio, dùng Twilio thật khi đã cấu hình (mock `twilio.rest.Client`, không gọi mạng thật), `generate_otp` gửi đúng mã qua SMS, `sos_delivery.status` phản ánh đúng thành công/thất bại thật. |
| `backend/billing/tests/test_scheduler.py` | **Mới 2026-08-02**: scheduler tắt qua `SCHEDULER_ENABLED=false`, bật thì đăng ký đủ 3 job (`retry_failed_notifications`, `check_expiry`, `purge_old_location_logs`) đúng interval từ ENV, mỗi job gọi đúng hàm model, job nuốt exception (không crash scheduler). |

### 5.1 Kích hoạt SOS — đã code

```
[App điện thoại]                              [Backend]
  |-- POST /devices/{id}/sos/press ----------->|  Header: Authorization: Bearer <token chủ thiết bị>
  |   (gọi lại mỗi lần người dùng nhấn nút)     |  1) ghi 1 dòng sos_press(device_id, now)
  |                                             |  2) đếm số lần nhấn trong SOS_PRESS_WINDOW_SECONDS
  |<-- 200 {press_count, triggered: false} -----|     giây gần nhất — CHƯA đủ 3 lần thì dừng ở đây
  |                                             |
  |   ... nhấn tiếp cho tới khi đủ 3 lần trong cửa sổ thời gian ...
  |                                             |
  |-- POST /devices/{id}/sos/press (lần đủ 3) ->|  3) xoá lịch sử nhấn (reset bộ đếm cho lần sau)
  |                                             |  4) lấy điểm location_log mới nhất làm vị trí SOS
  |                                             |  5) tạo sos_event + location_token ngẫu nhiên
  |                                             |  6) gửi SONG SONG tới TẤT CẢ emergency_contact,
  |                                             |     cả 2 kênh SMS + push (mock — luôn "sent" ngay,
  |                                             |     TODO nối provider thật)
  |                                             |  7) ghi activity_log_entry("Đã gửi tín hiệu SOS")
  |<-- 200 {press_count, triggered: true,       |
  |     sos_event_id, location_token,           |
  |     deliveries: [...]} ---------------------|
```

**Quy tắc đã code:**
- **"3 lần nhấn"** = `SOS_PRESS_THRESHOLD` (mặc định **3**) lần gọi API trong `SOS_PRESS_WINDOW_SECONDS` (mặc định **10 giây**) — cả 2 là placeholder, chỉnh qua ENV, chưa phải số liệu sản phẩm chính thức.
- Sau khi kích hoạt, bộ đếm **reset về 0** — nhấn tiếp phải đủ 3 lần mới từ đầu mới trigger lại (test `test_sos_press_counter_resets_after_trigger`).
- Gửi **song song** (không tuần tự) tới **tất cả** Emergency Contacts, **cả 2 kênh** SMS + push cho mỗi liên hệ — mỗi lượt gửi ghi 1 dòng `sos_delivery(status)` để audit (hiện luôn là `"sent"` vì đang mock).
- Vị trí gửi kèm SOS lấy từ **điểm `location_log` mới nhất** đã ghi nhận (không tự đo GPS ngay lúc đó) — vì vậy phụ thuộc vào việc §5.2 đã báo cáo vị trí đều đặn trước đó.
- Mỗi lần kích hoạt tự động ghi 1 dòng vào Nhật ký hoạt động (§5.3) — dùng chung hạ tầng, không tách riêng.

**Quyết định kiến trúc đã chốt (Task 4):**
- **Nhà cung cấp SMS/push**: mock giống Payment gateway ở Task 3 — `sos_delivery.status` luôn `"sent"` ngay, chưa nối provider thật (Twilio/Firebase...). Có chỗ cắm provider thật sau (thay đoạn TODO trong `press_sos_button`) mà không đổi API/schema.
- **Link xem vị trí**: `GET /sos/{location_token}` — **công khai, không cần đăng nhập** (đã chốt, nhất quán với quyết định "không có role caregiver" ở Task 1: người thân không có tài khoản để đăng nhập). Token ngẫu nhiên (`secrets.token_urlsafe(24)`), hết hạn sau `LOCATION_LINK_TTL_HOURS` (mặc định 24 giờ). Hết hạn hoặc token sai đều trả **404 giống nhau** — không phân biệt để tránh lộ thông tin cho việc dò token.

**❓ Còn để ngỏ (chưa code):**
- Chưa có **retry** khi gửi SMS/push thất bại — vì mock hiện luôn thành công, chưa có trường hợp `"failed"` thật để retry. Cần làm khi nối provider thật.
- Chưa có cơ chế **huỷ SOS** trong X giây đầu (nhỡ tay) — hiện đã trigger là gửi luôn, không có API huỷ.

### 5.1b Kích hoạt SOS qua Server Kính — đã code (Task 5, luồng thứ 2, song song với 5.1)

> Khác với 5.1 (backend tự đếm 3 lần nhấn do điện thoại gọi lặp lại), luồng này giả định **Server Kính tự đếm** ở phía thiết bị/firmware và chỉ gọi backend **đúng 1 lần** khi đã đủ điều kiện, kèm sẵn toạ độ GPS. **Đã chốt cùng người dùng: giữ song song cả 2 luồng**, không xoá luồng cũ.

```
[Server Kính]                                    [billing-service]
  |-- POST /internal/api/v1/sos/trigger --------->|  Header: Authorization: Bearer <shared secret>
  |   {device_id, location: {latitude, longitude}, |  (xác thực bằng middleware chung, xem 5.1d)
  |    timestamp_utc}                              |  1) sai/thiếu key --> 401
  |                                                |  2) thiếu device_id/lat/lng --> 400
  |                                                |  3) device_id không tồn tại --> 404
  |                                                |  4) tạo sos_event (dùng thẳng lat/lng gửi lên,
  |                                                |     KHÔNG cần đọc location_log như luồng 5.1)
  |                                                |  5) SMS + push tới TẤT CẢ emergency_contact
  |                                                |  6) Robo-call CHỈ tới liên hệ is_primary=True
  |                                                |     (bỏ qua nếu account chưa có primary contact)
  |                                                |  7) ghi activity_log_entry("Đã gửi tín hiệu SOS")
  |<-- 202 Accepted {status: "accepted"} -----------|
```

**Quy tắc đã code:**
- **Xác thực service-to-service qua `Authorization: Bearer <INTERNAL_API_KEY>`** — **đã đổi từ `X-Internal-Key`** (thiết kế ban đầu Task 5) sang đúng giao thức S2S đã chốt lại ở Task 6: 1 key bí mật DÙNG CHUNG cho **cả 2 chiều** (Server Kính gọi ta, và ta gọi Server Kính — xem 5.1d), cùng tên header `Authorization: Bearer` với token người dùng nhưng **khác không gian giá trị** — phân biệt bằng tiền tố đường dẫn `/internal/api/*` ở middleware, không phải bằng nội dung token.
- `device_id` trong payload = **`serial_number` của kính** (đã chốt Task 7, xem test `test_sos_internal.py` và 5.0 ở trên) — **KHÔNG phải** `device.id` nội bộ. `trigger_sos_from_device` tra theo `WHERE serial_number = ?`. *(Sửa 2026-08-01: dòng này trước đây ghi ngược — nói `device_id` là ID nội bộ và "chưa xác nhận", đã lỗi thời so với code + test thật từ Task 7.)*
- Vị trí dùng **thẳng giá trị Server Kính gửi lên**, không phụ thuộc `location_log` đã báo cáo trước đó (khác luồng 5.1) — vì Server Kính có GPS tại đúng thời điểm nhấn.
- **Robo-call chỉ gửi tới liên hệ `is_primary=True`** (mục 5.1c) — nếu account chưa đánh dấu ai là primary, bỏ qua bước robo-call, không lỗi.
- Log mô phỏng đúng định dạng đã yêu cầu: `SOS TRIGGERED for device ...`, `SIMULATING_SMS to ...`, `SIMULATING_ROBO_CALL to ...`, `SIMULATING_PUSH_NOTIFICATION to ...` — xem `models.trigger_sos_from_device`.
- Trả `202 Accepted` cho mọi trigger hợp lệ — xử lý mock hiện tại là đồng bộ (chưa cần hàng đợi/async thật ở giai đoạn này).

**Yêu cầu đã xác nhận cho đội Server Kính:** khi có tín hiệu SOS (đã tự đếm đủ số lần nhấn theo logic phía kính), gọi **duy nhất** `POST /internal/api/v1/sos/trigger` kèm `device_id`, `location {latitude, longitude}`, `timestamp_utc`, và header `Authorization: Bearer <API key bí mật dùng chung>`. Toàn bộ logic gửi SMS/robo-call/push do billing-service xử lý — Server Kính không cần biết danh sách liên hệ khẩn cấp.

**❓ Còn để ngỏ:**
- `INTERNAL_API_KEY` thật sẽ quản lý/luân chuyển (rotate) thế nào — hiện chỉ là 1 chuỗi tĩnh trong ENV, và **hiện đang tạm KHÔNG bị enforce** ở `BILLING_ENV=dev` (quyết định demo-first 2026-08-01, xem 5.1d).

### 5.1c Primary contact — đã code (Task 5)
- `emergency_contact.is_primary` (bool, mặc định `False`) — set qua `POST /emergency-contacts {..., is_primary: true}` hoặc `PATCH /emergency-contacts/{id} {is_primary: true}`.
- **Chỉ 1 liên hệ là primary tại 1 thời điểm** cho mỗi account — đánh dấu 1 người mới làm primary sẽ tự động bỏ primary của người trước đó (`_unset_other_primary_contacts`).
- Dùng để xác định ai nhận **robo-call** trong luồng 5.1b (SMS/push vẫn gửi cho tất cả, không riêng primary).

### 5.1d Giao thức Server-to-Server với Server Kính — đã code (Task 6)

> **Kiến trúc (đã chốt cùng người dùng):** 2 server tách biệt — **Server App** (repo này: User/Auth/Device/Subscription/Payment, "nguồn chân lý" tài khoản) và **Server Kính** (đối tác, xử lý AI thời gian thực + nhận tín hiệu từ kính). Mọi request S2S xác thực bằng **1 API key bí mật DÙNG CHUNG**, gửi qua `Authorization: Bearer <SECRET_API_KEY>` — không phân biệt chiều gọi.

**A. Middleware xác thực chung cho mọi route `/internal/api/*`** (`app.py::_enforce_internal_api_auth`, chạy qua `@app.before_request`):
- Áp dụng cho **mọi** route có tiền tố `/internal/api/` (hiện tại: `/internal/api/v1/sos/trigger`), không cần gọi kiểm tra thủ công trong từng route nữa — thêm route `/internal/api/*` mới trong tương lai tự động được bảo vệ.
- Sai/thiếu `Authorization: Bearer <key>` (kể cả gửi nhầm bằng token người dùng) → `401`.

**B. API do billing-service GỌI ra Server Kính (Server Kính cần xây)** — **định nghĩa yêu cầu cho đội Server Kính**, KHÔNG phải code trong repo này:

| | |
|---|---|
| Mục đích | Khi thuê bao đổi trạng thái (thanh toán thành công, hoặc bị hoàn tiền) trên Server App, báo ngay cho Server Kính mở/khoá tính năng tương ứng trên kính. |
| Method & Endpoint | `POST {GLASSES_SERVER_BASE_URL}/internal/api/v1/devices/subscription-status` |
| Request body (billing-service gửi) | `{"device_id": "...", "subscription": {"plan_id": "pro_monthly", "status": "active"\|"expired"\|"cancelled", "expires_at": "..."}}` |
| Xác thực | `Authorization: Bearer <SECRET_API_KEY>` — key giống hệt key Server Kính dùng để gọi mục A. |
| `plan_id` | Ghép từ `f"{tier}_{billing_cycle}"` (vd. `pro_monthly`, `basic_yearly`) — quy ước riêng của billing-service, Server Kính cần xác nhận có đọc được format này không. |

**C. Đã code phía billing-service (bên gọi):**
- `models.notify_glasses_subscription_status(device_id, plan_id, status, expires_at)` — ghi 1 dòng `outbound_notification(status="pending")` **trước**, rồi mới gọi HTTP thật (`requests.post`, timeout `GLASSES_SERVER_TIMEOUT_SECONDS`, mặc định 5s) — đảm bảo không mất bản ghi nếu crash giữa chừng.
- **Không làm hỏng luồng chính**: lỗi mạng/HTTP khi gọi Server Kính **không** làm fail webhook thanh toán hay refund — chỉ đánh dấu `outbound_notification.status="failed"` + log lỗi (`FAILED to notify glasses server...`).
- **Hàng đợi retry**: `GET /admin/notifications/failed` (liệt kê), `POST /admin/notifications/retry-failed` (gọi lại toàn bộ) — cả 2 yêu cầu quyền `is_admin`, vẫn gọi tay được. **Cập nhật 2026-08-02: giờ CÓ scheduler tự động** gọi `retry-failed` mỗi `RETRY_NOTIFICATIONS_INTERVAL_MINUTES` phút (mặc định 5) — xem bảng scheduler ở mục 8.
- **Điểm gọi trong code:** `handle_payment_webhook` (khi `status="paid"` → báo `"active"` tới mọi thiết bị `active` của account), `refund_transaction` (báo `"cancelled"` sau khi hạ về free), và `_notify_expiry_all_channels` (báo `"expired"` — xem mục "hết hạn tự nhiên" bên dưới, mới 2026-08-01).

**GIẢ ĐỊNH chưa xác nhận:** `GLASSES_SERVER_BASE_URL` (ENV, mặc định `http://localhost:5004`) được đặt bằng địa chỉ `ocr-server-service` trong `docker-compose.yml` — **suy đoán "Server Kính" = `ocr-server-service`**, chưa xác nhận thật với đội đối tác.

~~**Chưa xử lý sự kiện "hết hạn tự nhiên"**~~ — **Đã code (2026-08-01, theo yêu cầu Server Kính khi rà `CONTRACT_SERVER_KINH.md`)**, chưa gắn số Task chính thức vì phát sinh ngoài kế hoạch task ban đầu: trước đó chỉ lazy (khi đọc `/subscription`/`/status`), chỉ thanh toán/refund mới có "thời điểm xảy ra" rõ ràng để chủ động trigger. Giờ có thêm đường **chủ động**: `models.scan_and_notify_expired_subscriptions()` quét toàn bộ `subscription` hết hạn nhưng chưa báo (`expiry_notified_at IS NULL`), claim từng dòng bằng `UPDATE ... WHERE expiry_notified_at IS NULL` + kiểm tra rowcount (race-safe với đường lazy — không báo trùng dù đường nào phát hiện trước). Gộp logic báo tin vào 1 helper dùng chung `_notify_expiry_all_channels()` cho cả 2 đường lazy (`get_device_status`/`get_subscription_status`) lẫn đường quét, đồng thời **thêm kênh mới: push app** (`_push_subscription_expired_to_app`, tái dùng bảng `device_push_token`/cơ chế push mock đã có cho tính năng "Server Kính điều khiển hành động" — xem 5.1e bên dưới, chưa nối Firebase/APNs thật) để UI app tự cập nhật khi gói hết hạn, không chỉ báo Server Kính như trước. Kích hoạt qua `POST /admin/subscriptions/check-expiry` (admin-gated, cùng pattern `retry_failed_notifications`) — **cập nhật 2026-08-02: giờ CÓ scheduler tự động** gọi endpoint này mỗi `CHECK_EXPIRY_INTERVAL_MINUTES` phút (mặc định 10, xem bảng scheduler ở mục 8), vẫn giữ endpoint admin để gọi tay khi cần kiểm tra ngay.

**❓ Còn để ngỏ:**
- Cơ chế quản lý/luân chuyển (rotate) `INTERNAL_API_KEY` thật khi lên production. **Lưu ý 2026-08-01**: kiểm tra key này hiện đang **tạm tắt hoàn toàn** ở `BILLING_ENV=dev` (Server Kính gọi `/internal/api/*` không cần header vẫn qua) — quyết định demo-first, xem `CONTRACT_SERVER_KINH.md` mục "Yêu cầu quan trọng". Bắt buộc bật lại khi `BILLING_ENV=production`.
- Xác nhận format `device_id` (mục 5.1b) và `plan_id` với đội Server Kính — đã gửi `CONTRACT_SERVER_KINH.md` liệt kê đủ 6 giá trị `plan_id` khả dĩ, đang chờ Server Kính xác nhận.

### 5.1e Server Kính điều khiển hành động trên app điện thoại — đã code

> **Bối cảnh:** kính (qua Server Kính, khi nghe được lệnh thoại hoặc phát hiện tình huống) muốn app điện thoại tự làm 1 việc thay mặt người dùng — gọi khẩn cấp, gọi 1 liên hệ bất kỳ, chỉ đường Google Maps, đặt Grab — vì bản thân kính/Server Kính không có quyền truy cập danh bạ máy hay tự gọi điện được. **Vấn đề kỹ thuật:** app điện thoại không chạy server công khai, không nhận POST trực tiếp từ backend được. **Giải pháp đã chốt:** Push Notification (FCM/APNs — hiện mock, chưa nối thật) làm kênh truyền cuối; Server Kính chỉ cần gọi **1 endpoint S2S** duy nhất vào billing-service, billing-service lo toàn bộ phần tra cứu + gửi push + theo dõi kết quả.
>
> 4 hành động hỗ trợ (`models.KINH_ACTIONS`): `call_emergency_contact`, `call_contact`, `navigate`, `book_grab`. Tài liệu **đầy đủ field-by-field cho từng action** (bắt buộc/optional, format `params`, mã lỗi) đã có sẵn ở `CONTRACT_SERVER_KINH.md` Phần 3 (viết cho đối tác nên rất chi tiết) — mục này chỉ tóm tắt luồng nội bộ, không lặp lại toàn bộ bảng field.

```
[Server Kính]                                     [billing-service]
  |-- POST /internal/api/v1/actions/dispatch ---->|  Header: Authorization: Bearer <shared secret>
  |   {device_id (=serial), request_id, action,   |     (giống 5.1d — tạm không enforce ở dev)
  |    params, timestamp_utc}                     |  1) validate field bắt buộc theo từng action
  |                                                |  2) request_id đã tồn tại? --> trả lại
  |                                                |     dispatch_status cũ, KHÔNG gửi push lần 2
  |                                                |     (idempotent, giống payment webhook)
  |                                                |  3) action=call_emergency_contact: tự tra
  |                                                |     emergency_contact (theo contact_id gửi lên,
  |                                                |     hoặc is_primary=true nếu không gửi), đính
  |                                                |     tên+SĐT vào payload push — Server Kính
  |                                                |     KHÔNG cần biết danh bạ khẩn cấp
  |                                                |  4) action=call_contact: KHÔNG tự tra được số
  |                                                |     (đây là danh bạ máy, khác Emergency
  |                                                |     Contacts) — chỉ relay nguyên văn
  |                                                |     params.contact_query cho app tự khớp
  |                                                |  5) tra device_push_token theo device.id nội bộ
  |                                                |     (app tự đăng ký, xem route dưới)
  |                                                |  6) ghi kinh_action_request(dispatch_status);
  |                                                |     có token --> log SIMULATING_PUSH_ACTION
  |                                                |     (mock, 1 data message tới app, payload xem
  |                                                |     CONTRACT_SERVER_KINH.md mục 3.3)
  |<-- 202 {request_id, status:"dispatched"} ------|     hoặc 200 "no_push_token" nếu app chưa đăng ký
  |
  |   ... app điện thoại nhận push (ngoài phạm vi backend), tự thực thi (gọi điện qua tai nghe
  |       Bluetooth nếu đang kết nối / mở Google Maps / mở deep-link Grab), rồi tự báo kết quả về
  |       billing-service qua POST /devices/{id}/actions/{request_id}/report (cần token người
  |       dùng — app đã đăng nhập). Có thể gọi NHIỀU LẦN cho cùng 1 request_id (vd. book_grab:
  |       đặt xe -> tài xế nhận -> đang tới) — mỗi lần ghi 1 dòng kinh_action_report mới, KHÔNG
  |       ghi đè, giữ toàn bộ lịch sử ...
  |
  |-- GET /internal/api/v1/actions/{request_id}/  |
  |     result ----------------------------------->|  Server Kính chủ động poll khi cần đọc kết quả
  |<-- 200 {request_id, action, dispatch_status,   |     cho người dùng nghe qua loa kính (vd. "không
  |     reports: [...]} ----------------------------|     tìm thấy liên hệ mẹ") — trả TOÀN BỘ lịch sử
  |                                                 |     report, mới nhất ở cuối mảng
```

**Đăng ký push token — route riêng cho app (không phải Server Kính):**
```
POST /devices/{id}/push-token {platform: "android"|"ios", push_token}   (cần token người dùng)
```
App tự gọi lúc khởi động/đăng nhập, để billing-service biết gửi push vào đâu. `device_push_token` chỉ lưu **1 token/device** (ghi đè token cũ nếu đăng ký lại).

**Quy tắc đã code:**
- **Idempotency theo `request_id`** do Server Kính tự sinh — gọi lại cùng `request_id` không gửi push lần 2, chỉ trả lại kết quả lần dispatch đầu tiên (`dispatch_kinh_action`, test `test_dispatch_is_idempotent_by_request_id`).
- **`call_contact` khác `call_emergency_contact` ở chỗ ai tách tên**: `call_contact` bắt Server Kính tự tách tên người muốn gọi ra khỏi câu lệnh trước khi gửi (`contact_query`, vd. gửi `"mẹ"` chứ không phải `"gọi mẹ tôi"`) — billing-service chỉ relay nguyên văn, không tự parse được vì đó là danh bạ **máy** của người dùng, không phải bảng `emergency_contact`.
- **`navigate`/`book_grab`** đều cần `params.destination.lat`/`.lng` (bắt buộc), `.address` chỉ để hiển thị/đọc cho người dùng, không dùng để định vị.
- **Xác thực S2S dùng chung middleware/key với 5.1d** (`/internal/api/*`) — **hiện tạm không enforce ở `BILLING_ENV=dev`** (quyết định demo-first 2026-08-01, xem 5.1d).
- Response **không bao giờ rỗng** — kể cả lỗi đều có `{"error": "..."}` hoặc field cụ thể để Server Kính đọc và phát âm thanh phản hồi người dùng (yêu cầu chốt 2026-08-01, xem `CONTRACT_SERVER_KINH.md`).

**❓ Còn để ngỏ:**
- Firebase/APNs thật chưa nối — hiện chỉ log `SIMULATING_PUSH_ACTION`, chưa gửi push thật tới thiết bị nào.
- **Phía app điện thoại (frontend) chưa có code xử lý loại push này** — nhận push `type: "kinh_action"`, tự thực thi hành động (gọi điện/mở Maps/mở Grab), gọi lại `.../report` để báo kết quả. Việc nối `device.tsx`/`GET /devices` (Task quản lý thiết bị phía app) không bao gồm phần này — cần 1 task frontend riêng.
- Đặt Grab xác nhận là **deep-link**, không dùng Grab Partner API thật — người dùng vẫn phải tự xác nhận đặt xe trong app Grab, chưa hoàn toàn tự động.

### 5.2 Theo dõi vị trí (Location tracking) — đã code

```
[Kính/điện thoại]                        [Backend]
  |-- POST /devices/{id}/location ---------->|  (KHÔNG cần token người dùng — device-to-backend,
  |   {lat, lng}                             |   giống /seen, /status, /consume ở mục 2)
  |                                          |  ghi 1 dòng location_log(account_id, lat, lng, now)
  |<-- 200 {"message": "..."} -----------------|

[App]
  |-- GET /location/current ------------------>|  Header: Authorization: Bearer <token>
  |                                            |  lấy 2 điểm location_log gần nhất của account,
  |                                            |  so khoảng cách (haversine) với
  |                                            |  LOCATION_MOVING_THRESHOLD_METERS (mặc định 20m)
  |<-- 200 {lat, lng, status, updated_at} -----|  status = "Đang di chuyển" hoặc "Đứng yên"
```

**Quy tắc đã code (đã chốt kiến trúc ở Task 4: ghi liên tục định kỳ, khớp UI luôn hiển thị "vị trí hiện tại"):**
- Backend **không tự poll** — thiết bị/điện thoại chủ động gọi `/location` theo chu kỳ riêng (tần suất cụ thể vẫn để ngỏ, xem ❓ dưới).
- Trạng thái di chuyển tính bằng khoảng cách **haversine** giữa 2 điểm ghi gần nhất nhất so với ngưỡng `LOCATION_MOVING_THRESHOLD_METERS` (đặt 20m, placeholder) — chỉ 1 điểm duy nhất (mới bật lần đầu) thì mặc định "Đứng yên".
- **Quyền riêng tư**: `GET /location/current` yêu cầu token của chính chủ tài khoản — không có endpoint nào cho phép người khác xem vị trí liên tục; người thân chỉ xem được **1 điểm chụp tại thời điểm SOS** qua link công khai tạm thời (§5.1), không phải theo dõi trực tiếp kiểu Life360 (khớp đúng những gì demo UI thể hiện — chỉ có 1 nút SOS, không có "chia sẻ vị trí liên tục").
- **Retention**: `purge_old_location_logs()` xoá log cũ hơn `LOCATION_LOG_RETENTION_DAYS` (mặc định 30 ngày) — **cập nhật 2026-08-02: giờ có scheduler tự động gọi mỗi `PURGE_LOCATION_LOGS_INTERVAL_MINUTES` phút** (mặc định 1440 = 1 ngày/lần, xem bảng scheduler ở mục 8), trước đó phải gọi tay/lên lịch ngoài `billing-service`.

**❓ Còn để ngỏ:** tần suất báo cáo vị trí cụ thể (bao nhiêu giây/phút 1 lần — ảnh hưởng pin kính, quyết định ở phía firmware/app, backend chấp nhận bất kỳ tần suất nào được gọi); có cần thông báo rõ cho người dùng khi tính năng theo dõi vị trí đang bật không (UI/UX, ngoài phạm vi backend).

### 5.3 Nhật ký hoạt động (Activity log) — đã code (ghi thủ công)

```
POST /devices/{id}/activity-log {title}   (device-to-backend, không cần token người dùng)
  --> ghi 1 dòng activity_log_entry(account_id, title, now)
GET /activity-log   (cần token — trả về mới nhất trước)
```

**Đã chốt kiến trúc (Task 4):** **chưa làm auto-detect** điểm đến (geofencing/POI) — đây là bài toán AI/bản đồ riêng, ngoài phạm vi `billing-service`. Hiện tại nguồn duy nhất là **API ghi thủ công**: app hoặc thiết bị tự gọi `/activity-log` với `title` cho sẵn (vd. "Bắt đầu đi dạo"). SOS trigger cũng tự động ghi 1 dòng qua cùng cơ chế này (§5.1).

**❓ Còn để ngỏ:** khi nào làm auto-detect thật (cần tích hợp bản đồ/POI database) — chưa có kế hoạch, chờ quyết định sản phẩm riêng.

---

## 6. Community Module

### 6.1 Nhóm hỗ trợ (Groups)
```
Xem danh sách nhóm (kèm số thành viên) → bấm "tham gia" → thêm user vào group_members → cập nhật đếm thành viên
```
- **❓ Cần chốt:** có cần duyệt (admin approve) trước khi tham gia nhóm không, hay tham gia tự do.

### 6.2 Bài viết (Posts)
```
Đăng bài mới (text, có thể kèm ảnh?) → hiển thị trong feed (mới nhất trước) 
  → tính năng "Nghe bài viết" = text-to-speech đọc nội dung → không cần lưu audio, generate on-demand
```
- **❓ Cần chốt:** có kiểm duyệt nội dung trước khi hiển thị công khai không (tránh nội dung không phù hợp trong cộng đồng người khiếm thị); TTS dùng engine nào (ảnh hưởng chất lượng giọng đọc, đã có tuỳ chọn Giọng Nam/Nữ ở Profile — engine cần hỗ trợ cả 2 giọng).

### 6.3 Sự kiện (Events)
```
Xem danh sách sự kiện → bấm "lưu sự kiện" → thêm vào saved_events của user → (❓ có gửi nhắc nhở trước giờ sự kiện không?)
```

---

## 7. Support Module

### 7.1 Nội dung tĩnh
- "Hướng dẫn sử dụng" (Mở) và "FAQ" (Xem): nội dung do admin quản lý (CMS đơn giản), không phải dữ liệu người dùng tạo ra.

### 7.2 Ticket-based (Phản hồi lỗi / Gửi yêu cầu hỗ trợ)
```
Người dùng gửi mô tả (lỗi/yêu cầu) → tạo support_ticket (status=open) 
  → đội hỗ trợ xử lý qua PATCH /admin/support/tickets/{id}/status (status=in_progress → resolved) 
  → thông báo lại cho người dùng khi có cập nhật (SMS, mới 2026-08-02 — xem dưới)
```
- ~~Chưa gửi thông báo lại cho người dùng khi đổi trạng thái~~ — **Đã code 2026-08-02**: `update_support_ticket_status` tự gửi SMS (Twilio thật nếu cấu hình, mock nếu chưa — xem mục 1.8) báo trạng thái mới cho đúng SĐT của account tạo ticket, chỉ gửi khi status THỰC SỰ đổi (không spam nếu admin PATCH lại đúng status cũ).
- **❓ Cần chốt:** form nhập thực tế cần trường gì (demo chỉ có nút "Gửi"/"Tạo", chưa có form chi tiết) — mô tả lỗi có cần đính kèm ảnh/log thiết bị không (quan trọng vì đây là thiết bị phần cứng) — **vẫn chưa có hạ tầng lưu file, chỉ nhận text** (xem `support_ticket` không có cột attachment).

### 7.3 Hotline
- "1900 1234" — chỉ là số điện thoại tĩnh, không cần backend, nhưng nên log số lượt bấm gọi để đo nhu cầu hỗ trợ trực tiếp.

---

## 8. Vấn đề xuyên suốt (Cross-cutting concerns)

| Chủ đề | Ghi chú |
|---|---|
| **Notification Gateway** | **Cập nhật 2026-08-02**: chưa phải 1 service trung tâm tách riêng, nhưng đã có 1 điểm gọi chung `models._send_sms`/`_make_robocall` (Twilio) dùng cho cả OTP, SOS, và cập nhật ticket hỗ trợ. Push (kinh_action, hết hạn gói) vẫn qua nhánh mock riêng, **chưa nối Firebase/APNs thật**. Có log trạng thái gửi cho SOS (`sos_delivery.status`, giờ phản ánh đúng thật/mock), nhưng **chưa có retry tự động khi SMS/robo-call thất bại** (khác hàng đợi retry Server Kính ở 5.1d — cái đó có retry qua scheduler). Nhắc gia hạn/sự kiện cộng đồng qua kênh này: chưa làm. |
| **Audit log** | Bắt buộc ghi log cho các hành động nhạy cảm: Khoá thiết bị, Báo mất, Đổi kính, Đăng xuất, thay đổi liên hệ khẩn cấp, kích hoạt SOS — phục vụ điều tra khi có sự cố. **Chưa code** — hiện chỉ có `logger.info`/`logger.error` rải rác từng chỗ, chưa có bảng audit log riêng biệt. |
| **Rate limiting** | Áp dụng cho: gửi OTP (đã có cooldown 60s, xem 1.8), áp mã giảm giá (tránh brute-force mã), tạo support ticket (chống spam). **Chưa code** rate limit cho register/login/support ticket ngoài cooldown OTP sẵn có. |
| **Quyền riêng tư dữ liệu vị trí** | Xem mục 5.2 — cần chính sách rõ ràng vì đây là nhóm dữ liệu nhạy cảm nhất trong toàn hệ thống. |
| **Idempotency** | Bắt buộc cho: webhook thanh toán (đã code, theo `gateway_ref`), gửi SOS qua Server Kính (chưa idempotent, xem 5.1b — Server Kính tự đảm bảo không gọi trùng), `dispatch_kinh_action` (đã code, theo `request_id`), hết hạn gói (đã code, theo `expiry_notified_at`, xem 5.1d). |
| **Job nền tự động (scheduler)** | **Mới 2026-08-02** — `app.py::_start_background_scheduler`, dùng APScheduler chạy trong process (an toàn vì Dockerfile chỉ 1 gunicorn worker). Xem bảng chi tiết ngay dưới. |

**Bảng job scheduler (mới 2026-08-02):**

| Job | Interval mặc định | Đổi qua ENV | Gọi hàm |
|---|---|---|---|
| Retry thông báo Server Kính lỗi | 5 phút | `RETRY_NOTIFICATIONS_INTERVAL_MINUTES` | `models.retry_failed_notifications` |
| Quét subscription hết hạn | 10 phút | `CHECK_EXPIRY_INTERVAL_MINUTES` | `models.scan_and_notify_expired_subscriptions` |
| Xoá location_log quá hạn retention | 1440 phút (1 ngày) | `PURGE_LOCATION_LOGS_INTERVAL_MINUTES` | `models.purge_old_location_logs` |

Tắt toàn bộ scheduler qua `SCHEDULER_ENABLED=false` (vd. nếu sau này tăng số gunicorn worker, tránh gọi trùng — hoặc quay lại gọi tay qua 3 admin endpoint tương ứng). Mỗi job tự bọc try/except, lỗi 1 job không làm chết scheduler hay các job khác. Test: `backend/billing/tests/test_scheduler.py`.

---

## 9. Tổng hợp — Danh sách "❓ Cần chốt" ưu tiên cao

Nhóm theo mức độ ảnh hưởng, nên chốt trước khi bắt đầu code phần tương ứng:

1. ~~**SOS (mục 5.1, 5.2)**~~ — **Đã code ở Task 4** (2026-07-31): cửa sổ "3 lần nhấn" = 3 lần/10 giây (placeholder, ENV), link vị trí công khai không cần đăng nhập (TTL 24 giờ), ghi vị trí liên tục định kỳ. **SMS/robo-call nối Twilio thật 2026-08-02** (mục 1.8, 5) — chỉ còn push vẫn mock. Còn lại: chưa có retry khi gửi SOS thất bại (Twilio lỗi thật bây giờ CÓ THỂ xảy ra, khác trước đây mock luôn thành công — nhưng chưa build cơ chế tự retry cho riêng SOS), chưa có cơ chế huỷ SOS trong X giây đầu, chưa chốt tần suất báo cáo vị trí cụ thể.
2. ~~**Quota gói Free (mục 3.2)**~~ — đã có định nghĩa sẵn từ code nền tảng (1 lần dùng = 1 lần gọi `/consume`, Free=20/ngày, reset 00:00 UTC). Còn lại: `consume_quota()` chưa thực sự **chặn** khi vượt quota (chỉ báo `quota_remaining=0`) — quyết định chặn cứng là việc của service gọi quota (`ocr-server`, chưa build).
3. ~~**Bảo mật hành động thiết bị (mục 2.2)**~~ — **Đã code ở Task 2**: Khoá/Báo mất/Đổi kính bắt buộc OTP re-auth. Còn lại: `/devices/{id}/status`, `/devices/{id}/consume`, `/devices/{id}/seen`, `/devices/{id}/location`, `/devices/{id}/activity-log` vẫn chưa có xác thực riêng cho thiết bị (device secret/API key) — để ngỏ cho tới khi cần (xem mục 1.4, 2.2, 2.3, 5.2, 5.3).
4. ~~**Auth (mục 1.1, 1.2)**~~ — **Đã code ở Task 1**: login dùng OTP tạm thời giống register; TTL OTP=300s, TTL session=30 ngày (ENV). Còn lại: OAuth Google chưa code, role admin/support thật chưa code (đang dùng cờ `is_admin` tạm, xem mục 4.2).
5. ~~**Subscription & Refund (mục 3.3, 4.2)**~~ — **Đã code ở Task 3 + 3b**: ngưỡng sắp hết hạn = 7 ngày, hạ về free ngay khi hết hạn; refund trong 7 ngày kể từ thanh toán, hạ về free ngay, gate bằng cờ `is_admin`.

Tất cả các điểm ❓ "bắt buộc chốt trước khi code" ban đầu đã được xử lý (Task 1–4). Các điểm còn để ngỏ ở trên đều là phần mở rộng/production-hardening, không chặn việc tiếp tục sang Community/Support (mục 6, 7).

---

## 10. Tổng kết trạng thái backend tính đến 2026-08-02

Rà lại toàn bộ code (`app.py`, `models.py`, 191 test) theo yêu cầu "backend hoàn chỉnh cho luồng user từ đăng ký đến bước cuối". Kết quả:

### 10.1 Luồng user — đầy đủ endpoint, chạy được từ đầu tới cuối
Đăng ký/đăng nhập (OTP thật qua Twilio nếu cấu hình) → xem hồ sơ (`GET /account`, **mới**) → liên kết kính → xem/đổi gói → thanh toán (mock gateway) → xem trạng thái thuê bao → quản lý thiết bị (khoá/mở/báo mất/khôi phục/đổi/reset) → liên hệ khẩn cấp → SOS (SMS/robo-call thật qua Twilio nếu cấu hình) → theo dõi vị trí → nhật ký hoạt động → cộng đồng → hỗ trợ (ticket giờ tự báo lại qua SMS, **mới**) → đăng xuất. Không có bước nào trong luồng chính thiếu API.

### 10.2 Mới thêm 2026-08-02 (task này)
- Twilio SMS thật cho OTP (`generate_otp`) và SOS (`press_sos_button`, `trigger_sos_from_device`) — tự fallback mock nếu chưa cấu hình ENV, xem mục 1.8.
- Twilio robo-call thật cho liên hệ `is_primary` khi SOS (luồng Server Kính, mục 5.1b).
- `sos_delivery.status` giờ phản ánh đúng thành công/thất bại thật thay vì hardcode `"sent"`.
- Scheduler tự động (APScheduler, trong process) cho 3 job trước đây phải gọi tay: retry thông báo Server Kính lỗi, quét subscription hết hạn, xoá location log quá hạn — xem bảng mục 8.
- `GET /account` — trước đây KHÔNG có cách nào để app lấy lại thông tin tài khoản (SĐT, ngày tạo) sau khi đăng nhập, cần cho màn Hồ sơ.
- Support ticket đổi trạng thái tự gửi SMS báo người dùng (đóng gap đã ghi ở mục 7.2 từ trước).
- Sửa nhiều chỗ tài liệu bị lệch code thật (route pairing cũ, mã trạng thái sai, số lượng test lỗi thời) ở mục 1.4/1.6/1.9/5.2.

### 10.3 Đã cố ý KHÔNG làm trong task này (ngoài phạm vi hoặc cần quyết định thêm)
- **Cổng thanh toán thật** (`/payment/checkout`, `/payment/webhook`) — vẫn mock (`MOCKPAY-...`), chưa nối VNPay/MoMo/Stripe... — quyết định rõ ràng để dành việc khác, chưa nằm trong phạm vi task này.
- **Auth riêng cho thiết bị** (5 endpoint device-to-backend không cần token) — cần phối hợp Server Kính để biết thiết bị nhận secret bằng cách nào, đang bị chặn ngoài tầm kiểm soát backend (xem mục 1.4, `CONTRACT_SERVER_KINH.md`).
- **Chuẩn hoá mã lỗi** (`{"error": {"code", "message"}}` thay vì chỉ message) — sẽ là breaking change cho toàn bộ app điện thoại hiện đang đọc `data.error` như string ở mọi màn hình; cần đồng bộ với frontend trước, chưa làm trong task này.
- **Rate limiting rộng hơn** (register/login ngoài cooldown OTP, support ticket chống spam) — chưa làm, ưu tiên demo-first.
- **Audit log riêng biệt** cho hành động nhạy cảm — chưa làm, hiện chỉ có log rải rác.
- **Push thật** (Firebase/APNs cho kinh_action + báo hết hạn gói) — vẫn mock, cần tài khoản Firebase project riêng (khác Twilio).
- **OAuth Google, Roles module thật** — như đã ghi từ Task 1, chưa cần cho luồng user chính (chỉ đăng nhập bằng SĐT+OTP), vẫn dùng cờ `is_admin` tạm.

### 10.4 Cách bật SMS/robo-call thật khi có tài khoản Twilio
Không cần sửa code — chỉ set 3 biến ENV rồi khởi động lại container:
```bash
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_FROM_NUMBER=+1...
```
Xác nhận đã chuyển sang gửi thật bằng cách xem log: `TWILIO_SMS_SENT`/`TWILIO_ROBOCALL_SENT` thay vì `SIMULATING_SMS`/`SIMULATING_ROBO_CALL`.
