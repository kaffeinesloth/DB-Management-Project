"""Application entry point inheriting 100% lifecycle from feature/qltv:login.py."""

import os
from pathlib import Path
import sys


def _bootstrap_runtime() -> None:
    """Relaunch with the project runtime before importing GUI/ODBC packages.

    This makes ``python3 main.py`` reliable even when the caller forgot to
    activate ``.venv``.  Microsoft ODBC Driver 18 also needs Homebrew's
    OpenSSL directory on macOS; that environment value must exist before the
    driver is loaded, so the process is relaunched when necessary.
    """
    project_root = Path(__file__).resolve().parent
    venv_root = project_root / ".venv"
    if sys.platform == "win32":
        venv_python = venv_root / "Scripts" / "python.exe"
    else:
        venv_python = venv_root / "bin" / "python"

    environment = os.environ.copy()
    runtime_changed = False

    if sys.platform == "darwin":
        openssl_candidates = (
            Path("/opt/homebrew/opt/openssl@3/lib"),
            Path("/usr/local/opt/openssl@3/lib"),
        )
        openssl_dir = next((path for path in openssl_candidates if path.is_dir()), None)
        if openssl_dir is not None:
            current_paths = [
                value for value in environment.get("DYLD_LIBRARY_PATH", "").split(":")
                if value
            ]
            openssl_value = str(openssl_dir)
            if openssl_value not in current_paths:
                environment["DYLD_LIBRARY_PATH"] = ":".join(
                    [openssl_value, *current_paths]
                )
                runtime_changed = True

    using_project_venv = Path(sys.prefix).resolve() == venv_root.resolve()
    if venv_python.is_file() and not using_project_venv:
        os.execve(
            str(venv_python),
            [str(venv_python), str(Path(__file__).resolve()), *sys.argv[1:]],
            environment,
        )

    if runtime_changed and environment.get("LMS_RUNTIME_BOOTSTRAPPED") != "1":
        environment["LMS_RUNTIME_BOOTSTRAPPED"] = "1"
        os.execve(sys.executable, [sys.executable, *sys.argv], environment)


if __name__ == "__main__":
    _bootstrap_runtime()


import customtkinter as ctk
import ctk_patch
from login.login_screen import LoginForm
from dashboard import MainDashboard

# Cấu hình giao diện Dark Mode chuẩn đồ án
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


def start_application() -> None:
    """
    Vòng đời ứng dụng Quản Lý Thư Viện:
    1. Khởi chạy cửa sổ đăng nhập riêng biệt LoginForm (420x560).
    2. Xác thực thành công -> Mở cửa sổ Dashboard chính (1260x740) với phân quyền người dùng.
    3. Khi đăng xuất -> Quay trở lại cửa sổ đăng nhập.
    4. Khi tắt cửa sổ -> Thoát hoàn toàn ứng dụng.
    """
    while True:
        # Bước 1: Mở màn hình đăng nhập
        login_app = LoginForm()
        login_app.mainloop()

        # Nếu người dùng tắt cửa sổ đăng nhập mà không đăng nhập -> Thoát hẳn
        if not getattr(login_app, "logged_in_user", None):
            try:
                login_app.destroy()
            except Exception:
                pass
            break

        # Bước 2: Đăng nhập thành công -> Hủy cửa sổ đăng nhập và Mở Dashboard
        current_user = login_app.logged_in_user
        try:
            login_app.destroy()
        except Exception:
            pass

        logout_holder = {"logged_out": False}

        def on_logout():
            logout_holder["logged_out"] = True

        dashboard = MainDashboard(current_user, on_logout=on_logout)
        dashboard.mainloop()

        try:
            dashboard.destroy()
        except Exception:
            pass

        # Nếu người dùng đóng Dashboard bằng nút X (không phải bấm Đăng xuất) -> Thoát hẳn
        if not logout_holder["logged_out"]:
            break


# Bí danh tương thích
LibraryApplication = MainDashboard

if __name__ == "__main__":
    start_application()
