# IIITH Mess + Siri Integration 🎙️

Voice-controlled meal management for IIIT Hyderabad mess system. Ask Siri what's for lunch, and it tells you. Cancel meals with a voice command.

**Key Features:**
- 🎙️ **Voice-controlled** - Ask Siri "What's for lunch?" 
- 📅 **Auto-registration** - Cron job registers you for the entire month automatically
- 🍽️ **Smart menus** - Shows meals for all your registered messes
- 📱 **iPhone-native** - No app installation needed, uses built-in Shortcuts app
- 🔒 **Secure** - Runs on your Raspberry Pi, not in the cloud

---

## Quick Start (5 minutes)

### Prerequisites
- Raspberry Pi running on IIIT VPN
- iPhone on IIIT VPN
- IIIT auth credentials

### 1. Setup on Pi

```bash
# Clone repo
git clone https://github.com/yourusername/IIITH-Mess-MCP-with-Siri-.git
cd IIITH-Mess-MCP-with-Siri-

# Create env file
echo "IIITH_MESS_MCP_AUTH_KEY=your-auth-key-here" > .env
echo "MESS_AUTH_KEY=your-auth-key-here" >> .env

# Install dependencies
pip install -r requirements.txt

# Setup auto-registration
nano registration_preferences.json
# Edit to your preferences:
# {
#   "breakfast": "yuktahar",
#   "lunch": "kadamba-veg",
#   "dinner": "palash"
# }

# Add cron job (runs 27th of each month)
crontab -e
# Add: 0 10 27 * * cd ~/iiith-mess-mcp && /usr/bin/python3 auto_register.py >> auto_register.log 2>&1
```

### 2. Create Siri Shortcuts (2 minutes)

Follow [SIRI_SHORTCUTS_GUIDE.md](SIRI_SHORTCUTS_GUIDE.md) to create:
1. **"What's for lunch?"** - Shows today's meals
2. **"Cancel my meal"** - Cancel a registration

### 3. Use It!

```
"Hey Siri, what's for lunch?"
→ "Breakfast (yuktahar): Idli, Dosa, Sambar. 
   Lunch (kadamba-veg): Rice, Dal, Cabbage. 
   Dinner (palash): Biryani, Raita."

"Hey Siri, cancel my meal"
→ (asks for date and meal type, then cancels)
```

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│         iPhone (Siri Shortcuts)                 │
│  "What's for lunch?" → Cancel my meal           │
└────────────────┬────────────────────────────────┘
                 │ HTTP POST
                 ↓
┌─────────────────────────────────────────────────┐
│    Raspberry Pi (Flask API Server)              │
│    - /api/interact (menu, cancel)               │
│    - /api/menus (get menus)                     │
│    - /api/meal/cancel (cancel registration)    │
└────────────────┬────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────┐
│  IIITH Mess MCP Server (on VPN)                 │
│  - mess_get_menus()                             │
│  - mess_get_registrations()                     │
│  - mess_create_registration() (via cron)        │
│  - mess_cancel_registration()                   │
└─────────────────────────────────────────────────┘
```

**Auto-Registration Flow (Monthly):**
```
27th of month, 10:00 AM
    ↓
Cron runs auto_register.py
    ↓
Reads registration_preferences.json
    ↓
Registers for ALL days of next month
    ↓
Each meal at your preferred mess
```

---

## Files

| File | Purpose |
|------|---------|
| `api_wrapper.py` | Flask API server (runs on Pi) |
| `auto_register.py` | Monthly auto-registration script (cron job) |
| `registration_preferences.json` | Your meal preferences config |
| `SIRI_SHORTCUTS_GUIDE.md` | Step-by-step shortcut setup |
| `iiith_mess_mcp/` | MCP server implementation |

---

## Configuration

### Meal Preferences
Edit `registration_preferences.json`:
```json
{
  "breakfast": "yuktahar",
  "lunch": "kadamba-veg", 
  "dinner": "palash"
}
```

**Available Mess IDs:**
- `yuktahar`, `yuktahar-jain`
- `palash`, `north`
- `kadamba`, `south`
- `kadamba-veg`, `kadamba-nonveg`
- `kadamba-veg-mild`, `kadamba-nonveg-mild`

### Enable Current Month Registration (Testing)
Edit `auto_register.py`, set at the top:
```python
REGISTER_CURRENT_MONTH = 1  # 1 = current month, 0 = next month
```

---

## Troubleshooting

### Shortcut says "Connection refused"
- Verify Pi is running: `ssh pi@raspberrypi.local`
- Check Flask is running: `ps aux | grep api_wrapper`
- Verify correct IP in shortcut (use `hostname -I` on Pi)

### "Registration is only allowed a minimum of 2 days before"
- Can only register/cancel for dates at least 2 days in the future
- Cron automatically handles this by running on the 27th

### Shortcut returns empty
- Check Pi auth key in `.env`: `echo $IIITH_MESS_MCP_AUTH_KEY`
- Verify menu data: `curl http://localhost:5000/api/interact -H "Content-Type: application/json" -d '{"action":"menu"}'`

### Manual registration test
```bash
# On Pi
register_current_month=1 python3 auto_register.py
```

---

## API Endpoints

### `/api/interact` (POST)
Unified endpoint for Siri commands

**Menu:**
```bash
curl -X POST http://localhost:5000/api/interact \
  -H "Content-Type: application/json" \
  -d '{"action": "menu"}'
```

**Cancel meal:**
```bash
curl -X POST http://localhost:5000/api/interact \
  -H "Content-Type: application/json" \
  -d '{"action": "cancel", "date": "2026-04-10", "meal_type": "lunch"}'
```

---

## Requirements

- Python 3.8+
- Raspberry Pi (or any Linux machine on IIIT VPN)
- iPhone with Shortcuts app
- IIIT auth key

---

## Setup Details

See [SIRI_SHORTCUTS_GUIDE.md](SIRI_SHORTCUTS_GUIDE.md) for:
- Detailed Siri Shortcut creation
- Troubleshooting guide
- Advanced customization

---

## License

See [LICENSE](LICENSE)

---

## Contributing

Pull requests welcome! For major changes, please open an issue first.

---

**Made for IIIT Hyderabad Students** 🎓
