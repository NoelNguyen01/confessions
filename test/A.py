"""
A_1 problem
Đề bài: "Hệ thống quản lý Log bảo mật cho DropVault"
Giả sử hệ thống DropVault của og nhận được một danh sách các lượt truy cập dưới dạng một List chứa các Dictionary. Mỗi lượt truy cập gồm có: user_id (ID người dùng), action (hành động: "login" hoặc "download"), và status (trạng thái: "success" hoặc "failed").

Og hãy viết một hàm Python để lọc ra danh sách các user_id có hành vi đáng ngờ (độ rủi ro cao). Một người dùng bị coi là đáng ngờ khi thỏa mãn một trong hai điều kiện sau:

Có từ 3 lần đăng nhập thất bại ("failed") trở lên.

Thực hiện hành động "download" thành công nhưng trạng thái đăng nhập gần nhất trước đó lại là "failed".
"""

log_data_v0 = [
    {"user_id": "sam_lai", "action": "login", "status": "failed"},
    {"user_id": "bob_dev", "action": "login", "status": "failed"},
    {"user_id": "sam_lai", "action": "login", "status": "failed"},
    {"user_id": "alice_9x", "action": "login", "status": "success"},
    {"user_id": "sam_lai", "action": "login", "status": "failed"},
    {"user_id": "bob_dev", "action": "download", "status": "success"},
    {"user_id": "alice_9x", "action": "download", "status": "success"},
]  # output: ['sam_lai', 'bob_dev']

log_data_v1 = [
    {"user_id": "hacker_pro", "action": "Login", "status": "FAILED"},
    {"user_id": "hacker_pro", "action": "LOGIN", "status": "FAILED"},
    {"user_id": "hacker_pro", "action": "login", "status": "failed"},
    {
        "user_id": "time_traveler",
        "action": "login",
        "status": "failed",
        "timestamp": "2026-05-31 10:05:00",
    },
    {
        "user_id": "time_traveler",
        "action": "download",
        "status": "success",
        "timestamp": "2026-05-31 10:00:00",
    },
    {"user_id": "Mr_Spy", "action": "login", "status": "failed"},
    {"user_id": "Mr_Spy ", "action": "login", "status": "failed"},
    {"user_id": "Mr_Spy", "action": "login", "status": "failed"},
    {"user_id": "boolean_boy", "action": "login", "status": False},
    {"user_id": "clean_user", "action": "download", "status": "success"},
]  # output: ['hacker_pro', 'Mr_Spy']


log_data_v2 = [
    # Server A: Định dạng chuẩn
    {
        "user_id": "pro_coder",
        "action": "login",
        "status": "failed",
        "timestamp": "2026-05-31 09:00:01",
    },
    # Server B: Định dạng log hãm tài (dùng 'code' thay cho 'action', 'res' thay cho 'status')
    {
        "user_id": "pro_coder",
        "code": "login",
        "res": "failed",
        "timestamp": "2026-05-31 09:00:05",
    },
    # Kịch bản "tấn công phân tán": hacker dùng 3 user_id khác nhau nhưng cùng 1 IP
    # Hướng giải quyết: Phải phát hiện ra "Cụm tấn công" (Cluster) thay vì chỉ check từng user đơn lẻ.
    {
        "user_id": "hacker_1",
        "ip": "192.168.1.50",
        "action": "login",
        "status": "failed",
        "timestamp": "2026-05-31 10:00:01",
    },
    {
        "user_id": "hacker_2",
        "ip": "192.168.1.50",
        "action": "login",
        "status": "failed",
        "timestamp": "2026-05-31 10:00:02",
    },
    {
        "user_id": "hacker_3",
        "ip": "192.168.1.50",
        "action": "login",
        "status": "failed",
        "timestamp": "2026-05-31 10:00:03",
    },
    # Kịch bản "đánh tráo khái niệm": Hành động 'access' cũng là 'login'
    {
        "user_id": "shadow_man",
        "action": "access",
        "status": "failed",
        "timestamp": "2026-05-31 11:00:01",
    },
    {
        "user_id": "shadow_man",
        "action": "login",
        "status": "failed",
        "timestamp": "2026-05-31 11:00:02",
    },
    {
        "user_id": "shadow_man",
        "action": "login",
        "status": "failed",
        "timestamp": "2026-05-31 11:00:03",
    },
    # Kịch bản "nhiễu tín hiệu": Log rác do lỗi đường truyền
    {
        "user_id": "pro_coder",
        "action": "login",
        "status": "failed",
        "timestamp": "2026-05-31 09:00:10",
    },
    {"garbage": "data", "info": "none"},
]  # output: ['192.168.1.50', 'pro_coder', 'shadow_man']


from datetime import datetime
from collections import defaultdict


def A_1():
    failed = {}
    ngi_Van = []
    log_data_sorted = sorted(
        log_data_v2,
        key=lambda x: datetime.strptime(
            x.get("timestamp", "1970-01-01 00:00:00"), "%Y-%m-%d %H:%M:%S"
        ),
    )
    for success in log_data_sorted:
        if not success.get("user_id") or success.get("user_id").strip() == "":
            continue
        if success.get("action").lower() == "login":
            if not success.get("status") or success.get("status").lower() == "failed":
                if success.get("user_id").strip() not in failed:
                    failed[success.get("user_id").strip()] = 0
                failed[success.get("user_id").strip()] += 1
            elif (
                success.get("status") == "success"
                and int(failed.get(success.get("user_id").strip(), 0)) < 3
            ):
                failed[success.get("user_id").strip()] = 0
        if success.get("action").lower() == "download":
            if (
                success.get("status") == "success"
                and int(failed.get(success.get("user_id").strip(), 0)) > 0
            ):
                if success.get("user_id").strip() not in ngi_Van:
                    ngi_Van.append(success.get("user_id").strip())
        if int(failed.get(success.get("user_id").strip(), 0)) >= 3:
            if success.get("user_id").strip() not in ngi_Van:
                ngi_Van.append(success.get("user_id").strip())
    return ngi_Van


"""
A_2 problem

Bài toán: "Chiếc ví điện tử bị lỗi đồng bộ"
Bối cảnh:
Hệ thống DropVault có tính năng ví tiền. Một người dùng thực hiện các giao dịch liên tiếp trong vòng 1 giây:

Deposit (Nạp tiền): 100k

Withdraw (Rút tiền): 50k

Withdraw (Rút tiền): 80k

Deposit (Nạp tiền): 30k

Vấn đề: Đôi khi hệ thống xử lý song song (Multi-threading), các giao dịch bị thực hiện không đúng thứ tự hoặc bị "nghẽn" (race condition). Bạn hãy viết thuật toán để xác định xem: Số dư cuối cùng của ví là bao nhiêu, và ở bước nào ví bị "Âm tiền" (bị hack/lỗi)?
"""

transactions = [
    {"tx_id": 1, "type": "deposit", "amount": 100},
    {"tx_id": 2, "type": "withdraw", "amount": 50},
    {
        "tx_id": 3,
        "type": "withdraw",
        "amount": 80,
    },  # Ở đây ví chỉ còn 50, rút 80 là sai!
    {"tx_id": 4, "type": "deposit", "amount": 30},
]
