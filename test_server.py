"""
Dink filter server — pytest suite
Tests every notification type. Value-filtered types get a low (50k) and high (5000k) test.
Run with: pytest test_server.py -v
Requires the server running at SERVER_URL (default: http://localhost:3000)
"""

import pytest
import requests
import os

SERVER_URL = os.environ.get("DINK_FILTER_URL", "http://localhost:3000")
WEBHOOK    = f"{SERVER_URL}/webhook"

LOW_VALUE  =   50_000   # should be blocked for value-filtered types
HIGH_VALUE = 5_000_000  # should pass for value-filtered types


# ── helpers ───────────────────────────────────────────────────────────────────

def post(payload: dict) -> requests.Response:
    return requests.post(WEBHOOK, json=payload, timeout=5)

def assert_forwarded(resp: requests.Response):
    assert resp.status_code == 200, resp.text
    assert resp.text.startswith("Forwarded"), f"Expected forwarded, got: {resp.text}"

def assert_skipped(resp: requests.Response):
    assert resp.status_code == 200, resp.text
    assert resp.text.startswith("Skipped"), f"Expected skipped, got: {resp.text}"


# ── health ────────────────────────────────────────────────────────────────────

def test_health():
    resp = requests.get(f"{SERVER_URL}/health", timeout=5)
    assert resp.status_code == 200
    assert resp.text == "OK"


# ── COLLECTION ────────────────────────────────────────────────────────────────

def test_collection_high_value():
    resp = post({
        "type": "COLLECTION",
        "playerName": "TestIron",
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
        "type": "COLLECTION",
        "playerName": "TestIron",
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
        "type": "PET",
        "playerName": "TestIron",
        "extra": {
            "petName": "Ikkle hydra",
            "duplicate": False,
        },
    })
    assert_forwarded(resp)

def test_pet_duplicate():
    """Duplicate pets should not forward."""
    resp = post({
        "type": "PET",
        "playerName": "TestIron",
        "extra": {
            "petName": "Ikkle hydra",
            "duplicate": True,
        },
    })
    assert_skipped(resp)


# ── LOOT ─────────────────────────────────────────────────────────────────────

def _loot_payload(total_value: int) -> dict:
    return {
        "type": "LOOT",
        "playerName": "TestIron",
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
        "type": "CLUE",
        "playerName": "TestIron",
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
        "type": "DEATH",
        "playerName": "TestIron",
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
        "type": "LEVEL",
        "playerName": "TestIron",
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
        "type": "KILL_COUNT",
        "playerName": "TestIron",
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
        "type": "SLAYER",
        "playerName": "TestIron",
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
        "type": "QUEST",
        "playerName": "TestIron",
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
        "type": "COMBAT_ACHIEVEMENT",
        "playerName": "TestIron",
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
        "type": "ACHIEVEMENT_DIARY",
        "playerName": "TestIron",
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
        "type": "SPEEDRUN",
        "playerName": "TestIron",
        "extra": {
            "questName": "Cook's Assistant",
            "isPersonalBest": True,
            "currentTime": {"ticks": 100, "precise": "1:00.00"},
        },
    })
    assert_skipped(resp)

def test_speedrun_disabled_normal():
    resp = post({
        "type": "SPEEDRUN",
        "playerName": "TestIron",
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
        "type": "BA_GAMBLE",
        "playerName": "TestIron",
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
        "type": "GRAND_EXCHANGE",
        "playerName": "TestIron",
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
        "type": "TRADE",
        "playerName": "TestIron",
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
        "type": "LOGIN",
        "playerName": "TestIron",
        "extra": {},
    })
    assert_skipped(resp)


# ── CHAT ──────────────────────────────────────────────────────────────────────
# Disabled in config

def test_chat_disabled():
    resp = post({
        "type": "CHAT",
        "playerName": "TestIron",
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
        "type": "SOME_FUTURE_TYPE",
        "playerName": "TestIron",
        "extra": {},
    })
    assert_forwarded(resp)
