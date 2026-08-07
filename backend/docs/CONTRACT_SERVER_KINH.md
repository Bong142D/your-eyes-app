# Giao thức Server Kính ↔ Backend (billing-service)

> **Tài liệu gửi cho Server Kính** (AI Gateway chạy trên/cho thiết bị kính — dự kiến service `ocr-server-service`). Đây là hợp đồng API đầy đủ cho kênh giao tiếp giữa 2 hệ thống: những gì backend (billing-service) cung cấp sẵn cho Server Kính gọi vào, những gì Server Kính cần tự xây để backend gọi ra, và 4 tính năng mới đang chờ tích hợp 2 phía.
>
> Tài liệu khác (`API_CONTRACT.md`) dành cho app điện thoại/frontend — không cần đọc nếu bạn chỉ làm phía Server Kính, nhưng phần 3 (tính năng mới) có nhắc tới app điện thoại vì luồng đi qua cả 3 hệ thống.
>
> Cập nhật lần cuối: 2026-08-01. Khớp code `backend/billing/app.py` hiện tại.

---

## ⚠️ Yêu cầu quan trọng — cần Server Kính cung cấp/xác nhận

Đây là những việc cần Server Kính phản hồi trước khi 2 hệ thống nối được với nhau đầy đủ:

1. **Base URL thật của Server Kính.** Hiện chúng tôi mới đặt giá trị giả định `http://localhost:5004` (ENV `GLASSES_SERVER_BASE_URL`) để backend gọi ra (Phần 2). **Vui lòng cung cấp URL thật** (dev/staging/production nếu có nhiều môi trường) để chúng tôi cấu hình.
2. **Timeout mong đợi** khi chúng tôi gọi vào Server Kính — hiện backend đặt `GLASSES_SERVER_TIMEOUT_SECONDS = 5` giây (ENV, có thể chỉnh). Báo lại nếu 2 endpoint ở Phần 2 của bạn cần thời gian xử lý lâu hơn.
3. **Format `plan_id` trong `subscription-status` (Phần 2) chưa được Server Kính xác nhận chính thức.** Giá trị thực tế code gửi là `"{tier}_{billing_cycle}"` — toàn bộ 6 giá trị có thể xảy ra: `"free_monthly"`, `"free_yearly"`, `"basic_monthly"`, `"basic_yearly"`, `"pro_monthly"`, `"pro_yearly"` (suy ra trực tiếp từ `tiers.TIERS` × 2 chu kỳ thanh toán trong code, không phải đoán). Vui lòng xác nhận format này parse được.
4. **[Demo: tạm hoãn, chưa cần giải quyết ngay — production: bắt buộc phải chốt] `device_id` nội bộ cho nhóm endpoint Phần 1.1** (`/seen`, `/status`, `/consume`, `/location`, `/activity-log`) — 5 endpoint này dùng **ID nội bộ (UUID)** do backend sinh lúc pairing, khác hẳn `serial_number` dùng ở Phần 1.2/2/3. Với kênh `channel: "bluetooth"` (điện thoại relay hộ kính) không vấn đề. Với kênh `channel: "cellular"` (kính tự gọi thẳng qua SIM/4G, độc lập điện thoại) — kính cần biết trước ID nội bộ này bằng cách nào vẫn chưa có câu trả lời. **Cho giai đoạn demo hiện tại: dùng tạm 1 `device_id` bất kỳ demo được trọn luồng là đủ** (đã xác nhận với đội sản phẩm — 1 kính chắc chắn chỉ gắn với 1 `serial_number`), không cần giải quyết gap này ngay. Bắt buộc phải chốt trước khi tích hợp kính thật qua kênh `cellular`.

**Đã chốt phía chúng tôi (không cần bạn phản hồi, chỉ cần implement đúng theo đây):**
- **Xác thực backend → Server Kính** (Phần 2, chiều CHÚNG TÔI GỌI RA): không đổi — vẫn luôn gửi `Authorization: Bearer <INTERNAL_API_KEY>` mỗi request, endpoint bạn tự xây ở Phần 2 phải chấp nhận header này.
- **Xác thực Server Kính gọi VÀO chúng tôi** (Phần 1.2/3, mọi route dưới `/internal/api/*`): **quyết định 2026-08-01 — TẠM BỎ kiểm tra `INTERNAL_API_KEY` trong giai đoạn demo** (ưu tiên tích hợp nhanh, chưa bàn bảo mật). Server Kính có thể gọi thẳng các endpoint này **không cần** header `Authorization` trong lúc demo. ⚠️ Sẽ bật lại bắt buộc khi lên môi trường production — đừng phụ thuộc vào việc "luôn không cần auth", chỉ là tạm thời cho demo.
- **Format `contact_query`** (Phần 3.2, action `call_contact`): Server Kính phải **tự tách sẵn tên người muốn gọi** trước khi gửi — gửi `"mẹ"`, không gửi cả câu `"gọi mẹ tôi"`. Việc parse câu lệnh là việc của AI/STT bên bạn, chúng tôi chỉ relay nguyên văn `contact_query` cho app để app tự khớp danh bạ máy.
- **Response không bao giờ trả body rỗng** — mọi endpoint (kể cả lỗi) đều có `{"message": "..."}` hoặc `{"error": "..."}` hoặc field cụ thể, không có route nào trả `204`/body rỗng (đã rà lại toàn bộ code để xác nhận) — quan trọng vì Server Kính cần đọc để phát âm thanh phản hồi người dùng.

