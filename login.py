import customtkinter as ctk
import ui.ctk_patch
from tkinter import messagebox
from db import dang_nhap_he_thong

# Cấu hình giao diện Dark Mode
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class LoginForm(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Quản Lý Thư Viện - Đăng Nhập")
        self.geometry("420x540")
        self.resizable(False, False)
        self.logged_in_user = None

        # Căn giữa màn hình
        self.center_window()

        # Container chính
        self.frame = ctk.CTkFrame(self, corner_radius=15)
        self.frame.pack(pady=20, padx=20, fill="both", expand=True)

        # Tiêu đề
        self.lbl_title = ctk.CTkLabel(
            self.frame, 
            text="ĐĂNG NHẬP HỆ THỐNG", 
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.lbl_title.pack(pady=(25, 6))

        self.lbl_subtitle = ctk.CTkLabel(
            self.frame, 
            text="Xác thực qua tài khoản SQL Server", 
            font=ctk.CTkFont(size=12), 
            text_color="gray"
        )
        self.lbl_subtitle.pack(pady=(0, 20))

        # Ô nhập tài khoản (Login name)
        self.txt_username = ctk.CTkEntry(
            self.frame, 
            placeholder_text="Tên đăng nhập (admin / nv_mai)", 
            width=300, 
            height=40
        )
        self.txt_username.pack(pady=(5, 12))

        # Ô nhập mật khẩu
        self.txt_password = ctk.CTkEntry(
            self.frame, 
            placeholder_text="Mật khẩu", 
            show="*", 
            width=300, 
            height=40
        )
        self.txt_password.pack(pady=(0, 15))

        # Gợi ý tài khoản thử nghiệm
        self.lbl_hints = ctk.CTkLabel(
            self.frame,
            text="Tài khoản thử nghiệm (Mật khẩu: 123456):\n• Quản lý: admin\n• Thủ thư: nv_mai / nv_nam\n• Độc giả tra cứu: docgia",
            font=ctk.CTkFont(size=11),
            text_color="#9CA3AF",
            justify="left"
        )
        self.lbl_hints.pack(pady=(0, 15))

        # Nút đăng nhập
        self.btn_login = ctk.CTkButton(
            self.frame, 
            text="Đăng Nhập", 
            width=300, 
            height=40, 
            font=ctk.CTkFont(weight="bold"),
            command=self.handle_login
        )
        self.btn_login.pack(pady=(0, 10))

        # Phím tắt Enter để đăng nhập
        self.bind("<Return>", lambda event: self.handle_login())

    def center_window(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def handle_login(self):
        username = self.txt_username.get().strip()
        password = self.txt_password.get().strip()

        if not username or not password:
            messagebox.showwarning("Thông báo", "Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu!")
            return

        try:
            user = dang_nhap_he_thong(username, password)
            if user:
                self.logged_in_user = user
                self.destroy()  # Đóng cửa sổ login sạch sẽ để nhường chỗ cho Dashboard
        except ValueError as val_err:
            messagebox.showerror("Thất bại", str(val_err))
            self.txt_password.delete(0, 'end')
        except Exception as err:
            messagebox.showerror("Lỗi CSDL", str(err))

def start_application():
    from ui.main_dashboard import MainDashboard

    while True:
        # Bước 1: Mở màn hình đăng nhập
        login_app = LoginForm()
        login_app.mainloop()

        # Nếu người dùng tắt cửa sổ đăng nhập mà không đăng nhập -> Thoát hẳn
        if not login_app.logged_in_user:
            break

        # Bước 2: Đăng nhập thành công -> Mở màn hình Dashboard
        current_user = login_app.logged_in_user
        logout_holder = {"logged_out": False}

        def on_logout():
            logout_holder["logged_out"] = True

        dashboard = MainDashboard(current_user, on_logout=on_logout)
        dashboard.mainloop()

        # Nếu người dùng đóng Dashboard bằng nút X (không phải bấm Đăng xuất) -> Thoát hẳn
        if not logout_holder["logged_out"]:
            break

if __name__ == "__main__":
    start_application()