import os
import gspread
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SPREADSHEET_NAME = "System Monitoring"
CREDENTIALS_PATH = os.path.join("config", "credentials.json")
TOKEN_PATH = os.path.join("config", "token.json")


def get_client():
    creds = None

    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
        creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "w", encoding="utf-8") as f:
            f.write(creds.to_json())

    return gspread.authorize(creds)


def main():
    gc = get_client()
    sh = gc.open(SPREADSHEET_NAME)

    # Test write into metrics
    ws_metrics = sh.worksheet("metrics")
    ws_metrics.append_row(
        ["2026-02-19 15:00:00", 10, 20, 30, 0, 0, 123, 1.2, 3.4],
        value_input_option="USER_ENTERED",
    )

    # Test update last_only (row 2)
    ws_last = sh.worksheet("last_only")
    ws_last.update(
        "A2:I2",
        [["2026-02-19 15:00:00", 10, 20, 30, 0, 0, 123, 1.2, 3.4]],
        value_input_option="USER_ENTERED",
    )

    print("✅ Connexion OK : écriture dans metrics + last_only réussie")


if __name__ == "__main__":
    main()
