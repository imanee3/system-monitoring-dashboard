import os
import time
from datetime import datetime
import random

import psutil
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

INTERVAL_SECONDS = 60



def get_client():
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
        # Si jamais le navigateur pose problème, remplace par: flow.run_console()
        creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "w", encoding="utf-8") as f:
            f.write(creds.to_json())

    return gspread.authorize(creds)


def get_cpu_temp_c():
    """Essaie psutil, sinon simule (utile sur Windows)."""
    try:
        temps = psutil.sensors_temperatures()
        if temps:
            for _, entries in temps.items():
                if entries:
                    return float(entries[0].current)
    except Exception:
        pass

    # fallback Windows : simulation
    return round(random.uniform(40, 70), 2)


def collect_metrics(prev_net):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory().percent
    disk = psutil.disk_usage("/").percent
    swap = psutil.swap_memory().percent
    proc_count = len(psutil.pids())
    temp = get_cpu_temp_c()  # peut être None

    net = psutil.net_io_counters()
    sent_mb = net.bytes_sent / (1024 * 1024)
    recv_mb = net.bytes_recv / (1024 * 1024)

    # Delta réseau (MB depuis la dernière mesure)
    if prev_net is None:
        sent_delta = 0.0
        recv_delta = 0.0
    else:
        sent_delta = max(0.0, sent_mb - prev_net[0])
        recv_delta = max(0.0, recv_mb - prev_net[1])

    return (
        ts,
        round(cpu, 2),
        round(ram, 2),
        round(disk, 2),
        round(swap, 2),
        None if temp is None else round(temp, 2),
        int(proc_count),
        round(sent_delta, 4),
        round(recv_delta, 4),
        (sent_mb, recv_mb),
    )


def main():
    gc = get_client()
    sh = gc.open(SPREADSHEET_NAME)
    ws_metrics = sh.worksheet("metrics")
    ws_last = sh.worksheet("last_only")

    prev_net = None
    print("✅ Monitoring démarré. CTRL+C pour arrêter.")

    try:
        while True:
            (
                ts,
                cpu,
                ram,
                disk,
                swap,
                temp,
                proc_count,
                net_sent_mb,
                net_recv_mb,
                prev_net,
            ) = collect_metrics(prev_net)

            row = [ts, cpu, ram, disk, swap, temp, proc_count, net_sent_mb, net_recv_mb]

            # 1) append historique
            ws_metrics.append_row(row, value_input_option="USER_ENTERED")

            # 2) update last_only (ligne 2)
            ws_last.update("A2:I2", [row], value_input_option="USER_ENTERED")

            print(f"[{ts}] CPU={cpu}% RAM={ram}% DISK={disk}% NETΔ={net_sent_mb}/{net_recv_mb} MB")

            time.sleep(INTERVAL_SECONDS)

    except KeyboardInterrupt:
        print("\n🛑 Arrêt du monitoring.")


if __name__ == "__main__":
    main()
