# Dink Webhook Filter — Setup Guide

A Node.js server that sits between your clan members' RuneLite (Dink plugin) and your Discord channel. All filtering is centralised on your server — players just point Dink at your URL, no per-player config needed.

```
RuneLite (Dink)  →  Your filter server  →  Discord
```

---

## What's handled

| Type | Filter |
|---|---|
| **Collection Log** | GE value threshold (default: 1M gp) |
| **Pet** | Always forwarded — duplicates skipped by default |
| **Loot** | Total drop value threshold (default: 25M gp) |
| **Clue Scroll** | Tier allowlist + total reward value threshold |
| **Death** | PvP-only toggle + minimum GP lost |
| **Level** | Minimum level threshold (default: 99 only) |
| **Kill Count** | Personal best only toggle + milestone intervals |
| **Slayer** | Minimum points threshold |
| **Quest** | Always forwarded when enabled |
| **Combat Achievement** | Tier allowlist |
| **Achievement Diary** | Tier allowlist |
| **Speedrun** | Personal best only toggle |
| **BA Gamble** | Total reward value threshold |
| **Grand Exchange** | On/off (default: off) |
| **Trade** | On/off (default: off) |

---

## Step 1 — Deploy to Railway

1. Push the project files to a GitHub repository
2. Go to [railway.app](https://railway.app), sign up, and click **New Project → Deploy from GitHub repo**
3. Connect your repository — Railway auto-detects Node.js and runs `npm start`
4. Go to your project **Settings → Variables** and add the environment variables below
5. Railway gives you a public `https://` URL automatically under **Settings → Networking → Generate Domain**

### Environment variables

| Variable | Required | Description |
|---|---|---|
| `DISCORD_WEBHOOK_URL` | **Yes** | The Discord webhook URL to forward events to |
| `CLAN_NAME` | No | If set, only events from players in this exact clan are forwarded. Leave unset to allow everyone. |

> **`CLAN_NAME` must match exactly** what appears in-game as your clan name (e.g. `Duck Trumps`). The check is case-insensitive, so capitalisation doesn't matter.

---

## Step 2 — Get your Discord webhook URL

1. Open Discord → go to the channel you want notifications in
2. Click the **gear icon** (Edit Channel) → **Integrations** → **Webhooks**
3. Click **New Webhook**, give it a name (e.g. "OSRS Drops")
4. Click **Copy Webhook URL**
5. Paste it as the `DISCORD_WEBHOOK_URL` variable in Railway — **never put it directly in the code**

---

## Step 3 — Configure Dink in RuneLite

Each player does this once:

1. Open RuneLite → **Plugin Hub** → search **Dink** → install
2. Open Dink settings (the wrench icon next to the plugin)
3. Under **Primary Webhook URLs**, enter your Railway server URL:
   ```
   https://your-app-name.railway.app/webhook
   ```
4. Enable whichever notifiers you want in Dink (Collection, Pet, Loot, etc.)
5. **Important:** disable any value filtering inside Dink itself — let your server handle it, otherwise Dink may silently drop events before they even reach you

> Players point Dink at **your server**, not at Discord. Your server decides what reaches Discord.

---

## Step 4 — Customise the filters

All configuration is at the top of `server.js` in the `CONFIG` block. Edit the values and push to GitHub — Railway will redeploy automatically.

### Only notify on 99s
```js
LEVEL: {
  enabled:  true,
  minLevel: 99,
},
```

### Only Hard/Elite/Master clues worth 1M+
```js
CLUE: {
  enabled:      true,
  minValue:     1_000_000,
  allowedTiers: ["Hard", "Elite", "Master"],
},
```

### PvP deaths only
```js
DEATH: {
  enabled:      true,
  pvpOnly:      true,
  minValueLost: 0,
},
```

### Kill count every 100 kills, or on personal bests
```js
KILL_COUNT: {
  enabled:          true,
  personalBestOnly: false,
  milestone:        100,
},
```

---

## Step 5 — Test it

### Check the server is alive
```bash
curl https://your-app-name.railway.app/health
# Returns: OK
```

### Simulate a collection log drop (above threshold — should forward)
```bash
curl -X POST https://your-app-name.railway.app/webhook \
  -H "Content-Type: application/json" \
  -d '{"type":"COLLECTION","playerName":"TestIron","clanName":"Duck Trumps","extra":{"itemName":"Abyssal whip","itemId":4151,"price":2500000,"completedEntries":100,"totalEntries":1443}}'
```

### Simulate a cheap drop (below threshold — should be skipped)
```bash
curl -X POST https://your-app-name.railway.app/webhook \
  -H "Content-Type: application/json" \
  -d '{"type":"COLLECTION","playerName":"TestIron","clanName":"Duck Trumps","extra":{"itemName":"Bronze arrow","itemId":882,"price":3,"completedEntries":101,"totalEntries":1443}}'
```

### Simulate a player from a different clan (should be skipped if CLAN_NAME is set)
```bash
curl -X POST https://your-app-name.railway.app/webhook \
  -H "Content-Type: application/json" \
  -d '{"type":"PET","playerName":"SomeRando","clanName":"Other Clan","extra":{"petName":"Ikkle hydra","duplicate":false}}'
```

### Simulate a pet (always forwards if clan matches)
```bash
curl -X POST https://your-app-name.railway.app/webhook \
  -H "Content-Type: application/json" \
  -d '{"type":"PET","playerName":"TestIron","clanName":"Duck Trumps","extra":{"petName":"Ikkle hydra","duplicate":false}}'
```

### Simulate a level up (99 Slayer)
```bash
curl -X POST https://your-app-name.railway.app/webhook \
  -H "Content-Type: application/json" \
  -d '{"type":"LEVEL","playerName":"TestIron","clanName":"Duck Trumps","extra":{"levelledSkills":{"Slayer":99},"allSkills":{"Slayer":99}}}'
```

Check Railway's **Deployments → View Logs** — every request logs `[ALLOW]` or `[SKIP]` with the reason.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Nothing appearing in Discord | Check `DISCORD_WEBHOOK_URL` is set correctly in Railway variables; check logs for errors |
| Events being skipped with "player not in clan" | Check `CLAN_NAME` in Railway matches your exact in-game clan name |
| Server not receiving from Dink | Check the URL in Dink settings matches your Railway URL exactly, including `/webhook` |
| Items above threshold not forwarding | Make sure Dink's own value filter isn't also filtering — set Dink's min value to 0 or 1 |
| Pets not appearing | Confirm Pet notifier is enabled in Dink and `PET.enabled: true` in config |
| Duplicate pets being skipped | Set `PET.duplicates: true` in config |
| Screenshots not forwarding | Enable "Send Screenshot" per-notifier in Dink settings |
| Server crashes on start | Make sure `DISCORD_WEBHOOK_URL` is set in Railway variables before deploying |
