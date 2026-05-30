import requests


def dang_bai_fanpage():
    # Điền chính xác thông tin thực tế của og vào đây
    page_id = "1005200049343949"
    page_token = "EAGJpK9z6nc0BRkH7ZAZAARbCAzbxupX1dnXLW6VO4UomT8QSZAZCfKICSsF1ZBV0ZBfr4RSqncgEhL2BDp3lAEwHVvkHJKRmfHV6FsuAMcDegkuVAPeZCQ0AbwcFs9ZCFmdFeKHSScJJY0RqNZB2F4e0975uVaMRb8AWMo3qouKDc4Wn6sAvvhPum2ZB5Gi7sZClktE9ZCI323vCzbYpgmaFdgojQneewKyhF23quqAtfo0ZD"

    url = f"https://graph.facebook.com/v25.0/{page_id}/feed"

    payload = {
        "message": "Hello World! Test hệ thống gửi bài tự động từ script Python.",
        "access_token": page_token,
    }

    try:
        response = requests.post(url, data=payload)
        res_data = response.json()

        if response.status_code == 200 and "id" in res_data:
            print(f"🎉 Đăng bài thành công rồi og ơi! ID bài viết: {res_data['id']}")
        else:
            print("❌ Thất bại mất rồi. Log lỗi chi tiết từ Facebook:")
            print(res_data)

    except Exception as e:
        print(f"❌ Lỗi kết nối HTTP: {e}")


if __name__ == "__main__":
    dang_bai_fanpage()
