const express = require("express");
const multer  = require("multer");
const fetch   = require("node-fetch");

const app    = express();
const upload = multer();

// ═══════════════════════════════════════════════════════════════════════════════
//  CONFIG — edit everything in this block to suit your clan
// ═══════════════════════════════════════════════════════════════════════════════

const DISCORD_WEBHOOK_URL = process.env.DISCORD_WEBHOOK_URL; // set via env var
const PORT = process.env.PORT || 3000;

const CONFIG = {

  // ── COLLECTION LOG ──────────────────────────────────────────────────────────
  COLLECTION: {
    enabled:   true,
    minValue:  1_000_000,   // only notify if item GE value >= this (gp)
  },

  // ── PETS ────────────────────────────────────────────────────────────────────
  PET: {
    enabled: true,          // pets are always priceless — no value filter
  },

  // ── LOOT ────────────────────────────────────────────────────────────────────
  LOOT: {
    enabled:  true,
    minValue: 500_000,      // total loot value across all items in the drop
  },

  // ── CLUE SCROLLS ────────────────────────────────────────────────────────────
  CLUE: {
    enabled:    true,
    minValue:   250_000,    // total value of the clue reward
    // Tiers to notify for. Comment out any you don't want.
    // Options: "Beginner" | "Easy" | "Medium" | "Hard" | "Elite" | "Master"
    allowedTiers: [
      // "Beginner",
      // "Easy",
      // "Medium",
      "Hard",
      "Elite",
      "Master",
    ],
  },

  // ── DEATHS ──────────────────────────────────────────────────────────────────
  DEATH: {
    enabled:       true,
    pvpOnly:       false,   // true = only notify on PvP deaths
    minValueLost:  0,       // only notify if items lost >= this gp (0 = always)
  },

  // ── LEVELS ──────────────────────────────────────────────────────────────────
  LEVEL: {
    enabled:   true,
    // Only notify at or above this level. 99 = only 99s. 1 = all levels.
    minLevel:  99,
  },

  // ── KILL COUNT ──────────────────────────────────────────────────────────────
  KILL_COUNT: {
    enabled:          true,
    personalBestOnly: false,   // true = only notify on new personal bests
    // Milestone intervals — notify every N kills. 0 = every kill.
    // e.g. 100 = notify at 100, 200, 300...
    milestone:        0,
  },

  // ── SLAYER ──────────────────────────────────────────────────────────────────
  SLAYER: {
    enabled:   true,
    minPoints: 0,   // only notify if slayer points >= this (0 = always)
  },

  // ── QUESTS ──────────────────────────────────────────────────────────────────
  QUEST: {
    enabled: true,  // no filtering needed — quest completions are always notable
  },

  // ── COMBAT ACHIEVEMENTS ─────────────────────────────────────────────────────
  COMBAT_ACHIEVEMENT: {
    enabled: true,
    // Tiers to notify for. Comment out any you don't want.
    // Options: "Easy" | "Medium" | "Hard" | "Elite" | "Master" | "Grandmaster"
    allowedTiers: [
      // "Easy",
      // "Medium",
      "Hard",
      "Elite",
      "Master",
      "Grandmaster",
    ],
  },

  // ── ACHIEVEMENT DIARIES ─────────────────────────────────────────────────────
  ACHIEVEMENT_DIARY: {
    enabled: true,
    // Tiers to notify for. Comment out any you don't want.
    // Options: "Easy" | "Medium" | "Hard" | "Elite"
    allowedTiers: [
      // "Easy",
      // "Medium",
      "Hard",
      "Elite",
    ],
  },

  // ── SPEEDRUN ────────────────────────────────────────────────────────────────
  SPEEDRUN: {
    enabled:          true,
    personalBestOnly: false,   // true = only notify on new personal bests
  },

  // ── BARBARIAN ASSAULT GAMBLES ───────────────────────────────────────────────
  BA_GAMBLE: {
    enabled:  true,
    minValue: 0,    // total gamble reward value threshold (0 = always)
  },

  // ── GRAND EXCHANGE ──────────────────────────────────────────────────────────
  GRAND_EXCHANGE: {
    enabled: false,  // GE notifications are usually spammy — off by default
  },

  // ── TRADES ──────────────────────────────────────────────────────────────────
  TRADE: {
    enabled: false,
  },

  // ── LOGIN (character summary) ───────────────────────────────────────────────
  LOGIN: {
    enabled: false,
  },

  // ── CHAT MESSAGES ───────────────────────────────────────────────────────────
  CHAT: {
    enabled: false,
  },

};

