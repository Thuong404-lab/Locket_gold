# Cấu hình thử Shadowrocket cho Locket

Đây là bộ thử sửa phản hồi RevenueCat **trên thiết bị**, tách riêng khỏi SDK Python. Không thực hiện giao dịch App Store, không cấp thuê bao trên server và không bảo đảm các chức năng Gold sẽ hoạt động. Chưa kiểm thử trên iPhone. Nếu Locket xác minh chữ ký phản hồi hoặc quyền trên server, kết quả giả có thể bị từ chối.

## Phạm vi

- Chỉ xử lý endpoint `api.revenuecat.com/v1/subscribers/...` và `/v1/receipts` khi header nhận diện Locket. Nếu không nhận diện được app, giữ nguyên dữ liệu.
- Script không gọi mạng, không lưu email/mật khẩu/token, không in body hoặc header. Không dùng lại file session Python.
- Chỉ bỏ ETag của request khớp. Không sửa IP, quốc gia, Firebase Remote Config, caption hoặc camera.
- Giữ nguyên phản hồi lỗi, dữ liệu không hợp lệ, dữ liệu thuê bao khác và quyền Gold đang có hiệu lực.
- Phản hồi giả có thời hạn 24 giờ tính từ lần sửa. Đây không phải gói Gold 24 giờ trên server, cũng không bảo đảm Gold còn hiển thị sau khi tắt Shadowrocket.
- Product ID dự phòng `com.locket02.premium.yearly` lấy từ bộ `Locket_15s_Full_Source/Locket.js` hiện có; chưa xác nhận khớp phiên bản Locket trên iPhone. Không xem test mock là bằng chứng kích hoạt thành công.

## Chuẩn bị link nhập

File cấu hình tham chiếu script trong repo `Thuong404-lab/Locket_gold`, nhánh `main`. **Link chưa sử dụng được cho đến khi hai file được đẩy lên repo**. Chỉ cần công khai `shadowrocket/locket-gold-local.js` và `shadowrocket/Locket_Gold_Local.conf`; không đưa session, lịch sử hoặc chứng chỉ lên GitHub.

Sau khi đã công khai và xác nhận URL trả đúng nội dung, link nhập là:

```text
https://raw.githubusercontent.com/Thuong404-lab/Locket_gold/main/shadowrocket/Locket_Gold_Local.conf
```

## Thao tác trên iPhone

1. Mở Shadowrocket → Config/Cấu hình → dấu `+`, nhập URL trên và tải cấu hình. Đây là profile thử riêng, không sửa profile đang dùng. Chọn profile thử và routing theo Config/Cấu hình.
2. Mở nút `ⓘ` của profile → HTTPS Decryption/Giải mã HTTPS. Tạo CA mới ngay trên điện thoại rồi cài chứng chỉ đó. Không nhập chứng chỉ/private key do người khác cung cấp.
3. Trong Cài đặt iOS, cài hồ sơ chứng chỉ vừa tạo; mở Cài đặt → Cài đặt chung → Giới thiệu → Cài đặt tin cậy chứng nhận và bật tin cậy đúng CA của Shadowrocket.
4. Bật kết nối Shadowrocket, đóng hẳn rồi mở Locket để kiểm tra. Profile dùng `FINAL,DIRECT`, không cần khai báo VPS.
5. Nếu không có thay đổi, chưa thể kết luận lỗi do server, rule, nhận diện app, product ID hay chữ ký. Không xóa dữ liệu hoặc cài lại Locket để thử mò. Chỉ gửi phiên bản iOS/Locket/Shadowrocket và ảnh trạng thái; che UID, URL có định danh, token và nội dung request.

HTTPS được giải mã theo **hostname RevenueCat dùng chung**, trước khi script kiểm tra app; lưu lượng app khác tới hostname đó vẫn có thể được Shadowrocket giải mã. Bộ script giữ nguyên nội dung của app không khớp và không ghi log. Tắt profile thử và tắt tin cậy/xóa CA thử sau khi hoàn tất nếu không dùng nữa; chọn lại profile cũ để khôi phục cấu hình mạng.

Tham khảo: [module/HTTPS Decryption trong Shadowrocket Wiki](https://github.com/LOWERTOP/Shadowrocket/wiki), [xác minh chữ ký RevenueCat](https://www.revenuecat.com/docs/customers/trusted-entitlements).

## Kiểm tra trên máy tính

```powershell
node --test shadowrocket/tests/locket-gold-local.test.cjs
```

Các test chỉ dùng dữ liệu giả, không gọi API và không xác nhận kết quả trên iPhone.
