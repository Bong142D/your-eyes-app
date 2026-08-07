## **A. Ứng dụng người dùng**

Chức năng cần có:

| Nhóm chức năng | Mô tả |
| ----- | ----- |
| Đăng ký/đăng nhập | SĐT để đăng ký đăng nhập, OTP để xác nhận đăng ký  |
| Liên kết kính | Nhập serial number, mã kích hoạt |
| Xem gói dịch vụ | Gói tháng, năm, dùng thử |
| Thanh toán/gia hạn | Chuyển sang cổng thanh toán |
| Xem trạng thái thuê bao | Trạng thái thuê báo gồm 3 loại: còn hạn, sắp hết hạn, quá hạn |
| Quản lý thiết bị | Đổi kính, khóa thiết bị, báo mất, có thông tin kính |
| Hỗ trợ người dùng | Hotline, hướng dẫn sử dụng, phản hồi lỗi |

## **B. Backend chính**

Các module quan trọng:

### **1\. User & Auth Module**

Quản lý:

| Thành phần | Vai trò |
| ----- | ----- |
| User profile | Thông tin người dùng |
| Login/OTP | Xác thực tài khoản |
| Role | User, caregiver, admin, support |
| Session/token | Duy trì phiên đăng nhập |

Nên hỗ trợ thêm vai trò **người thân/người hỗ trợ**, vì người khiếm thị có thể cần người khác thanh toán hoặc quản lý gói thay.

### **2\. Device Management Module**

Quản lý kính thông minh.

Cần lưu:

| Dữ liệu | Ý nghĩa |
| ----- | ----- |
| device\_id | ID duy nhất của kính |
| serial\_number | Mã sản xuất/in trên thiết bị |
| owner\_user\_id | Người sở hữu |
| firmware\_version | Phiên bản phần mềm kính |
| sim/4G status | Trạng thái kết nối |
| last\_seen\_at | Lần cuối kính online |
| device\_status | Active, locked, lost, replaced |

### **3\. Payment/Billing Module**

Đây là module xử lý thanh toán.

Chức năng:

| Chức năng | Mô tả |
| ----- | ----- |
| Tạo đơn thanh toán | Tạo order/payment session |
| Redirect checkout | Chuyển người dùng sang cổng thanh toán |
| Nhận webhook/IPN | Nhận kết quả thanh toán từ cổng thanh toán |
| Xác minh chữ ký | Kiểm tra webhook thật hay giả |
| Lưu giao dịch | Lưu paid, failed, pending, refunded |
| Đối soát | So sánh giao dịch nội bộ với gateway |
| Hoàn tiền | Xử lý refund khi cần |

### **4\. Subscription Module**

Module này quản lý gói duy trì.

Ví dụ gói:

| Gói | Nội dung |
| ----- | ----- |
| Freemium | Trải nghiệm các tính năng cơ bản, giới hạn số lần sử dụng mỗi ngày. |
| Premium Subscription | Sử dụng không giới hạn số lần, không giới hạn thời gian trong ngày. |
| B2B Licensing | Doanh nghiệp tài trợ thiết bị hoặc gói Premium cho người khiếm thị theo chương trình từ thiện hoặc phúc lợi xã hội. |

Thông tin cần lưu:

| Dữ liệu | Ví dụ |
| ----- | ----- |
| plan\_id | BASIC\_MONTHLY |
| billing\_cycle | Monthly / Quarterly / Yearly |
| start\_date | Ngày bắt đầu |
| end\_date | Ngày hết hạn |
| renewal\_status | Auto-renew / Manual |
| subscription\_status | active, trialing, past\_due, canceled, expired |

