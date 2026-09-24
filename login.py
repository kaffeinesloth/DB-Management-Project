import customtkinter as ctk
from tkinter import messagebox
from db import kiem_tra_dang_nhap

# Cấu hình giao diện Dark Mode
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class LoginForm(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Quản Lý Thư Viện - Đăng Nhập")
        self.geometry("420x530")
        self.resizable(False, False)

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
            placeholder_text="Tên đăng nhập (Login Name)", 
            width=300, 
            height=40
        )
        self.txt_username.pack(pady=(5, 3))
        self.txt_username.bind("<KeyRelease>", self.on_username_change)
        self.txt_username.bind("<FocusOut>", self.on_username_change)

        # Nhãn auto hiện thông tin Employee ID khi gõ username
        self.lbl_employee_info = ctk.CTkLabel(
            self.frame,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="#38BDF8"
        )
        self.lbl_employee_info.pack(pady=(0, 8))

        # Ô nhập mật khẩu
        self.txt_password = ctk.CTkEntry(
            self.frame, 
            placeholder_text="Mật khẩu", 
            show="*", 
            width=300, 
            height=40
        )
        self.txt_password.pack(pady=5)

        # Nút đăng nhập
        self.btn_login = ctk.CTkButton(
            self.frame, 
            text="Đăng Nhập", 
            width=300, 
            height=40, 
            font=ctk.CTkFont(weight="bold"),
            command=self.handle_login
        )
        self.btn_login.pack(pady=(20, 10))

        # Phím tắt Enter để đăng nhập
        self.bind("<Return>", lambda event: self.handle_login())

    def center_window(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def on_username_change(self, event=None):
        """Auto hiển thị Employee ID và họ tên khi người dùng gõ username."""
        login_name = self.txt_username.get().strip()
        if not login_name:
            self.lbl_employee_info.configure(text="")
            return

        from db import tra_cuu_nhan_vien_nhanh
        emp = tra_cuu_nhan_vien_nhanh(login_name)
        if emp:
            role_display = "Quản lý" if emp["RoleName"] == "QUANLY" else "Thủ thư"
            self.lbl_employee_info.configure(
                text=f"Mã NV: {emp['MANV']} - {emp['HoTen']} ({role_display})",
                text_color="#38BDF8"
            )
        else:
            self.lbl_employee_info.configure(
                text="Chưa tìm thấy nhân viên trong CSDL",
                text_color="#9CA3AF"
            )

    def handle_login(self):
        username = self.txt_username.get().strip()
        password = self.txt_password.get().strip()

        if not username or not password:
            messagebox.showwarning("Thông báo", "Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu!")
            return

        try:
            from db import dang_nhap_he_thong
            user = dang_nhap_he_thong(username, password)
            if user:
                # Ẩn cửa sổ đăng nhập và khởi chạy Dashboard
                self.withdraw()
                from ui.main_dashboard import MainDashboard

                def on_dashboard_close():
                    self.destroy()

                dashboard = MainDashboard(user, on_logout=self.show_login_again)
                dashboard.protocol("WM_DELETE_WINDOW", on_dashboard_close)
                dashboard.mainloop()
        except ValueError as val_err:
            messagebox.showerror("Thất bại", str(val_err))
            self.txt_password.delete(0, 'end')
        except Exception as err:
            messagebox.showerror("Lỗi CSDL", str(err))

    def show_login_again(self):
        """Hiện lại cửa sổ đăng nhập khi bấm Đăng xuất."""
        self.txt_password.delete(0, 'end')
        self.deiconify()

if __name__ == "__main__":
    app = LoginForm()
    app.mainloop()