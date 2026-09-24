"""Entry point for the Library Management SQL Server login demo."""

from ui.login_window import LoginWindow


def main() -> None:
    app = LoginWindow()
    app.mainloop()


if __name__ == "__main__":
    main()

