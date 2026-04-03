# Complete Siri Shortcuts Setup Guide

This is the **complete, step-by-step guide** to create all Siri shortcuts for IIITH Mess management.

---

## Prerequisites ✅

Before you start, make sure:

1. **Pi is set up and running:**
   ```bash
   ssh pi@raspberrypi.local
   ps aux | grep api_wrapper
   ```
   Should show `python3 api_wrapper.py` running

2. **API is running on port 5000:**
   ```bash
   curl http://localhost:5000/api/health
   ```
   Should return: `{"status":"ok","authenticated":true}`

3. **Find your Pi's IP:**
   ```bash
   hostname -I
   ```
   Example: `192.168.1.42` — **you'll use this in shortcuts**

4. **iPhone connected to IIIT VPN**

5. **Shortcuts app installed** on iPhone

---

## Quick Start

**Automatic registration setup (5 minutes, one-time):**
1. Set your meal preferences in `registration_preferences.json` on Pi
2. Create a cron job to auto-register on the 27th of every month
3. Done! You're registered for the entire next month

**Then create 2 Siri shortcuts (5 minutes total):**
1. ✅ "What's for lunch?" (Menu) — Check today's meals
2. ✅ "Cancel my meal" (Cancel) — Skip a meal if needed

Each takes **2-3 minutes** to create.

---

## Shortcut 1: "What's for lunch?" (Menu)

**What it does:** Ask Siri "What's for lunch?" and get today's complete menu for **ALL your registered meals**
- If you registered for breakfast at Yuktahar, lunch at Kadamba-veg, and dinner at Palash, you'll get all three menus
- Shows **ALL menu items** (not just a few) ✅

**Time:** 3 minutes

**Steps:**

