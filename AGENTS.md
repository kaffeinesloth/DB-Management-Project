# 🤖 AI Assistant Self-Verification & Testing Guidelines (Quy tắc Tự Kiểm Chứng)

Tài liệu quy chuẩn dành cho Trợ lý AI khi phát triển, sửa lỗi và refactor trong dự án **DB-Management-Project**.

---

## 🎯 NGUYÊN TẮC CỐT LÕI (CORE PRINCIPLES)

### 1. 🧪 Tự test kết quả thực tế trước khi kết luận (Mandatory Self-Testing)
* **Tuyệt đối KHÔNG** tuyên bố "đã xong 100%", "hết lỗi", hoặc "chạy ngon lành" chỉ dựa trên suy đoán hoặc việc chỉ sửa code trên lý thuyết.
* **Quy trình bắt buộc trước khi phản hồi người dùng:**
  1. **Biên dịch cú pháp:** Chạy `python -m py_compile` cho tất cả các file liên quan.
  2. **Chạy Unit Test:** Chạy `python -m unittest discover -s tests` để đảm bảo không làm gãy các tính năng cũ (No Regression).
  3. **Chạy kiểm thử tích hợp (End-to-End Diagnostic):** Chạy thử nghiệm thực tế luồng ứng dụng hoàn chỉnh:
     * Xác thực tài khoản với CSDL thực tế.
     * Khởi tạo giao diện (Window / Dashboard).
     * Duyệt qua từng View / Tab để xác nhận mọi thành phần UI render thành công, không bị văng `TclError` hay `pyodbc.Error`.
     * Xác nhận bảng hiển thị đúng số dòng dữ liệu thực tế (`len(tree.get_children()) > 0`).

---

### 2. 🔍 Kiểm tra log chi tiết và ngoại lệ ngầm (Traceback & Deep Logging)
* Không nuốt lỗi ngầm (`silent fail`).
* Luôn kiểm tra log `stderr`, `stdout` và bắt trọn vẹn `traceback.print_exc()`.
* Chú ý đặc biệt các lỗi UI runtime:
  * Trùng khóa `iid` trong Tkinter Treeview (`_tkinter.TclError: Item X already exists`).
  * Luồng nền (Background thread) gặp lỗi nhưng không ném ra giao diện chính.
  * Các callback hẹn giờ `after()` bị treo hoặc gọi sau khi widget đã bị hủy (`destroy`).

---

### 3. 🌐 Tính tương thích môi trường làm việc nhóm (Environment Parity)
* Luôn nạp cấu hình từ `.env` (`python-dotenv`) để tương thích với môi trường của từng thành viên:
  * Kiểm tra đúng cổng CSDL Docker (`MSSQL_PORT=14333` vs `1433`).
  * Tuyệt đối không hardcode cổng cục bộ nếu có thể gây fallback ngoài ý muốn sang các instance SQL Server khác trên máy.
* Trước khi kết luận CSDL thiếu Stored Procedure hay Table, luôn kiểm tra xem kết nối hiện tại đang trỏ vào đúng CSDL mục tiêu (`LibraryManagement` trên Docker) hay bị nhảy sang CSDL khác (`QLTV` cục bộ).

---

### 4. 📊 Báo cáo minh bạch & Cung cấp bằng chứng kiểm thử (Evidence-Based Reporting)
* Khi báo cáo cho người dùng, luôn đính kèm:
  * **Log lỗi thực tế:** Nguyên nhân kỹ thuật cụ thể.
  * **Bằng chứng sau khi sửa:** Số lượng bản ghi truy vấn được, kết quả test pass, trạng thái các tab.
  * Nếu phát hiện lỗi mới trong quá trình test, lập tức sửa và chứng minh đã test thành công trước khi bàn giao lại cho người dùng.