---

## Tóm tắt toàn bộ endpoint

| Method | URL | Ai gọi | Auth | Trạng thái |
|---|---|---|---|---|
| `POST` | `/devices/{device_id}/seen` | Kính/Server Kính | Không cần | ✅ |
| `GET` | `/devices/{device_id}/status` | Server Kính | Không cần | ✅ |
| `POST` | `/devices/{device_id}/consume` | Server Kính | Không cần | ✅ |
| `POST` | `/devices/{device_id}/location` | Kính | Không cần | ✅ |
| `POST` | `/devices/{device_id}/activity-log` | Kính | Không cần | ✅ |
| `POST` | `/internal/api/v1/sos/trigger` | Server Kính | `INTERNAL_API_KEY` | ✅ 🧪 |
| `POST` | `/internal/api/v1/actions/dispatch` | Server Kính | `INTERNAL_API_KEY` | ✅ 🧪 |
| `GET` | `/internal/api/v1/actions/{request_id}/result` | Server Kính | `INTERNAL_API_KEY` | ✅ |
| `POST` | `{GLASSES_SERVER_BASE_URL}/internal/api/v1/devices/subscription-status` | Backend gọi Server Kính | `INTERNAL_API_KEY` (đã gửi sẵn từ phía chúng tôi) | 🧪 (chờ URL thật) |
| `POST` | `{GLASSES_SERVER_BASE_URL}/internal/api/v1/devices/link-status` | Backend gọi Server Kính | `INTERNAL_API_KEY` (đã gửi sẵn từ phía chúng tôi) | 🧪 (chờ URL thật) |
| `POST` | `/devices/{device_id}/push-token` | App điện thoại (không phải Server Kính) | Token người dùng | ✅ — liệt kê để hiểu trọn luồng Phần 3 |
| `POST` | `/devices/{device_id}/actions/{request_id}/report` | App điện thoại (không phải Server Kính) | Token người dùng | ✅ — liệt kê để hiểu trọn luồng Phần 3 |

**Ký hiệu:** ✅ đã code, có test · 🧪 phần gọi dịch vụ ngoài (SMS/push/Server Kính thật) hiện chỉ mock/log giả lập.

---

## Quy ước chung