// ═══════════════════════════════════════════════════════════════════════════════
//  END CONFIG
// ═══════════════════════════════════════════════════════════════════════════════

if (!DISCORD_WEBHOOK_URL) {
  console.error("ERROR: DISCORD_WEBHOOK_URL environment variable is not set.");
  process.exit(1);
}

// ── Middleware ─────────────────────────────────────────────────────────────────
// Dink sends multipart/form-data when a screenshot is attached,
// and application/json when there is no screenshot.
app.use((req, res, next) => {
  const ct = req.headers["content-type"] || "";
  if (ct.includes("multipart/form-data")) {
    upload.single("file")(req, res, next);
  } else {
    express.json()(req, res, next);
  }
});

// ── Main route ─────────────────────────────────────────────────────────────────
app.post("/webhook", async (req, res) => {
  try {
    let payload = parsePayload(req);
    if (!payload) return res.status(400).send("Invalid payload");

    const { type, extra = {} } = payload;
    const { allow, reason }    = shouldForward(type, extra);

    const tag = allow ? "[ALLOW]" : "[SKIP] ";
    console.log(`${tag} ${type.padEnd(20)} — ${reason}`);

    if (allow) {
      await forwardToDiscord(req, payload);
    }

    return res.status(200).send(allow ? `Forwarded: ${reason}` : `Skipped: ${reason}`);

  } catch (err) {
    console.error("Error processing webhook:", err);
    return res.status(500).send("Internal server error");
  }
});

app.get("/health", (_req, res) => res.send("OK"));

app.listen(PORT, () => {
  console.log(`Dink filter listening on port ${PORT}`);
  console.log(`Config summary:`);
  for (const [type, cfg] of Object.entries(CONFIG)) {
    console.log(`  ${type.padEnd(22)} enabled=${cfg.enabled}`);
  }
});

// ═══════════════════════════════════════════════════════════════════════════════
//  HANDLERS — one per Dink notification type
// ═══════════════════════════════════════════════════════════════════════════════

