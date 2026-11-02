#!/usr/bin/env python3
"""Đăng nhập Locket bằng thông tin nhập tại terminal và dùng lại phiên đã lưu.

Mật khẩu không được ghi vào mã nguồn. File session chứa token dạng văn bản
thuần: chỉ giữ trên máy của bạn và không đưa lên GitHub.
"""

import os
import sys
import warnings
from getpass import GetPassWarning, getpass

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from requests.exceptions import RequestException

from locketlam import LocketClient
from locketlam.exceptions import AuthenticationError, LocketError

SESSION_FILE = os.path.join(REPO_ROOT, "locketlam_session.json")


def main():
    print("🔑 ĐĂNG NHẬP VÀ QUẢN LÝ PHIÊN LOCKET")
    client = LocketClient(session_path=SESSION_FILE)

    # Giữ cấu hình thiết bị đã lưu. Client mới tự dùng cấu hình mặc định.
    # Nếu cần thông số riêng, gọi client.set_device(auto_emulate=False, ...).
    try:
        if client.is_authenticated():
            print("Đã tìm thấy phiên đăng nhập, đang kiểm tra token...")
        else:
            print("Nhập tài khoản tại terminal; không điền mật khẩu vào file Python.")
            email = input("Email Locket: ").strip()
            if not email:
                print("Email không được để trống.")
                return 1

            # Dừng nếu terminal không thể ẩn mật khẩu, tránh getpass chuyển
            # sang chế độ nhập có hiển thị ký tự.
            with warnings.catch_warnings():
                warnings.simplefilter("error", GetPassWarning)
                password = getpass("Mật khẩu Locket (không hiển thị ký tự): ")
            if not password:
                print("Mật khẩu không được để trống.")
                return 1

            try:
                client.login(email=email, password=password)
            finally:
                del password

        # Kiểm tra/làm mới token đồng bộ trước khi báo thành công.
        client.session.get_valid_token()
    except GetPassWarning:
        print("Không thể ẩn mật khẩu. Hãy chạy bằng terminal tương tác của VS Code hoặc PowerShell.")
        return 1
    except (EOFError, KeyboardInterrupt):
        print("\nĐã hủy đăng nhập.")
        return 1
    except AuthenticationError:
        print("Xác thực thất bại. Kiểm tra thông tin đăng nhập hoặc phiên đã lưu.")
        return 1
    except RequestException:
        print("Không thể kết nối máy chủ đăng nhập. Kiểm tra kết nối mạng và thử lại.")
        return 1
    except LocketError:
        print("Không thể hoàn tất đăng nhập. Vui lòng kiểm tra cấu hình và thử lại.")
        return 1

    print("✅ Phiên đăng nhập đã sẵn sàng. Token không được hiển thị.")
    print(f"💾 File phiên: {SESSION_FILE}")
    print("File này chứa token đăng nhập dạng văn bản thuần. Không chia sẻ hoặc đưa lên GitHub.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