1. Open **Shortcuts** app on iPhone
2. Tap **+ (Create new shortcut)**
3. Tap **+ (Add action)**
4. Search for **"URL"** → Tap it
   - Enter: `http://192.168.1.42:5000/api/interact` (replace IP with your Pi's IP)
5. Tap **+ (Add action)** again
6. Search for **"Get contents of URL"** → Tap it
   - **Method:** POST
   - **Headers:** Expand and verify `Content-Type: application/json` is there (if not, add it)
   - **Request Body:** Change to **JSON** and paste:
     ```json
     {
       "action": "menu"
     }
     ```
     (This automatically fetches your registered mess(es) for today - no hardcoding needed!)

7. Tap **+ (Add action)**
8. Search for **"Get Dictionary Value"** → Tap it
   - Tap the blue **dictionary icon**
   - Select **"spoken"**
9. Tap **+ (Add action)**
10. Search for **"Speak Text"** → Tap it

11. **Test it:** Tap play ▶️
    - You should hear: "Breakfast (yuktahar): Idli, Dosa, Sambar, Coconut Chutney. Lunch (kadamba-veg): Rice, Dal, Cabbage, Carrots, Beans. Dinner (palash): Biryani, Raita, Salad."

12. **Add to Siri:**
    - Tap **... (menu)** → **Add to Siri**
    - Tap record 🎤
    - Say: "What's for lunch?"
    - Tap **Done**

**💡 Smart Features:**
- Automatically detects which messes you registered for today
- Shows meals from each of your registered messes
- Displays complete item lists (no truncation!)
- If you're not registered for today, you can add `mess_id: "yuktahar"` to the JSON to see a specific mess's menu

**Now say:** "Hey Siri, what's for lunch?" ✅

---

## Setup: Automatic Monthly Registration via Cron

**What this does:** Auto-registers you for ALL meals for the entire month on the 27th

**Time:** 5 minutes (one-time setup)

**Step 1: Create preferences file on Pi**

SSH into Pi and create `registration_preferences.json`:

```bash
ssh pi@raspberrypi.local
cd ~/iiith-mess-mcp  # or wherever api_wrapper.py is
nano registration_preferences.json
```

Paste your preferences (customize these!):

```json
{
  "breakfast": "yuktahar",
  "lunch": "kadamba-veg",
  "dinner": "palash"
}
```

Save: `Ctrl+O` → Enter → `Ctrl+X`

**Available Mess IDs:**
- `yuktahar`, `yuktahar-jain`
- `palash`, `north`
- `kadamba`, `south`
- `kadamba-veg`, `kadamba-nonveg`
- `kadamba-veg-mild`, `kadamba-nonveg-mild`

**Step 2: Create registration script on Pi**

Create `auto_register.py`:

```bash
nano auto_register.py
```

Paste this:

```python
#!/usr/bin/env python3
"""
Auto-register for entire month based on preferences.
Run on 27th of each month via cron.
"""

import json
import os
from datetime import datetime, timedelta
from iiith_mess_mcp.server import mess_create_registration, CreateRegistrationInput
import asyncio

# Read preferences
with open('registration_preferences.json') as f:
    prefs = json.load(f)

print(f"Auto-registering with preferences: {prefs}")

# Get auth from environment
auth_key = os.getenv('IIITH_MESS_MCP_AUTH_KEY')
if not auth_key:
    print("ERROR: IIITH_MESS_MCP_AUTH_KEY not set")
    exit(1)

auth = {"auth_key": auth_key}

# Register for all days of NEXT month
today = datetime.now()
if today.month == 12:
    target_month = 1
    target_year = today.year + 1
else:
    target_month = today.month + 1
    target_year = today.year

# Get last day of month
import calendar
last_day = calendar.monthrange(target_year, target_month)[1]

print(f"Registering for {target_month}/{target_year} (days 1-{last_day})")

# Register for each day, each meal
async def register_month():
    success_count = 0
    fail_count = 0
    
    for day in range(1, last_day + 1):
        date_str = f"{target_year}-{target_month:02d}-{day:02d}"
        
        for meal_type, mess_id in prefs.items():
            try:
                params = CreateRegistrationInput(
                    meal_date=date_str,
                    meal_type=meal_type,
                    meal_mess=mess_id,
                    **auth
                )
                result = await mess_create_registration(params)
                
                if result.get("error"):
                    print(f"  ✗ {meal_type} on {date_str} at {mess_id}: {result['error']}")
                    fail_count += 1
                else:
                    print(f"  ✓ {meal_type} on {date_str} at {mess_id}")
                    success_count += 1
            except Exception as e:
                print(f"  ✗ {meal_type} on {date_str}: {str(e)}")
                fail_count += 1
    
    print(f"\nRegistration complete: {success_count} success, {fail_count} failed")

asyncio.run(register_month())
```

Save: `Ctrl+O` → Enter → `Ctrl+X`

Make executable:
```bash
chmod +x auto_register.py
```

**Step 3: Set up cron job**

Edit crontab:
```bash
crontab -e
```

Add this line (runs at 10 AM on the 27th of every month):

```
0 10 27 * * cd /home/pi/iiith-mess-mcp && /usr/bin/python3 auto_register.py >> auto_register.log 2>&1
```

Save and exit.

**Step 4: Test it manually**

```bash
python3 auto_register.py
```

You should see:
```
Auto-registering with preferences: {'breakfast': 'yuktahar', ...}
Registering for 5/2026 (days 1-31)
  ✓ breakfast on 2026-05-01 at yuktahar
  ✓ lunch on 2026-05-01 at kadamba-veg
  ✓ dinner on 2026-05-01 at palash
  ✓ breakfast on 2026-05-02 at yuktahar
  ...
Registration complete: 93 success, 0 failed
```

✅ Done! Cron will auto-register you on the 27th of every month.

---

## Shortcut 2: "Cancel my meal" (Cancel registration)

**What it does:** Ask "Cancel my meal" and it asks for date/meal, then cancels

**Time:** 3 minutes

**Important:** Cancellation must be at least **2 days before** the meal date!
(Today is April 3, so you can only cancel meals on April 5 or later)

**Steps:**

1. Create **new shortcut**
2. Tap **+** → **Ask for Text**
   - Prompt: `Date? (YYYY-MM-DD, minimum 2 days from now)`
   - Save as: `date`

3. Tap **+** → **Ask for Text**
   - Prompt: `Meal? (breakfast/lunch/snacks/dinner)`
   - Save as: `meal`

4. Tap **+** → **URL**: `http://192.168.1.42:5000/api/interact`

5. Tap **+** → **Get contents of URL**
   - **Method:** POST
   - **Headers:** `Content-Type: application/json`
   - **Request Body (JSON):**
     ```json
     {
       "action": "cancel",
       "date": "[date]",
       "meal_type": "[meal]"
     }
     ```

6. Tap **+** → **Get Dictionary Value** → Select **"spoken"**
7. Tap **+** → **Speak Text**

8. **Test:** Tap play ▶️
   - It asks: "Date?"
   - You type: "2026-04-05" (at least 2 days away)
   - It asks: "Meal?"
   - You type: "lunch"
   - Hear: "Cancelled lunch on April 5, 2026"

9. **Add to Siri:** "Cancel my meal"

**Now say:** "Hey Siri, cancel my meal" ✅

---

## Quick Reference: Your Siri Commands

```
"Hey Siri, what's for lunch?" → Shows today's menu

"Hey Siri, cancel my meal" → Cancel a registered meal
```

✅ **Auto-registration:** Cron job handles monthly registration on the 27th

No need to say "register me" anymore!

---

## Troubleshooting

### ❌ "Registration is only allowed a minimum of 2 days before the meal date"

**Fix:**
- Only register for dates that are **at least 2 days in the future**
- Today is April 3, so earliest registration is April 5
- Try again with a date like "2026-04-05" or later

### ❌ "Cancellation/Uncancellation is only allowed a minimum of 2 days before the meal date"

**Fix:**
- Only cancel meals that are **at least 2 days in the future**
- You cannot cancel meals that are tomorrow or day-after-tomorrow
- Try cancelling a meal that's further away

### ❌ Shortcut says "Connection refused"

**Fix:**
1. Verify Pi is running:
   ```bash
   ssh pi@raspberrypi.local
   ps aux | grep api_wrapper
   ```
2. Verify correct IP in shortcut (use `hostname -I` on Pi)
3. Make sure iPhone is on IIIT VPN

### ❌ Shortcut says "The operation couldn't be completed"

**Fix:**
1. Check the **Headers** section — must have `Content-Type: application/json`
2. Check **Request Body** — must be set to **JSON** (not Text/Form)
3. Verify JSON syntax is correct (no missing commas/brackets)

### ❌ Shortcut returns "Action not specified"

**Fix:**
1. Make sure **Request Body** has JSON content
2. Verify `"action"` field is spelled correctly
3. Check that JSON is valid (use online JSON validator)

### ❌ Shortcut says "speak text is empty"

**Fix:**
1. The API returned no `"spoken"` field
2. Check if `"Get Dictionary Value"` is correctly set to **"spoken"**
3. Check the `success` field in the response to debug

### ❌ Shortcut says "Mess [name] not found"

**Fix:**
1. Use the correct mess_id (check Mess ID Reference table above)
2. Say "What messes are available?" in Shortcut 5 to see valid mess IDs
3. Mess IDs are case-sensitive and use lowercase with dashes (e.g., `kadamba-veg`, not `Kadamba-Veg` or `kadamba_veg`)

### ❌ iPhone volume is muted

**Fix:**
1. On iPhone, toggle the **mute switch** on the side (near volume buttons)
2. Make sure volume is turned up
3. Try **Speak Text** action with a static text first to verify it works

---

## API Responses Reference

**Shortcuts use these API actions:**

```
"action": "menu"
→ "spoken": "Breakfast (yuktahar): Kanchipuram Idli, Sambar, Coconut Chutney. Lunch (kadamba-veg): Veg Poolao, Gongura Dal, Cabbage. Dinner (palash): Wheat Roti, Black Chick Peas, Banana Curry."

"action": "cancel"
→ "spoken": "Cancelled lunch on April 5, 2026"
(on success; on error: "Failed to cancel: Cancellation is only allowed a minimum of 2 days before the meal date.")
```

**Registrations are automatic via `auto_register.py` cron job — no manual registration needed!**

---

## Testing Checklist

- [ ] Pi is running and API responds to health check
- [ ] iPhone can reach Pi's IP on local network
- [ ] iPhone is on IIIT VPN
- [ ] Created `registration_preferences.json` on Pi
- [ ] Created `auto_register.py` on Pi
- [ ] Ran `python3 auto_register.py` manually and verified registrations
- [ ] Added cron job to crontab
- [ ] Created Shortcut 1 (Menu) and tested
- [ ] Created Shortcut 2 (Cancel) and tested
- [ ] Both shortcuts added to Siri
- [ ] Voice commands work naturally

---

## Pro Tips 💡

**1. Name shortcuts clearly**
- Instead of "Shortcut 1", name them "Menu", "Meals", etc.

**2. Test plain shortcuts first**
- Get Shortcut 2 (registrations) working before trying Shortcut 3 (register)
- Plain JSON is easier than variables

**3. Use the Alert action for debugging**
- Add `Show Result` action before `Speak Text` to see what the API returned

**4. Keep your mess names handy**
- See Shortcut 5 list above (or say "What messes are available?")
- Use the **mess_id** (e.g., `kadamba-veg`, not `Kadamba (V)`)

**5. Important date restrictions** ⚠️
- **Registration**: Must be **at least 2 days** before meal date
- **Cancellation**: Must be **at least 2 days** before meal date
- If date is too close, API will return: "Only allowed a minimum of 2 days before the meal date"

**6. Date format is strict**
- Always use YYYY-MM-DD format (2026-04-05, not 4/5/2026)

**7. Mess ID vs Mess Name**
- For shortcuts: Use **mess_id** (e.g., `yuktahar`, `kadamba-veg`)
- Siri will speak back the **display name** (e.g., `Yuktāhār`, `Kadamba (Veg)`)

---

## Mess ID Reference

Use these IDs in Shortcut 3 (Register) and Shortcut 4 (Cancel):

| Mess ID | Display Name |
|---------|------------|
| `yuktahar` | Yuktāhār |
| `yuktahar-jain` | Yuktāhār (Jain) |
| `palash` | Palāsh |
| `north` | North |
| `kadamba` | Kadamba |
| `south` | South |
| `kadamba-veg` | Kadamba (Veg) |
| `kadamba-nonveg` | Kadamba (Non-Veg) |
| `kadamba-veg-mild` | Kadamba (Veg with Mild Spice) |
| `kadamba-nonveg-mild` | Kadamba (Non Veg with Mild Spice) |

---

## Next Steps

1. ✅ Ensure Pi API is running on port 5000
2. ✅ Create all 5 shortcuts (total ~15 minutes)
3. ✅ Test each one by tapping play ▶️
4. ✅ Add each to Siri
5. ✅ Test voice commands naturally

**Enjoy voice-controlled meal registration!** 🎙️

---

## Questions?

**Test endpoint directly:**
```bash
curl -X POST http://192.168.1.42:5000/api/interact \
  -H "Content-Type: application/json" \
  -d '{"action":"messes"}'
```

**Check Pi logs:**
```bash
ssh pi@raspberrypi.local
# Then look for Flask output showing requests
```

**Check .env is set correctly:**
```bash
ssh pi@raspberrypi.local
cat .env
```
