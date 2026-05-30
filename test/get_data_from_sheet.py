import gspread
from oauth2client.service_account import ServiceAccountCredentials

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)

sheet = client.open("Confession_app").sheet1
data = sheet.get_all_records()

latest_entry = data[-1]

print(latest_entry.get("Confession của bạn là gì?"))
