const express = require("express");
const multer  = require("multer");

const app    = express();
const upload = multer();

// ═══════════════════════════════════════════════════════════════════════════════
//  CONFIG — edit everything in this block to suit your clan
// ═══════════════════════════════════════════════════════════════════════════════

const DISCORD_WEBHOOK_URL = process.env.DISCORD_WEBHOOK_URL;
const PORT = process.env.PORT || 3000;

const CONFIG = {

  COLLECTION: {
    enabled:        true,
    minValue:       1_000_000,
    sendScreenshot: true,
  },

  PET: {
    enabled:        true,
    duplicates:     false,
    sendScreenshot: true,
  },

  LOOT: {
    enabled:        true,
    minValue:       25_000_000,
    sendScreenshot: true,
  },

  CLUE: {
    enabled:        false,
    minValue:       250_000,
    allowedTiers:   ["Hard", "Elite", "Master"],
    sendScreenshot: false,
  },

  DEATH: {
    enabled:        false,
    pvpOnly:        false,
    minValueLost:   0,
    sendScreenshot: false,
  },

  LEVEL: {
    enabled:        false,
    minLevel:       99,
    sendScreenshot: false,
  },

  KILL_COUNT: {
    enabled:          false,
    personalBestOnly: false,
    milestone:        0,
    sendScreenshot:   false,
  },

  SLAYER: {
    enabled:        false,
    minPoints:      0,
    sendScreenshot: false,
  },

  QUEST: {
    enabled:        false,
    sendScreenshot: false,
  },

  COMBAT_ACHIEVEMENT: {
    enabled:        false,
    allowedTiers:   ["Hard", "Elite", "Master", "Grandmaster"],
    sendScreenshot: false,
  },

  ACHIEVEMENT_DIARY: {
    enabled:        false,
    allowedTiers:   ["Hard", "Elite"],
    sendScreenshot: false,
  },

  SPEEDRUN: {
    enabled:          false,
    personalBestOnly: false,
    sendScreenshot:   false,
  },

  BA_GAMBLE: {
    enabled:        false,
    minValue:       0,
    sendScreenshot: false,
  },

  GRAND_EXCHANGE: {
    enabled:        false,
    sendScreenshot: false,
  },

  TRADE: {
    enabled:        false,
    sendScreenshot: false,
  },

  LOGIN: {
    enabled:        false,
    sendScreenshot: false,
  },

  CHAT: {
    enabled:        false,
    sendScreenshot: false,
  },

};

// ═══════════════════════════════════════════════════════════════════════════════
//  END CONFIG
// ═══════════════════════════════════════════════════════════════════════════════

if (!DISCORD_WEBHOOK_URL) {
  console.error("ERROR: DISCORD_WEBHOOK_URL environment variable is not set.");
  process.exit(1);
}

app.use(express.json()); // handles application/json
app.use(upload.single("file")); // handles multipart/form-data


