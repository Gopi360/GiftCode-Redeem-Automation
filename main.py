"""
KingShot Auto Gift Code Redeemer
---------------------------------
Polls kingshot.net/api/gift-codes every 15 minutes.
When a NEW code is detected, automatically redeems it
for every player in playerIDs.txt.

Author: Built by Gopi
"""

import time
import json
import os
import requests
import schedule
import logging
from datetime import datetime
from redeemer import redeem_code_for_all_players

# ─── Config ────────────────────────────────────────────────────────────────────
API_URL          = "https://kingshot.net/api/gift-codes"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PLAYER_IDS_FILE  = os.path.join(BASE_DIR, "playerIDs.txt")
SEEN_CODES_FILE  = os.path.join(BASE_DIR, "seen_codes.json")  # Tracks codes we've already processed
LOGS_DIR         = os.path.join(BASE_DIR, "logs")
CHECK_INTERVAL   = 15                  # How often to poll the API (minutes)
# ───────────────────────────────────────────────────────────────────────────────

# Set up logging to both console and file
os.makedirs(LOGS_DIR, exist_ok=True)
log_filename = os.path.join(LOGS_DIR, f"run_{datetime.now().strftime('%Y%m%d')}.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_filename, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)


def load_seen_codes() -> set:
    """Load the set of gift code strings we've already processed."""
    if not os.path.exists(SEEN_CODES_FILE):
        return set()
    with open(SEEN_CODES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return set(data.get("redeemed", []))


def save_seen_codes(codes: set):
    """Persist the set of processed codes to disk."""
    with open(SEEN_CODES_FILE, "w", encoding="utf-8") as f:
        json.dump({"redeemed": list(codes)}, f, indent=2)


def load_player_ids() -> list:
    """Read player IDs from playerIDs.txt (one ID per line, optional name after space)."""
    players = []
    if not os.path.exists(PLAYER_IDS_FILE):
        log.error(f"'{PLAYER_IDS_FILE}' not found! Please create it.")
        return players
    with open(PLAYER_IDS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(maxsplit=1)
            pid  = parts[0]
            name = parts[1] if len(parts) > 1 else pid
            players.append((pid, name))
    return players


def fetch_active_codes() -> list:
    """Call the KingShot API and return list of active gift code strings."""
    try:
        response = requests.get(API_URL, timeout=15)
        response.raise_for_status()
        data = response.json()
        codes = data.get("data", {}).get("giftCodes", [])
        return [c["code"] for c in codes if c.get("code")]
    except requests.RequestException as e:
        log.error(f"Failed to fetch gift codes from API: {e}")
        return []


def check_and_redeem():
    """Core job: check for new codes and redeem them."""
    log.info("─── Checking for new gift codes ───")

    active_codes = fetch_active_codes()
    if not active_codes:
        log.info("No active codes returned from API.")
        return

    log.info(f"API returned {len(active_codes)} active code(s): {active_codes}")

    seen_codes  = load_seen_codes()
    new_codes   = [c for c in active_codes if c not in seen_codes]

    if not new_codes:
        log.info("No new codes found. Nothing to redeem.")
        return

    log.info(f"🎁 NEW code(s) detected: {new_codes}")

    player_ids = load_player_ids()
    if not player_ids:
        log.warning("No player IDs loaded — skipping redemption.")
        return

    log.info(f"Loaded {len(player_ids)} players.")

    for code in new_codes:
        log.info(f"\n{'='*50}")
        log.info(f"  Redeeming code: {code}")
        log.info(f"{'='*50}")
        redeem_code_for_all_players(code, player_ids, log)
        seen_codes.add(code)
        save_seen_codes(seen_codes)
        log.info(f"✅ Finished processing code: {code}")

    log.info("─── Check complete ───\n")


def main():
    log.info("╔══════════════════════════════════════╗")
    log.info("║  KingShot Auto Gift Code Redeemer    ║")
    log.info("╚══════════════════════════════════════╝")
    log.info(f"Polling every {CHECK_INTERVAL} minutes.")
    log.info(f"Player file : {PLAYER_IDS_FILE}")
    log.info(f"Seen codes  : {SEEN_CODES_FILE}")

    # Run once immediately on startup, then on schedule
    check_and_redeem()
    schedule.every(CHECK_INTERVAL).minutes.do(check_and_redeem)

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