| | |
|---|---|
| **Base URL backend (dev/local)** | `http://localhost:5005` — chỉ gọi được nếu Server Kính chạy cùng máy/cùng LAN. **chưa có staging/production** (xem "Yêu cầu quan trọng" #1). |
| **Base URL backend (tunnel demo, tạm thời)** | `https://litigate-upheld-moonrise.ngrok-free.dev` — dùng để Server Kính test từ xa qua internet trong giai đoạn hiện tại. ⚠️ Chỉ sống khi máy dev + `docker compose` + `ngrok` đang chạy cùng lúc — không phải URL cố định lâu dài, sẽ đổi/mất khi ngừng demo. ⚠️ Middleware `INTERNAL_API_KEY` (mục 1.2 dưới) **đang tắt** (`BILLING_ENV=dev`) — ai có URL này cũng gọi được `/internal/api/*` không cần header, kể cả qua tunnel công khai. Chấp nhận được cho giai đoạn test, **không dùng URL này cho gì ngoài test**. |
| **Cách ghép URL đầy đủ (Phần 1)** | Mọi endpoint ở **Phần 1** dưới đây chỉ ghi **path tương đối** — ghép với Base URL ở trên để ra URL gọi thật. VD: `POST /devices/{device_id}/seen` → gọi thật là `POST http://localhost:5005/devices/{device_id}/seen` (thay `{device_id}` bằng ID thật). Riêng **Phần 2** (2 endpoint Server Kính tự xây) đã ghi sẵn URL đầy đủ dạng `{GLASSES_SERVER_BASE_URL}/...` — không cần ghép gì thêm. |
| **Content-Type** | `application/json` cho mọi request có body. |
| **Định dạng lỗi** | `{"error": "<thông báo bằng tiếng Việt>"}` — đọc theo HTTP status code, chưa có mã lỗi dạng code riêng. **Không route nào trả body rỗng** (đã rà lại toàn bộ code) — luôn có `message`/`error`/field cụ thể để đọc/phát âm thanh. |
| **Định dạng thời gian** | Đa số ISO 8601 UTC — **ngoại lệ**: `expires_at`/`changed_at` trong Phần 2 (`subscription-status`, `link-status`) dùng `"YYYY-MM-DD HH:MM:SS"` gọn hơn, xem chi tiết ở từng endpoint. |
| **Auth Server Kính → Backend (`/internal/api/*`)** | 🧪 **Tắt tạm thời trong giai đoạn demo** (`BILLING_ENV=dev`) — gọi không cần header vẫn thành công. Sẽ bắt buộc `Authorization: Bearer <INTERNAL_API_KEY>` khi lên production. |
| **Định dạng toạ độ** | ⚠️ Chưa nhất quán: `/internal/api/v1/sos/trigger` dùng `{latitude, longitude}`; các endpoint khác (`/devices/{id}/location`, `/internal/api/v1/actions/dispatch`) dùng `{lat, lng}`. Để ý đúng tên trường theo từng endpoint bên dưới. |

> ⚠️ **`device_id` có 2 nghĩa khác nhau tuỳ endpoint — đọc kỹ trước khi tích hợp:**
> - **Phần 1.1** (`/seen`, `/status`, `/consume`, `/location`, `/activity-log`): `device_id` = **ID nội bộ** (UUID) do backend sinh ra lúc pairing.
> - **Phần 1.2, Phần 2, Phần 3** (mọi endpoint dưới `/internal/api/*` và 2 endpoint Server Kính tự xây): `device_id` = **`serial_number`** in trên kính — **không phải** ID nội bộ.
>
> Xem mục "Yêu cầu quan trọng" #4 ở trên — cách kính lấy được ID nội bộ cho Phần 1.1 (đặc biệt kênh `cellular`) **hiện chưa chốt**.

---

## Vai trò App điện thoại trong luồng này

**App điện thoại KHÔNG giao tiếp trực tiếp với Server Kính** — mọi thứ đi qua backend (billing-service) làm trung gian, 2 chiều đều vậy. Tóm tắt riêng mục này vì ảnh hưởng tới cách bạn thiết kế luồng phía Server Kính:

**App cung cấp gì (cho backend, gián tiếp phục vụ Server Kính):**
- Đăng ký push token — `POST /devices/{device_id}/push-token` (cần token người dùng, không phải Server Kính gọi) — để backend biết gửi push FCM/APNs vào máy nào khi có `dispatch` từ Server Kính (Phần 3.2).
- Thực thi hành động Server Kính yêu cầu (gọi điện/mở Google Maps/mở Grab) sau khi nhận push, rồi báo kết quả qua `POST /devices/{device_id}/actions/{request_id}/report` — Server Kính đọc lại kết quả qua `GET /internal/api/v1/actions/{request_id}/result` (Phần 3.3).
- Danh bạ khẩn cấp (Emergency Contacts) do người dùng tự nhập trong app, backend lưu và tự tra khi cần — **Server Kính không bao giờ nhận được danh sách này**, chỉ nhận tên+SĐT của đúng 1 liên hệ đã chọn, đính kèm sẵn trong push (`call_emergency_contact`, Phần 3.3).

**App cần Server Kính cung cấp gì:** **không có gì trực tiếp.** App không tự gọi API của Server Kính, và Server Kính không tự gọi API của app — 100% qua backend làm cầu nối (push notification là kênh truyền cuối duy nhất tới app, xem "Vấn đề kỹ thuật" ở mục 3.1).

---

## Phần 1 — API backend cung cấp cho Server Kính gọi vào

### 1.1 Device-to-backend (không cần xác thực) — gọi định kỳ

#### `POST /devices/{device_id}/seen`
Báo cáo kết nối định kỳ (heartbeat) từ kính.

**Headers:** `Content-Type: application/json`

**Body:**
| Trường | Kiểu | Bắt buộc | Ý nghĩa |
|---|---|---|---|
| `channel` | string | ✅ | `"bluetooth"` hoặc `"cellular"` — kênh kính đang dùng để kết nối tới điện thoại/mạng. Giá trị khác → `400`. |
| `battery` | int (0–100) | — | % pin kính hiện tại. |
| `firmware` | string | — | Version firmware đang chạy trên kính, dùng để backend theo dõi tiến độ rollout. |

```json
{ "channel": "bluetooth", "battery": 77, "firmware": "v2.2.0" }
```

**Response:** `200 {"message": "..."}`. **Lỗi:** `400` `channel` sai giá trị · `404` `device_id` không tồn tại.

**Tác dụng phía backend:** cập nhật `last_seen_bluetooth_at` **hoặc** `last_seen_cellular_at` (2 cột tách biệt vì kính có SIM/4G riêng, độc lập điện thoại) + `battery`/`firmware` nếu có gửi.

---

#### `GET /devices/{device_id}/status`
Server Kính gọi **trước khi xử lý bất kỳ yêu cầu AI nào** (đọc chữ, mô tả cảnh...) để biết thiết bị còn quyền dùng không. **Không được cache lâu** — quota/status có thể đổi bất kỳ lúc nào (thanh toán, khoá kính, hết hạn gói).

**Headers:** không cần auth.

**Response `200`:**
| Trường | Kiểu | Ý nghĩa |
|---|---|---|
| `tier` | string | Gói hiện tại: `"free"` \| `"basic"` \| `"pro"`. |
| `subscription_valid` | bool | `false` nếu hết hạn/chưa mua — **Server Kính PHẢI chặn AI nếu `false`**. |
| `quota_remaining` | int | Số lượt AI còn lại trong kỳ — **PHẢI chặn AI nếu `0`**. |
| `allowed_intents` | array[string] | Danh sách intent AI được phép chạy theo gói (vd. `"DOC_CHU"`, `"MO_TA_CANH"`) — chặn intent ngoài danh sách. |
| `device_status` | string | `"active"` \| `"locked"` \| `"lost"` — `locked`/`lost` **PHẢI chặn AI** dù còn quota. |

```json
{ "tier": "pro", "subscription_valid": true, "quota_remaining": 2000,
  "allowed_intents": ["DOC_CHU", "MO_TA_CANH"], "device_status": "active" }
```

**Lỗi:** `404` `device_id` không tồn tại.

---

#### `POST /devices/{device_id}/consume`
Server Kính gọi **sau khi** đã xử lý xong 1 lượt AI thành công, để trừ quota.

**Headers:** không cần auth. `Content-Type: application/json` nếu có gửi body (không bắt buộc, xem dưới).

**Body:** không có field nào (gửi `{}` hoặc body rỗng).

**Response `200`:** `{ "quota_remaining": 1999 }`

**Lỗi:** `403` thiết bị đang `locked`/`lost` (lớp bảo vệ thứ 2, phòng khi `/status` bị bỏ qua) · `404` không tìm thấy thiết bị.

⚠️ **Không idempotent** — gọi lại sẽ trừ thêm quota. Server Kính tự đảm bảo chỉ gọi đúng 1 lần mỗi lượt AI thật.

---

#### `POST /devices/{device_id}/location`
Ghi 1 điểm vị trí (kính GPS/cellular tự gọi, hoặc app điện thoại).

**Headers:** không cần auth. `Content-Type: application/json`.

**Body:**
| Trường | Kiểu | Bắt buộc | Ý nghĩa |
|---|---|---|---|
| `lat` | float | ✅ | Vĩ độ. |
| `lng` | float | ✅ | Kinh độ. |

```json
{ "lat": 10.776889, "lng": 106.700833 }
```

**Response:** `200`. **Lỗi:** `400` thiếu `lat`/`lng` · `404` không tìm thấy thiết bị.

Vị trí mới nhất ghi qua endpoint này chính là vị trí sẽ dùng làm mặc định khi SOS kích hoạt qua luồng app — **nên gọi đều đặn**, không chỉ khi cần.

---

#### `POST /devices/{device_id}/activity-log`
Ghi thủ công 1 dòng hoạt động (chưa auto-detect điểm đến/geofencing).

**Headers:** không cần auth. `Content-Type: application/json`.

**Body:**
| Trường | Kiểu | Bắt buộc | Ý nghĩa |
|---|---|---|---|
| `title` | string | ✅ | Nội dung mốc hoạt động, tự do (vd. `"Bắt đầu đi dạo"`). |

**Response:** `200 {"message": "..."}`. **Lỗi:** `400` thiếu `title` · `404` `device_id` không tồn tại.

---

### 1.2 S2S — cần header xác thực `INTERNAL_API_KEY`

Toàn bộ endpoint dưới `/internal/api/*` **về nguyên tắc** yêu cầu:
```
Authorization: Bearer <INTERNAL_API_KEY>
Content-Type: application/json
```
`INTERNAL_API_KEY` là 1 secret dùng chung do backend cấp — **liên hệ chúng tôi để lấy giá trị thật cho môi trường của bạn** (giá trị dev mặc định `dev-internal-key`, không dùng cho production).

🧪 **Giai đoạn demo hiện tại (quyết định 2026-08-01): kiểm tra header này đang TẮT** (`BILLING_ENV=dev`) — Server Kính có thể gọi các endpoint dưới đây **không cần** gửi `Authorization` vẫn thành công, để tích hợp nhanh. Sẽ bật lại bắt buộc khi backend chạy `BILLING_ENV=production`. Vẫn nên implement gửi header ngay từ bây giờ để không phải sửa lại sau.

#### `POST /internal/api/v1/sos/trigger`
**Endpoint duy nhất** Server Kính cần gọi khi kính tự đếm đủ số lần nhấn nút SOS trên phần cứng (logic đếm số lần nằm bên kính — backend không biết). Toàn bộ phần còn lại (chọn liên hệ khẩn cấp, gửi SMS/robo-call/push, tạo link vị trí công khai) backend tự xử lý — **Server Kính không cần biết danh sách liên hệ khẩn cấp của người dùng**.

**Body:**
| Trường | Kiểu | Bắt buộc | Ý nghĩa |
|---|---|---|---|
| `device_id` | string | ✅ | **Là `serial_number` của kính**, không phải ID nội bộ. |
| `location.latitude` | float | ✅ | Vĩ độ kính đo được tại thời điểm trigger. Lưu ý tên trường `latitude` (khác `lat` ở các endpoint khác). |
| `location.longitude` | float | ✅ | Kinh độ. |
| `timestamp_utc` | string (ISO 8601) | ✅ | Thời điểm kính xác nhận đủ ngưỡng nhấn. |

```json
{
  "device_id": "YE-DEMO-0001",
  "location": { "latitude": 10.776889, "longitude": 106.700833 },
  "timestamp_utc": "2026-08-01T10:00:00Z"
}
```

**Response `202`:** `{ "status": "accepted" }`

**Lỗi:** `401` thiếu/sai `INTERNAL_API_KEY` · `400` thiếu field · `404` `device_id` (serial) chưa từng được liên kết với tài khoản nào.

🧪 SMS/Push/Robo-call gửi tới liên hệ khẩn cấp hiện chỉ log giả lập, chưa nối provider thật (Twilio/Firebase) — không ảnh hưởng gì tới hợp đồng phía Server Kính.

⚠️ Chưa idempotent — nếu Server Kính lỡ gọi 2 lần cho cùng 1 sự kiện SOS thật sẽ tạo 2 sự kiện, gửi thông báo 2 lần. **Server Kính tự đảm bảo chỉ gọi 1 lần** mỗi lần đủ ngưỡng nhấn.

---

#### `POST /internal/api/v1/actions/dispatch` — tính năng mới, xem chi tiết đầy đủ ở **Phần 3.2**

---

## Phần 2 — API Server Kính CẦN tự xây dựng, backend sẽ gọi vào

⚠️ **Cần bạn cung cấp URL thật** — xem mục "Yêu cầu quan trọng" ở đầu tài liệu. Xác thực đã chốt: mỗi request backend gửi tới bạn đều kèm header `Authorization: Bearer <INTERNAL_API_KEY>` (cùng key với Phần 1.2) — **endpoint bạn tự xây phải tự kiểm tra header này**, chúng tôi không cần bạn phản hồi thêm về auth.

🧪 **Hiện luôn thất bại phía backend** vì chưa có URL thật để gọi. Backend tự động đưa vào hàng đợi retry nội bộ (`GET /admin/notifications/failed`, `POST /admin/notifications/retry-failed` — API quản trị nội bộ của chúng tôi, không liên quan Server Kính), **không** làm hỏng flow chính (pairing/thanh toán/refund của người dùng vẫn thành công dù gọi Server Kính thất bại).

#### `POST {GLASSES_SERVER_BASE_URL}/internal/api/v1/devices/subscription-status`
**Headers gửi kèm:** `Authorization: Bearer <INTERNAL_API_KEY>`, `Content-Type: application/json`.

**Backend gọi khi:** thanh toán thành công (`status: "active"`), hoàn tiền (`status: "cancelled"`), hoặc gói hết hạn tự nhiên (`status: "expired"`) — phát hiện qua **1 trong 2 đường** (đường nào xảy ra trước sẽ báo, không báo trùng): lazy (ai đó gọi `/subscription`/`/status` sau khi hết hạn), hoặc **chủ động** qua job quét `POST /admin/subscriptions/check-expiry` (quyết định 2026-08-01 — nội bộ chúng tôi tự gọi định kỳ, Server Kính không cần quan tâm cơ chế này, chỉ cần biết `status: "expired"` giờ có thể tới **chủ động** thay vì chỉ khi có người đọc).

**Body backend sẽ gửi:**
| Trường | Kiểu | Ý nghĩa |
|---|---|---|
| `device_id` | string | **= `serial_number` của kính** (đã xác nhận trong code, cùng quy ước với Phần 1.2/Phần 3) — không phải ID nội bộ. |
| `subscription.plan_id` | string | `"{tier}_{billing_cycle}"` — 1 trong 6 giá trị: `"free_monthly"`, `"free_yearly"`, `"basic_monthly"`, `"basic_yearly"`, `"pro_monthly"`, `"pro_yearly"` — ⚠️ chưa xác nhận với Server Kính, xem mục "Yêu cầu quan trọng" #3. |
| `subscription.status` | string | `"active"` \| `"cancelled"` \| `"expired"`. |
| `subscription.expires_at` | string | `"YYYY-MM-DD HH:MM:SS"` (vd. `"2027-01-01 00:00:00"`) — **không phải ISO 8601 thô**, đã format gọn cho dễ đọc/parse (quyết định 2026-08-01). |

```json
{ "device_id": "YE-DEMO-0001", "subscription": { "plan_id": "pro_monthly", "status": "active", "expires_at": "2027-01-01 00:00:00" } }
```

**Server Kính cần trả về:** mã HTTP 2xx để backend coi là thành công (nội dung response body hiện backend không đọc — báo lại nếu bạn muốn định dạng cụ thể).

---

#### `POST {GLASSES_SERVER_BASE_URL}/internal/api/v1/devices/link-status`
**Headers gửi kèm:** `Authorization: Bearer <INTERNAL_API_KEY>`, `Content-Type: application/json`.

**Backend gọi khi:** liên kết kính thành công (`status: "linked"`); đổi kính (`/devices/{id}/replace`) → gọi 2 lần: `"unlinked"` cho serial cũ rồi `"linked"` cho serial mới.

**Body backend sẽ gửi:**
| Trường | Kiểu | Ý nghĩa |
|---|---|---|
| `device_id` | string | **= `serial_number` của kính** (giống `subscription-status` ở trên) — không phải ID nội bộ. |
| `link_status.status` | string | `"linked"` \| `"unlinked"`. |
| `link_status.changed_at` | string | `"YYYY-MM-DD HH:MM:SS"` — cùng format với `expires_at` ở trên (không phải ISO 8601 thô). |

```json
{ "device_id": "YE-DEMO-0001", "link_status": { "status": "linked", "changed_at": "2026-08-01 10:00:00" } }
```

---

## Phần 3 — Tính năng mới: Server Kính điều khiển hành động trên app điện thoại

**Trạng thái:** ✅ phần backend đã code (route + test). 🧪 gửi push hiện chỉ mock (log). Phần Server Kính gọi vào **có thể tích hợp ngay** theo đặc tả dưới đây — chỉ còn thiếu phần app điện thoại thực thi hành động và Firebase/APNs thật (không thuộc phạm vi Server Kính).

### 3.1 Bối cảnh — 4 tính năng

1. **Gọi khẩn cấp cho người thân** — kính phát hiện tình huống khẩn cấp → app tự chọn liên hệ đã thiết lập sẵn (Emergency Contacts) → tự gọi điện, âm thanh qua tai nghe Bluetooth đang kết nối, người dùng không cần chạm điện thoại.
2. **Gọi liên hệ bất kỳ** — kính nghe lệnh thoại (vd. "gọi mẹ tôi") → app tự tìm trong danh bạ điện thoại → khớp thì gọi; **không khớp thì chỉ báo lại, không ép gọi bằng được**.
3. **Chỉ đường Google Maps** — kính gửi điểm đến → app mở Google Maps, chỉ đường đi bộ.
4. **Đặt Grab** — kính gửi điểm đến → app mở app Grab có sẵn trên điện thoại với điểm đến điền sẵn (deep-link, không dùng Grab Partner API) → người dùng xác nhận đặt xe trong app Grab → app báo lại tiến trình (tài xế nhận, đang tới...) qua audio.

**Vấn đề kỹ thuật:** app điện thoại không chạy server công khai, không thể nhận POST trực tiếp. Giải pháp: dùng **Push Notification (FCM/APNs)** làm kênh truyền cuối — Server Kính chỉ cần gọi 1 endpoint S2S vào backend, backend lo phần gửi push.

### 3.2 `POST /internal/api/v1/actions/dispatch` — endpoint Server Kính gọi vào

**Auth:** `Authorization: Bearer <INTERNAL_API_KEY>` (giống mục 1.2).

**Body:**
| Trường | Kiểu | Bắt buộc | Ý nghĩa |
|---|---|---|---|
| `device_id` | string | ✅ | `serial_number` của kính — cùng quy ước với `/internal/api/v1/sos/trigger`. |
| `request_id` | string | ✅ | **Do Server Kính tự sinh, phải duy nhất mỗi lần yêu cầu.** Dùng để: (a) idempotency — gọi lại cùng `request_id` sẽ KHÔNG gửi push lần 2, chỉ trả lại kết quả lần đầu; (b) app dùng lại `request_id` này khi báo cáo kết quả. |
| `action` | string (enum) | ✅ | 1 trong 4 giá trị: `"call_emergency_contact"`, `"call_contact"`, `"navigate"`, `"book_grab"` — xem bảng chi tiết bên dưới. |
| `params` | object | tuỳ `action` | Nội dung khác nhau theo từng `action` — xem bảng. |
| `timestamp_utc` | string (ISO 8601) | ✅ | Thời điểm Server Kính phát sinh yêu cầu. |

**Chi tiết `params` theo từng `action`:**

| `action` | `params` | Bắt buộc trong `params` | Ý nghĩa |
|---|---|---|---|
| `call_emergency_contact` | `{}` hoặc `{"contact_id": "..."}` | Không — `contact_id` là optional | Không gửi `contact_id` → backend tự chọn liên hệ có `is_primary=true`. Có gửi → gọi đúng liên hệ đó. Backend tự tra bảng liên hệ khẩn cấp và đính tên+SĐT vào push — **Server Kính không cần biết danh bạ liên hệ**. |
| `call_contact` | `{"contact_query": "mẹ"}` | ✅ `contact_query` | **Server Kính phải tự tách tên ra khỏi câu lệnh trước khi gửi** (vd. gửi `"mẹ"`, không gửi cả câu `"gọi mẹ tôi"`) — xem mục "Đã chốt phía chúng tôi" ở đầu tài liệu. Backend **không** tự tra được số điện thoại (đây là danh bạ máy, không phải Emergency Contacts) — chỉ relay nguyên văn `contact_query` cho app để app tự khớp tên trong danh bạ điện thoại. |
| `navigate` | `{"destination": {"lat": ..., "lng": ..., "address": "..."}}` | ✅ `destination.lat`, `destination.lng`. `address` optional (chuỗi hiển thị/đọc cho người dùng, không dùng để định vị) | App mở Google Maps, chỉ đường đi bộ tới toạ độ. |
| `book_grab` | `{"destination": {"lat": ..., "lng": ..., "address": "..."}}` | Giống `navigate` | App mở deep-link Grab với điểm đến điền sẵn. |

```json
// Ví dụ request cho action = call_emergency_contact
{
  "device_id": "YE-DEMO-0001",
  "request_id": "kinh-req-8f3a1c...",
  "action": "call_emergency_contact",
  "params": {},
  "timestamp_utc": "2026-08-01T10:00:00Z"
}
```

**Response:**
| Mã | Body | Khi nào |
|---|---|---|
| `202` | `{ "request_id": "...", "status": "dispatched" }` | Đã gửi push thành công tới app (không đảm bảo app đã nhận/xử lý xong — đó là bất đồng bộ). |
| `200` | `{ "request_id": "...", "status": "no_push_token" }` | App chưa từng đăng ký push token cho thiết bị này — **không gửi được**, Server Kính có thể cân nhắc phản hồi lại người dùng bằng cách khác (vd. thông báo qua loa kính nếu có). |
| `200` | `{ "request_id": "...", "status": "<trạng thái lần gọi đầu>" }` | `request_id` đã được gửi trước đó (retry) — trả lại đúng kết quả cũ, không gửi push lần 2. |

**Lỗi:**
| Mã | Khi nào |
|---|---|
| `401` | Thiếu/sai `INTERNAL_API_KEY`. |
| `400` | Thiếu `device_id`/`request_id`/`action`/`timestamp_utc`; hoặc `action` không hợp lệ; hoặc thiếu `params.contact_query` (cho `call_contact`); hoặc thiếu `params.destination.lat`/`lng` (cho `navigate`/`book_grab`). |
| `404` | `device_id` (serial) chưa từng được liên kết; hoặc `action = call_emergency_contact` mà tài khoản chưa có liên hệ khẩn cấp phù hợp (không có `contact_id` hợp lệ, hoặc không có liên hệ nào đánh dấu `is_primary`). |

### 3.3 Sau khi dispatch — điều gì xảy ra tiếp theo (để Server Kính hiểu trọn luồng)

Sau khi backend nhận `dispatch` và trả `202`, backend gửi 1 push notification (data message) tới app điện thoại:
```json
{
  "type": "kinh_action",
  "request_id": "kinh-req-8f3a1c...",
  "action": "call_emergency_contact",
  "params": { "contact_name": "Mẹ", "contact_phone": "0911111111" },
  "issued_at": "2026-08-01T10:00:00Z"
}
```
App tự thực thi hành động (gọi điện/mở Maps/mở Grab), sau đó gọi `POST /devices/{device_id}/actions/{request_id}/report` (endpoint dành cho app, không phải Server Kính) để báo lại kết quả — `status`: `"done"` \| `"no_match"` \| `"failed"` \| `"in_progress"` (dùng cho `book_grab` khi có nhiều cập nhật: đặt xe → tài xế nhận → tài xế đang tới).

#### `GET /internal/api/v1/actions/{request_id}/result` — để Server Kính đọc lại kết quả

Nếu cần phản hồi người dùng bằng giọng nói qua kính (vd. "không tìm thấy liên hệ mẹ trong danh bạ", hay đọc tiến trình đặt Grab), Server Kính có thể **chủ động poll** endpoint này theo `request_id` đã dùng lúc `dispatch`.

**Auth:** `Authorization: Bearer <INTERNAL_API_KEY>` (giống mục 1.2/3.2).

**Response `200`:**
| Trường | Kiểu | Ý nghĩa |
|---|---|---|
| `request_id` | string | Khớp `request_id` đã gửi lúc dispatch. |
| `action` | string | Action tương ứng. |
| `dispatch_status` | string | `"dispatched"` \| `"no_push_token"` — kết quả của bước gửi push (không phải kết quả hành động). |
| `reports` | array | **Toàn bộ lịch sử** report app đã gửi về, sắp theo thời gian tăng dần (report mới nhất ở cuối mảng). Rỗng `[]` nếu app **chưa** report gì. Mỗi phần tử: `{"status": "...", "detail": "...", "reported_at": "..."}` — `status` là 1 trong `"done"`/`"no_match"`/`"failed"`/`"in_progress"`. |

```json
{
  "request_id": "kinh-req-8f3a1c...",
  "action": "call_contact",
  "dispatch_status": "dispatched",
  "reports": [
    { "status": "no_match", "detail": "Không tìm thấy 'chú Ba' trong danh bạ.", "reported_at": "2026-08-01T10:00:05" }
  ]
}
```

**Lỗi:** `401` thiếu/sai `INTERNAL_API_KEY` · `404` `request_id` không tồn tại (chưa từng dispatch).

Với `book_grab`, đọc phần tử **cuối cùng** trong `reports` để lấy trạng thái mới nhất (vd. đang đi từ `"in_progress"` → `"done"`).

### 3.4 Ghi chú thực thi trên máy (ngoài phạm vi backend/Server Kính)

- **Gọi điện qua tai nghe Bluetooth**: hành vi hệ điều hành điện thoại (Android `Intent.ACTION_CALL` / iOS `CallKit`) — nếu tai nghe Bluetooth đang kết nối, OS tự route âm thanh qua đó. Không ai ở phía backend/Server Kính can thiệp được, chỉ cần app trigger cuộc gọi bình thường.
- **Google Maps chỉ đường**: app tự chọn deep-link hoặc Directions API — không ảnh hưởng hợp đồng ở trên (backend/Server Kính chỉ truyền toạ độ).
- **Đặt Grab**: xác nhận là **deep-link**, không dùng Grab Partner API thật — người dùng vẫn xác nhận đặt xe trong app Grab, không hoàn toàn tự động.

---

## Phụ lục — Checklist cần Server Kính phản hồi

| # | Nội dung | Mức độ chặn |
|---|---|---|
| 1 | Base URL thật cho `GLASSES_SERVER_BASE_URL` (Phần 2) | Chặn — backend không gọi được vào Server Kính nếu thiếu |
| 2 | Timeout mong đợi cho 2 endpoint ở Phần 2 nếu khác 5 giây | Không chặn, chỉ cần báo nếu khác mặc định |
| 3 | Xác nhận format `plan_id` = `"{tier}_{billing_cycle}"` (6 giá trị liệt kê ở mục "Yêu cầu quan trọng" #3) dùng được cho Server Kính | Không chặn Phần 1/3, chặn nếu Server Kính cần parse `plan_id` từ `subscription-status` |
| 4 | Cách kính lấy `device_id` nội bộ để gọi Phần 1.1 qua kênh `cellular` (xem "Yêu cầu quan trọng" #4) | **Không chặn demo hiện tại** (dùng tạm 1 device_id demo được) — chặn khi tích hợp kính thật qua `cellular`. Kênh `bluetooth` không bị ảnh hưởng |

Các điểm còn lại (auth demo tạm tắt, format `contact_query`, response không rỗng, cách đọc lại kết quả report) **đã chốt phía chúng tôi** — xem "Đã chốt phía chúng tôi" ở đầu tài liệu và mục 3.3 (`GET /internal/api/v1/actions/{request_id}/result`), Server Kính chỉ cần implement theo đúng đặc tả, không cần phản hồi thêm.
