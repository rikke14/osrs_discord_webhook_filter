"""
Dink filter server — pytest suite
Tests every notification type. Value-filtered types get a low (50k) and high (5000k) test.
Run with: pytest test_server.py -v

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 LOCAL SETUP — run the filter server before running these tests
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Prerequisites:
  - Node.js 18+  →  https://nodejs.org
  - Python 3.8+  →  https://python.org
  - pytest + requests:
      pip install pytest requests        (Linux/macOS)
      pip install pytest requests        (Windows — same command)

── Linux / macOS ──────────────────────────────────────────────

  Terminal 1 — start the server:
    cd /path/to/osrs_discord_webhook_filter
    npm install
    DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/fake/url" npm start

  To also test the clan filter, add CLAN_NAME:
    DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/fake/url" CLAN_NAME="Duck Trumps" npm start

  Terminal 2 — run the tests:
    pytest test_server.py -v

  To test against a clan-filtered server, also set DINK_CLAN_NAME:
    DINK_CLAN_NAME="Duck Trumps" pytest test_server.py -v

── Windows (Command Prompt) ───────────────────────────────────

  Terminal 1 — start the server:
    cd C:\\path\\to\\osrs_discord_webhook_filter
    npm install
    set DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/fake/url
    npm start

  To also test the clan filter:
    set CLAN_NAME=Duck Trumps
    npm start

  Terminal 2 — run the tests:
    pytest test_server.py -v

  To test against a clan-filtered server:
    set DINK_CLAN_NAME=Duck Trumps
    pytest test_server.py -v

── Windows (PowerShell) ───────────────────────────────────────

  Terminal 1 — start the server:
    cd C:\\path\\to\\osrs_discord_webhook_filter
    npm install
    $env:DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/fake/url"
    npm start

  To also test the clan filter:
    $env:CLAN_NAME = "Duck Trumps"
    npm start

  Terminal 2 — run the tests:
    pytest test_server.py -v

  To test against a clan-filtered server:
    $env:DINK_CLAN_NAME = "Duck Trumps"
    pytest test_server.py -v

── Notes ───────────────────────────────────────────────────────

  - The DISCORD_WEBHOOK_URL can be a fake URL for testing — the server
    will attempt to forward but that's fine; what we're testing is whether
    the filter allows or blocks each event before it gets that far.
  - To test against a remote server (e.g. Railway), set DINK_FILTER_URL:
      DINK_FILTER_URL=https://your-app.railway.app pytest test_server.py -v
  - DINK_CLAN_NAME should match whatever CLAN_NAME you set on the server.
    If not set, clan filter tests are skipped.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import pytest
import requests
import os

SERVER_URL = os.environ.get("DINK_FILTER_URL", "http://localhost:3000")
WEBHOOK    = f"{SERVER_URL}/webhook"

# If set, clan filter tests run and use this name. Must match the server's CLAN_NAME.
CLAN_NAME  = os.environ.get("DINK_CLAN_NAME", "").strip() or None

LOW_VALUE  =    50_000   # should be blocked for value-filtered types
HIGH_VALUE = 50_000_000   # should pass for value-filtered types


# ── helpers ───────────────────────────────────────────────────────────────────

def post(payload: dict) -> requests.Response:
    return requests.post(WEBHOOK, json=payload, timeout=5)

def assert_forwarded(resp: requests.Response):
    assert resp.status_code == 200, resp.text
    assert resp.text.startswith("Forwarded"), f"Expected forwarded, got: {resp.text}"

def assert_skipped(resp: requests.Response):
    assert resp.status_code == 200, resp.text
    assert resp.text.startswith("Skipped"), f"Expected skipped, got: {resp.text}"

def player(name: str = "TestIron", clan: str = None) -> dict:
    """Base player fields. Uses CLAN_NAME env var if no clan is passed."""
    p = {"playerName": name}
    if clan is not None:
        p["clanName"] = clan
    elif CLAN_NAME:
        p["clanName"] = CLAN_NAME
    return p


# ── health ────────────────────────────────────────────────────────────────────

def test_health():
    resp = requests.get(f"{SERVER_URL}/health", timeout=5)
    assert resp.status_code == 200
    assert resp.text == "OK"


# ── CLAN FILTER ───────────────────────────────────────────────────────────────

@pytest.mark.skipif(CLAN_NAME is None, reason="DINK_CLAN_NAME not set — skipping clan filter tests")
def test_clan_filter_correct_clan_forwards():
    """Event from the correct clan should pass through."""
    resp = post({**player(clan=CLAN_NAME), "type": "PET", "extra": {"petName": "Ikkle hydra", "duplicate": False}})
    assert_forwarded(resp)

@pytest.mark.skipif(CLAN_NAME is None, reason="DINK_CLAN_NAME not set — skipping clan filter tests")
def test_clan_filter_wrong_clan_skipped():
    """Event from a different clan should be blocked."""
    resp = post({**player(clan="Some Other Clan"), "type": "PET", "extra": {"petName": "Ikkle hydra", "duplicate": False}})
    assert_skipped(resp)

@pytest.mark.skipif(CLAN_NAME is None, reason="DINK_CLAN_NAME not set — skipping clan filter tests")
def test_clan_filter_case_insensitive():
    """Clan name check should be case-insensitive."""
    resp = post({**player(clan=CLAN_NAME.upper()), "type": "PET", "extra": {"petName": "Ikkle hydra", "duplicate": False}})
    assert_forwarded(resp)

@pytest.mark.skipif(CLAN_NAME is None, reason="DINK_CLAN_NAME not set — skipping clan filter tests")
def test_clan_filter_no_clan_name_skipped():
    """Event with no clanName field should be blocked when filter is active."""
    payload = {"type": "PET", "playerName": "TestIron", "extra": {"petName": "Ikkle hydra", "duplicate": False}}
    resp = post(payload)
    assert_skipped(resp)


# ── COLLECTION ────────────────────────────────────────────────────────────────

def test_collection_high_value():
    resp = post({
        **player(),
        "type": "COLLECTION",
        "extra": {
            "itemName": "Abyssal whip",
            "itemId": 4151,
            "price": HIGH_VALUE,
            "completedEntries": 100,
            "totalEntries": 1443,
        },
    })
    assert_forwarded(resp)

def test_collection_low_value():
    resp = post({
        **player(),
        "type": "COLLECTION",
        "extra": {
            "itemName": "Bronze arrow",
            "itemId": 882,
            "price": LOW_VALUE,
            "completedEntries": 101,
            "totalEntries": 1443,
        },
    })
    assert_skipped(resp)


# ── PET ───────────────────────────────────────────────────────────────────────

def test_pet():
    resp = post({
        **player(),
        "type": "PET",
        "extra": {
            "petName": "Ikkle hydra",
            "duplicate": False,
        },
    })
    assert_forwarded(resp)

def test_pet_duplicate():
    """Duplicate pets should not forward."""
    resp = post({
        **player(),
        "type": "PET",
        "extra": {
            "petName": "Ikkle hydra",
            "duplicate": True,
        },
    })
    assert_skipped(resp)


# ── LOOT ─────────────────────────────────────────────────────────────────────

def _loot_payload(total_value: int) -> dict:
    return {
        **player(),
        "type": "LOOT",
        "extra": {
            "source": "Zulrah",
            "items": [
                {"id": 12934, "quantity": 1, "priceEach": total_value, "name": "Tanzanite fang"},
            ],
        },
    }

def test_loot_high_value():
    assert_forwarded(post(_loot_payload(HIGH_VALUE)))

def test_loot_low_value():
    assert_skipped(post(_loot_payload(LOW_VALUE)))


# ── CLUE ─────────────────────────────────────────────────────────────────────
# Disabled in config — all clue tests should be skipped regardless of value/tier

def _clue_payload(tier: str, total_value: int) -> dict:
    return {
        **player(),
        "type": "CLUE",
        "extra": {
            "clueType": tier,
            "numberCompleted": 42,
            "items": [
                {"id": 1234, "quantity": 1, "priceEach": total_value, "name": "Clue reward item"},
            ],
        },
    }

def test_clue_disabled_high_value():
    assert_skipped(post(_clue_payload("Elite", HIGH_VALUE)))

def test_clue_disabled_low_value():
    assert_skipped(post(_clue_payload("Elite", LOW_VALUE)))


# ── DEATH ─────────────────────────────────────────────────────────────────────
# Disabled in config

def _death_payload(value_lost: int, is_pvp: bool = False) -> dict:
    return {
        **player(),
        "type": "DEATH",
        "extra": {
            "valueLost": value_lost,
            "isPvp": is_pvp,
            "keptItems": [],
            "lostItems": [
                {"id": 314, "quantity": 1, "priceEach": value_lost, "name": "Some item"},
            ],
            "location": {"regionId": 10546, "plane": 0, "instanced": False},
        },
    }

def test_death_disabled_high_value():
    assert_skipped(post(_death_payload(HIGH_VALUE)))

def test_death_disabled_low_value():
    assert_skipped(post(_death_payload(LOW_VALUE)))


# ── LEVEL ─────────────────────────────────────────────────────────────────────
# Disabled in config

def _level_payload(skill: str, level: int) -> dict:
    return {
        **player(),
        "type": "LEVEL",
        "extra": {
            "levelledSkills": {skill: level},
            "allSkills": {skill: level},
            "combatLevel": {"value": 126, "increased": False},
        },
    }

def test_level_disabled_99():
    assert_skipped(post(_level_payload("Slayer", 99)))

def test_level_disabled_50():
    assert_skipped(post(_level_payload("Cooking", 50)))


# ── KILL COUNT ────────────────────────────────────────────────────────────────
# Disabled in config

def _kc_payload(boss: str, count: int, is_pb: bool = False) -> dict:
    return {
        **player(),
        "type": "KILL_COUNT",
        "extra": {
            "bossName": boss,
            "count": count,
            "isPersonalBest": is_pb,
        },
    }

def test_kc_disabled_pb():
    assert_skipped(post(_kc_payload("Zulrah", 100, is_pb=True)))

def test_kc_disabled_normal():
    assert_skipped(post(_kc_payload("Zulrah", 50)))


# ── SLAYER ────────────────────────────────────────────────────────────────────
# Disabled in config

def _slayer_payload(points: int) -> dict:
    return {
        **player(),
        "type": "SLAYER",
        "extra": {
            "slayerTask": "Abyssal demons",
            "slayerCompleted": "200",
            "slayerPoints": str(points),
            "killCount": 200,
            "monster": "Abyssal demon",
        },
    }

def test_slayer_disabled_high_points():
    assert_skipped(post(_slayer_payload(1000)))

def test_slayer_disabled_low_points():
    assert_skipped(post(_slayer_payload(15)))


# ── QUEST ─────────────────────────────────────────────────────────────────────
# Disabled in config

def test_quest_disabled():
    resp = post({
        **player(),
        "type": "QUEST",
        "extra": {
            "questName": "Dragon Slayer II",
            "completedQuests": 50,
            "totalQuests": 156,
            "questPoints": 300,
            "totalQuestPoints": 293,
        },
    })
    assert_skipped(resp)


# ── COMBAT ACHIEVEMENT ────────────────────────────────────────────────────────
# Disabled in config

def _ca_payload(tier: str) -> dict:
    return {
        **player(),
        "type": "COMBAT_ACHIEVEMENT",
        "extra": {
            "tier": tier,
            "task": "Whisperer speed-runner (4 minutes)",
        },
    }

def test_combat_achievement_disabled_grandmaster():
    assert_skipped(post(_ca_payload("Grandmaster")))

def test_combat_achievement_disabled_easy():
    assert_skipped(post(_ca_payload("Easy")))


# ── ACHIEVEMENT DIARY ─────────────────────────────────────────────────────────
# Disabled in config

def _diary_payload(difficulty: str) -> dict:
    return {
        **player(),
        "type": "ACHIEVEMENT_DIARY",
        "extra": {
            "area": "Karamja",
            "difficulty": difficulty,
        },
    }

def test_diary_disabled_elite():
    assert_skipped(post(_diary_payload("Elite")))

def test_diary_disabled_easy():
    assert_skipped(post(_diary_payload("Easy")))


# ── SPEEDRUN ──────────────────────────────────────────────────────────────────
# Disabled in config

def test_speedrun_disabled_pb():
    resp = post({
        **player(),
        "type": "SPEEDRUN",
        "extra": {
            "questName": "Cook's Assistant",
            "isPersonalBest": True,
            "currentTime": {"ticks": 100, "precise": "1:00.00"},
        },
    })
    assert_skipped(resp)

def test_speedrun_disabled_normal():
    resp = post({
        **player(),
        "type": "SPEEDRUN",
        "extra": {
            "questName": "Cook's Assistant",
            "isPersonalBest": False,
            "currentTime": {"ticks": 200, "precise": "2:00.00"},
        },
    })
    assert_skipped(resp)


# ── BA GAMBLE ─────────────────────────────────────────────────────────────────
# Disabled in config

def _ba_payload(total_value: int) -> dict:
    return {
        **player(),
        "type": "BA_GAMBLE",
        "extra": {
            "items": [
                {"id": 3486, "quantity": 1, "priceEach": total_value, "name": "Fighter torso"},
            ],
        },
    }

def test_ba_gamble_disabled_high_value():
    assert_skipped(post(_ba_payload(HIGH_VALUE)))

def test_ba_gamble_disabled_low_value():
    assert_skipped(post(_ba_payload(LOW_VALUE)))


# ── GRAND EXCHANGE ────────────────────────────────────────────────────────────
# Disabled in config

def test_grand_exchange_disabled():
    resp = post({
        **player(),
        "type": "GRAND_EXCHANGE",
        "extra": {
            "item": {"id": 4151, "quantity": 1, "priceEach": HIGH_VALUE, "name": "Abyssal whip"},
            "status": "BOUGHT",
            "bought": True,
        },
    })
    assert_skipped(resp)


# ── TRADE ─────────────────────────────────────────────────────────────────────
# Disabled in config

def test_trade_disabled():
    resp = post({
        **player(),
        "type": "TRADE",
        "extra": {
            "counterparty": "SomePlayer",
            "receivedItems": [
                {"id": 995, "quantity": HIGH_VALUE, "priceEach": 1, "name": "Coins"},
            ],
            "givenItems": [],
        },
    })
    assert_skipped(resp)


# ── LOGIN ─────────────────────────────────────────────────────────────────────
# Disabled in config

def test_login_disabled():
    resp = post({
        **player(),
        "type": "LOGIN",
        "extra": {},
    })
    assert_skipped(resp)


# ── CHAT ──────────────────────────────────────────────────────────────────────
# Disabled in config

def test_chat_disabled():
    resp = post({
        **player(),
        "type": "CHAT",
        "extra": {
            "message": "Finally got the drop!",
            "sender": "TestIron",
            "type": "GAME",
        },
    })
    assert_skipped(resp)


# ── UNKNOWN TYPE ──────────────────────────────────────────────────────────────

def test_unknown_type_forwards_by_default():
    """Unknown types should be forwarded so nothing is silently lost."""
    resp = post({
        **player(),
        "type": "SOME_FUTURE_TYPE",
        "extra": {},
    })
    assert_forwarded(resp)
