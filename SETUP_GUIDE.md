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
| **Pet** | Always forwarded — no filter |
| **Loot** | Total drop value threshold (default: 500k gp) |
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

## Step 1 — Get a server

You need somewhere to host this. A few easy options:

### Option A: Railway (recommended, free tier available)
1. Go to [railway.app](https://railway.app) and sign up
2. Push the project files to a GitHub repository
3. Click **New Project → Deploy from GitHub repo** and connect it
4. Railway auto-detects Node.js and runs `npm start`
5. Go to your project **Settings → Variables** and add `DISCORD_WEBHOOK_URL`
6. Railway gives you a public `https://` URL automatically

### Option B: Fly.io (free tier)
1. Install the Fly CLI: https://fly.io/docs/hands-on/install-flyctl/
2. Run `fly launch` inside the project folder and follow the prompts
3. Set your env var: `fly secrets set DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."`
4. Deploy: `fly deploy`

### Option C: Any VPS (DigitalOcean, Hetzner, etc.)
```bash
# Install Node.js
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Clone/upload your project files, then:
npm install

# Install PM2 to keep the server running after logout
npm install -g pm2
DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..." pm2 start server.js
pm2 save
pm2 startup

# Open the port in your firewall (if using ufw)
sudo ufw allow 3000
```

---

## Step 2 — Get your Discord webhook URL

1. Open Discord → go to the channel you want notifications in
2. Click the **gear icon** (Edit Channel) → **Integrations** → **Webhooks**
3. Click **New Webhook**, give it a name (e.g. "OSRS Drops")
4. Click **Copy Webhook URL**
5. Set this as the `DISCORD_WEBHOOK_URL` environment variable on your server — **never put it directly in the code**

---

## Step 3 — Run locally first (optional but recommended)

```bash
# Install dependencies
npm install

# Set your webhook URL and start
DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/YOUR_ID/YOUR_TOKEN" npm start
```

You should see output like:
```
Dink filter listening on port 3000
Config summary:
  COLLECTION             enabled=true
  PET                    enabled=true
  LOOT                   enabled=true
  ...
```

---

## Step 4 — Configure Dink in RuneLite

Each player does this once:

1. Open RuneLite → **Plugin Hub** → search **Dink** → install
2. Open Dink settings (the wrench icon next to the plugin)
3. Under **Primary Webhook URLs**, enter your server's URL:
   ```
   https://your-app-name.railway.app/webhook
   ```
   or if self-hosting:
   ```
   http://YOUR-SERVER-IP:3000/webhook
   ```
4. Enable whichever notifiers you want in Dink (Collection, Pet, Loot, etc.)
5. **Important:** disable any value filtering inside Dink itself — let your server handle it, otherwise Dink may silently drop things before they even reach you

> Players point Dink at **your server**, not at Discord. Your server decides what reaches Discord.

---

## Step 5 — Customise the filters

All configuration is at the top of `server.js` in the `CONFIG` block. The comments explain each option. Examples:

### Only notify on 99s AND 200M milestones
```js
LEVEL: {
  enabled:  true,
  minLevel: 99,
},
```
For 200M you'd need to also enable XP milestones in Dink and handle the `XP_MILESTONE` type separately.

### Only Hard/Elite/Master clues worth 1M+
```js
CLUE: {
  enabled:    true,
  minValue:   1_000_000,
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

### Kill count every 100 kills OR personal bests
```js
KILL_COUNT: {
  enabled:          true,
  personalBestOnly: false,
  milestone:        100,
},
```

---

## Step 6 — Test it

### Check the server is alive
```bash
curl https://your-server-url/health
# Returns: OK
```

### Simulate a collection log drop (above threshold — should forward)
```bash
curl -X POST https://your-server-url/webhook \
  -H "Content-Type: application/json" \
  -d '{"type":"COLLECTION","playerName":"TestIron","extra":{"itemName":"Abyssal whip","itemId":4151,"price":2500000,"completedEntries":100,"totalEntries":1443}}'
```

### Simulate a cheap drop (below threshold — should be skipped)
```bash
curl -X POST https://your-server-url/webhook \
  -H "Content-Type: application/json" \
  -d '{"type":"COLLECTION","playerName":"TestIron","extra":{"itemName":"Bronze arrow","itemId":882,"price":3,"completedEntries":101,"totalEntries":1443}}'
```

### Simulate a pet (always forwards)
```bash
curl -X POST https://your-server-url/webhook \
  -H "Content-Type: application/json" \
  -d '{"type":"PET","playerName":"TestIron","extra":{"petName":"Ikkle hydra","duplicate":false}}'
```

### Simulate a level up (99 Slayer)
```bash
curl -X POST https://your-server-url/webhook \
  -H "Content-Type: application/json" \
  -d '{"type":"LEVEL","playerName":"TestIron","extra":{"levelledSkills":{"Slayer":99},"allSkills":{"Slayer":99}}}'
```

Check your server's console output — every request logs `[ALLOW]` or `[SKIP]` with the reason.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Nothing appearing in Discord | Check `DISCORD_WEBHOOK_URL` is set correctly; check server console for errors |
| Server not receiving from Dink | Check the URL in Dink settings matches your server exactly including `/webhook` |
| Items above threshold not forwarding | Make sure Dink's own value filter isn't also filtering them out — set Dink's min value to 0 or 1 |
| Pets not appearing | Confirm Pet notifier is enabled in Dink settings and `PET.enabled: true` in config |
| Screenshots not forwarding | Enable "Send Screenshot" per-notifier in Dink settings |
| Server crashes on start | Make sure `DISCORD_WEBHOOK_URL` env var is set before starting |