// Webhook endpoint
app.post("/webhook", async (req, res) => {
  try {
    const parsed = parsePayload(req);
    if (!parsed) return res.status(400).send("Invalid payload");

    const { type, extra = {} } = parsed;
    const cfg                  = CONFIG[type];
    const { allow, reason }    = shouldForward(type, extra, cfg);

    console.log(`${allow ? "[ALLOW]" : "[SKIP]"} ${type} — ${reason}`);

    if (allow) {
      const ct = req.headers["content-type"] || "";
      if (ct.includes("multipart/form-data")) {
        console.log("Forwarding multipart payload to Discord:", req.body.payload_json);
        await forwardToDiscord(req, req.body.payload_json, cfg?.sendScreenshot ?? false);
      } else {
        console.log("Forwarding JSON payload to Discord:", req.body);
        await forwardToDiscord(req, JSON.stringify(req.body), cfg?.sendScreenshot ?? false);
      }
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
  console.log(`Active notifiers: ${Object.entries(CONFIG).filter(([,c]) => c.enabled).map(([t]) => t).join(", ")}`);
});

// ═══════════════════════════════════════════════════════════════════════════════
//  HANDLERS
// ═══════════════════════════════════════════════════════════════════════════════

function shouldForward(type, extra, cfg) {
  if (!cfg)          return { allow: true,  reason: `unknown type "${type}" — forwarding by default` };
  if (!cfg.enabled)  return { allow: false, reason: "type disabled in config" };

  switch (type) {

    case "COLLECTION": {
      const { itemName = "?", price = 0 } = extra;
      if (price < cfg.minValue)
        return { allow: false, reason: `${itemName} — ${gp(price)} below ${gp(cfg.minValue)} threshold` };
      return { allow: true, reason: `${itemName} — ${gp(price)}` };
    }

    case "PET": {
      const { petName = "unknown pet", duplicate = false } = extra;
      if (duplicate && !cfg.duplicates)
        return { allow: false, reason: `${petName} — duplicate pet, duplicates disabled` };
      return { allow: true, reason: `${petName}${duplicate ? " (duplicate)" : ""}` };
    }

    case "LOOT": {
      const items      = extra.items ?? [];
      const totalValue = items.reduce((sum, i) => sum + (i.priceEach ?? 0) * (i.quantity ?? 1), 0);
      const source     = extra.source ?? "unknown";
      if (totalValue < cfg.minValue)
        return { allow: false, reason: `${source} — ${gp(totalValue)} below ${gp(cfg.minValue)} threshold` };
      return { allow: true, reason: `${source} — ${gp(totalValue)}` };
    }

    case "CLUE": {
      const { clueType = "", numberCompleted = 0, items = [] } = extra;
      const totalValue = items.reduce((sum, i) => sum + (i.priceEach ?? 0) * (i.quantity ?? 1), 0);
      if (!cfg.allowedTiers.includes(clueType))
        return { allow: false, reason: `${clueType} clue — tier not in allowedTiers` };
      if (totalValue < cfg.minValue)
        return { allow: false, reason: `${clueType} clue #${numberCompleted} — ${gp(totalValue)} below ${gp(cfg.minValue)} threshold` };
      return { allow: true, reason: `${clueType} clue #${numberCompleted} — ${gp(totalValue)}` };
    }

    case "DEATH": {
      const { valueLost = 0, isPvp = false } = extra;
      if (cfg.pvpOnly && !isPvp)
        return { allow: false, reason: "non-PvP death — pvpOnly is enabled" };
      if (valueLost < cfg.minValueLost)
        return { allow: false, reason: `death — ${gp(valueLost)} lost, below ${gp(cfg.minValueLost)} threshold` };
      return { allow: true, reason: `${isPvp ? "PvP" : "PvE"} death — ${gp(valueLost)} lost` };
    }

    case "LEVEL": {
      const levelledSkills = extra.levelledSkills ?? {};
      const highestLevel   = Math.max(...Object.values(levelledSkills), 0);
      const skills         = Object.entries(levelledSkills).map(([s, l]) => `${s} ${l}`).join(", ");
      if (highestLevel < cfg.minLevel)
        return { allow: false, reason: `${skills} — below level ${cfg.minLevel} threshold` };
      return { allow: true, reason: skills };
    }

    case "KILL_COUNT": {
      const { bossName = "?", count = 0, isPersonalBest = false } = extra;
      if (cfg.personalBestOnly && !isPersonalBest)
        return { allow: false, reason: `${bossName} kc ${count} — not a PB` };
      if (cfg.milestone > 0 && count % cfg.milestone !== 0)
        return { allow: false, reason: `${bossName} kc ${count} — not a milestone (every ${cfg.milestone})` };
      return { allow: true, reason: `${bossName} — kc ${count}${isPersonalBest ? " (PB!)" : ""}` };
    }

    case "SLAYER": {
      const { slayerTask = "?", slayerPoints = 0 } = extra;
      if (Number(slayerPoints) < cfg.minPoints)
        return { allow: false, reason: `${slayerTask} — ${slayerPoints} pts below ${cfg.minPoints} threshold` };
      return { allow: true, reason: `${slayerTask} — ${slayerPoints} pts` };
    }

    case "QUEST": {
      const { questName = "?" } = extra;
      return { allow: true, reason: questName };
    }

    case "COMBAT_ACHIEVEMENT": {
      const { tier = "", task = "" } = extra;
      if (!cfg.allowedTiers.includes(tier))
        return { allow: false, reason: `${tier} combat achievement — tier not in allowedTiers` };
      return { allow: true, reason: `${tier} — ${task}` };
    }

    case "ACHIEVEMENT_DIARY": {
      const { area = "?", difficulty = "" } = extra;
      if (!cfg.allowedTiers.includes(difficulty))
        return { allow: false, reason: `${difficulty} diary (${area}) — tier not in allowedTiers` };
      return { allow: true, reason: `${difficulty} diary — ${area}` };
    }

    case "SPEEDRUN": {
      const { questName = "?", isPersonalBest = false } = extra;
      if (cfg.personalBestOnly && !isPersonalBest)
        return { allow: false, reason: `${questName} speedrun — not a PB` };
      return { allow: true, reason: `${questName} speedrun${isPersonalBest ? " (PB!)" : ""}` };
    }

    case "BA_GAMBLE": {
      const items      = extra.items ?? [];
      const totalValue = items.reduce((sum, i) => sum + (i.priceEach ?? 0) * (i.quantity ?? 1), 0);
      if (totalValue < cfg.minValue)
        return { allow: false, reason: `BA gamble — ${gp(totalValue)} below ${gp(cfg.minValue)} threshold` };
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

async function forwardToDiscord(req, payloadJson, sendScreenshot = false) {
  const hasScreenshot = !!req.file && sendScreenshot;

  if (hasScreenshot) {
    const { FormData, Blob } = await import("node-fetch");
    const form = new FormData();
    form.append("payload_json", payloadJson, { contentType: "application/json" });
    form.append(
      "file",
      new Blob([req.file.buffer], { type: req.file.mimetype }),
      req.file.originalname || "screenshot.png"
    );
    await fetch(DISCORD_WEBHOOK_URL, { method: "POST", body: form });
  } else {
    await fetch(DISCORD_WEBHOOK_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: payloadJson // untouched JSON string
    });
  }
}


function gp(value) {
  return `${Number(value).toLocaleString()} gp`;
}
