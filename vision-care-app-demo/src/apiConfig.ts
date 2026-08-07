// Đọc từ .env (biến EXPO_PUBLIC_API_URL, Expo tự inline lúc build — không cần thư viện
// ngoài). Sửa .env khi đổi IP LAN, không cần sửa file này. Fallback localhost cho trường hợp
// .env chưa tạo hoặc chạy bản web trên chính máy chạy backend.
export const API_BASE_URL = process.env.EXPO_PUBLIC_API_URL || 'http://172.20.10.2:5005';