function shouldForward(type, extra) {
  const cfg = CONFIG[type];

  // Unknown type — forward by default so nothing is silently lost
  if (!cfg) return { allow: true, reason: `unknown type "${type}" — forwarding by default` };

  // Disabled entirely
  if (!cfg.enabled) return { allow: false, reason: "type disabled in config" };

  switch (type) {

    case "COLLECTION": {
      const { itemName = "?", price = 0 } = extra;
      if (price < cfg.minValue) {
        return { allow: false, reason: `${itemName} — ${gp(price)} below ${gp(cfg.minValue)} threshold` };
      }
      return { allow: true, reason: `${itemName} — ${gp(price)}` };
    }

    case "PET": {
      const { petName = "unknown pet", duplicate = false } = extra;
      return { allow: true, reason: `${petName}${duplicate ? " (duplicate)" : ""}` };
    }

    case "LOOT": {
      // Total value is the sum of all items in the drop
      const items      = extra.items ?? [];
      const totalValue = items.reduce((sum, i) => sum + (i.priceEach ?? 0) * (i.quantity ?? 1), 0);
      const source     = extra.source ?? "unknown";
      if (totalValue < cfg.minValue) {
        return { allow: false, reason: `${source} — ${gp(totalValue)} below ${gp(cfg.minValue)} threshold` };
      }
      return { allow: true, reason: `${source} — ${gp(totalValue)}` };
    }

    case "CLUE": {
      const { clueType = "", numberCompleted = 0, items = [] } = extra;
      const totalValue = items.reduce((sum, i) => sum + (i.priceEach ?? 0) * (i.quantity ?? 1), 0);

      if (!cfg.allowedTiers.includes(clueType)) {
        return { allow: false, reason: `${clueType} clue — tier not in allowedTiers` };
      }
      if (totalValue < cfg.minValue) {
        return { allow: false, reason: `${clueType} clue #${numberCompleted} — ${gp(totalValue)} below ${gp(cfg.minValue)} threshold` };
      }
      return { allow: true, reason: `${clueType} clue #${numberCompleted} — ${gp(totalValue)}` };
    }

    case "DEATH": {
      const { valueLost = 0, isPvp = false } = extra;
      if (cfg.pvpOnly && !isPvp) {
        return { allow: false, reason: `non-PvP death — pvpOnly is enabled` };
      }
      if (valueLost < cfg.minValueLost) {
        return { allow: false, reason: `death — ${gp(valueLost)} lost, below ${gp(cfg.minValueLost)} threshold` };
      }
      return { allow: true, reason: `${isPvp ? "PvP" : "PvE"} death — ${gp(valueLost)} lost` };
    }

    case "LEVEL": {
      const levelledSkills = extra.levelledSkills ?? {};
      const highestLevel   = Math.max(...Object.values(levelledSkills), 0);
      const skills         = Object.entries(levelledSkills).map(([s, l]) => `${s} ${l}`).join(", ");
      if (highestLevel < cfg.minLevel) {
        return { allow: false, reason: `${skills} — below level ${cfg.minLevel} threshold` };
      }
      return { allow: true, reason: skills };
    }

    case "KILL_COUNT": {
      const { bossName = "?", count = 0, isPersonalBest = false } = extra;
      if (cfg.personalBestOnly && !isPersonalBest) {
        return { allow: false, reason: `${bossName} kc ${count} — not a PB` };
      }
      if (cfg.milestone > 0 && count % cfg.milestone !== 0) {
        return { allow: false, reason: `${bossName} kc ${count} — not a milestone (every ${cfg.milestone})` };
      }
      return { allow: true, reason: `${bossName} — kc ${count}${isPersonalBest ? " (PB!)" : ""}` };
    }

    case "SLAYER": {
      const { slayerTask = "?", slayerPoints = 0 } = extra;
      if (Number(slayerPoints) < cfg.minPoints) {
        return { allow: false, reason: `${slayerTask} — ${slayerPoints} pts below ${cfg.minPoints} threshold` };
      }
      return { allow: true, reason: `${slayerTask} — ${slayerPoints} pts` };
    }

    case "QUEST": {
      const { questName = "?" } = extra;
      return { allow: true, reason: questName };
    }

    case "COMBAT_ACHIEVEMENT": {
      const { tier = "", task = "" } = extra;
      if (!cfg.allowedTiers.includes(tier)) {
        return { allow: false, reason: `${tier} combat achievement — tier not in allowedTiers` };
      }
      return { allow: true, reason: `${tier} — ${task}` };
    }

    case "ACHIEVEMENT_DIARY": {
      const { area = "?", difficulty = "" } = extra;
      if (!cfg.allowedTiers.includes(difficulty)) {
        return { allow: false, reason: `${difficulty} diary (${area}) — tier not in allowedTiers` };
      }
      return { allow: true, reason: `${difficulty} diary — ${area}` };
    }

    case "SPEEDRUN": {
      const { questName = "?", isPersonalBest = false } = extra;
      if (cfg.personalBestOnly && !isPersonalBest) {
        return { allow: false, reason: `${questName} speedrun — not a PB` };
      }
      return { allow: true, reason: `${questName} speedrun${isPersonalBest ? " (PB!)" : ""}` };
    }

    case "BA_GAMBLE": {
      const items      = extra.items ?? [];
      const totalValue = items.reduce((sum, i) => sum + (i.priceEach ?? 0) * (i.quantity ?? 1), 0);
      if (totalValue < cfg.minValue) {
        return { allow: false, reason: `BA gamble — ${gp(totalValue)} below ${gp(cfg.minValue)} threshold` };
      }
      return { allow: true, reason: `BA gamble — ${gp(totalValue)}` };
    }

    case "GRAND_EXCHANGE":
    case "TRADE":
    case "LOGIN":
    case "CHAT":
      return { allow: cfg.enabled, reason: cfg.enabled ? "enabled" : "disabled in config" };

    default:
      return { allow: true, reason: `unrecognised type "${type}" — forwarding by default` };
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
//  HELPERS
// ═══════════════════════════════════════════════════════════════════════════════

function parsePayload(req) {
  const ct = req.headers["content-type"] || "";
  if (ct.includes("multipart/form-data")) {
    try { return JSON.parse(req.body.payload_json); } catch { return null; }
  }
  return req.body ?? null;
}

async function forwardToDiscord(req, payload) {
  const hasScreenshot = !!req.file;

  if (hasScreenshot) {
    const { FormData, Blob } = await import("node-fetch");
    const form = new FormData();
    form.append("payload_json", JSON.stringify(payload), { contentType: "application/json" });
    form.append(
      "file",
      new Blob([req.file.buffer], { type: req.file.mimetype }),
      req.file.originalname || "screenshot.png"
    );
    await fetch(DISCORD_WEBHOOK_URL, { method: "POST", body: form });
  } else {
    await fetch(DISCORD_WEBHOOK_URL, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify(payload),
    });
  }
}

function gp(value) {
  return `${Number(value).toLocaleString()} gp`;
}
