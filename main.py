# !/usr/bin/env python3
import os
import subprocess
import time
import psutil
import requests
from datetime import datetime

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")
INTERVAL = 60 * 5
API_TIMEOUT = 10
PUBLIC_IP_SERVICE = "https://api.ipify.org"


def get_public_ip():
    try:
        return requests.get(PUBLIC_IP_SERVICE, timeout=3).text
    except Exception as e:
        return "N/A"


def get_docker_stats():
    try:
        result = subprocess.run(['docker', 'ps', '--format', '{{.Names}}|{{.Status}}'], capture_output=True, text=True, timeout=5)

        containers = []
        for line in result.stdout.splitlines():
            if not line.strip():
                continue
            try:
                name, status = line.split('|', 1)
                status_short = status.split()[0] if status else 'Unknown'
                containers.append(f"  • {name}: {status_short}")
            except Exception as e:
                containers.append(f"  • {line}")

        if not containers:
            return "  No containers running"
        return "\n".join(containers)
    except Exception as e:
        return f"  Docker error: {str(e)}"


def get_server_stats():
    cpu = psutil.cpu_percent(interval=1)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    net = psutil.net_io_counters()
    uptime = time.time() - psutil.boot_time()
    docker_info = get_docker_stats()

    return (
        "🖥️ <b>Server Status</b>\n"
        f"🌐 • IP: <code>{get_public_ip()}</code>\n"
        f"⏱️ • Uptime: {int(uptime // 3600)}h {int((uptime % 3600) // 60)}m\n"
        f"⚡ • CPU: {cpu}%\n"
        f"🧠 • RAM: {mem.percent}% ({mem.used / (1024 ** 3):.1f}GB)\n"
        f"💾 • Disk: {disk.percent}% ({disk.used / (1024 ** 3):.1f}GB)\n"
        f"📶 • Network: ↑{net.bytes_sent / (1024 ** 2):.1f}MB ↓{net.bytes_recv / (1024 ** 2):.1f}MB\n"
        f"🕒 • Server Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        "🐳 <b>Docker Containers:</b>\n"
        f"{docker_info}\n"
    )


def send_to_telegram(message):
    payload = {
        "chat_id": TELEGRAM_CHANNEL_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
        "message_auto_delete_time": 60 * 60 * 24,
    }

    try:
        response = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json=payload,
            timeout=API_TIMEOUT
        )
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        print(f"API Error: {type(e).__name__} - {e}", str(e.response.content))
        return False


def main():
    retry_delay = INTERVAL

    while True:
        stats = get_server_stats()
        success = send_to_telegram(stats)

        if not success:
            retry_delay = min(retry_delay * 2, 300)
            print(f"Retrying in {retry_delay} seconds...")
        else:
            retry_delay = INTERVAL

        time.sleep(retry_delay)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nTelemetry stopped")
    except Exception as e:
        print(f"Fatal error: {e}")
        raise e
