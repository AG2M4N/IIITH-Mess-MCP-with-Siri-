#!/usr/bin/env python3

"""
Auto-register for entire month based on preferences.
Run on 27th of each month via cron job.

Usage:
    python3 auto_register.py          # Normal: register for NEXT month
    python3 auto_register.py          # With REGISTER_CURRENT_MONTH=1: register for CURRENT month

This will register for all days of the month using preferences from:
    registration_preferences.json
"""

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
# Set to 1 to register for CURRENT month, 0 to register for NEXT month
REGISTER_CURRENT_MONTH = 0

import json
import os
import sys
from datetime import datetime
import calendar
import asyncio

# Load environment variables from .env
from dotenv import load_dotenv
load_dotenv()

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from iiith_mess_mcp.server import mess_create_registration, CreateRegistrationInput


def load_preferences():
    """Load meal preferences from JSON file"""
    try:
        with open('registration_preferences.json') as f:
            prefs = json.load(f)
        print(f"✓ Loaded preferences: {prefs}")
        return prefs
    except FileNotFoundError:
        print("✗ ERROR: registration_preferences.json not found")
        print("  Create it with: {\"breakfast\": \"yuktahar\", \"lunch\": \"kadamba-veg\", \"dinner\": \"palash\"}")
        sys.exit(1)
    except json.JSONDecodeError:
        print("✗ ERROR: registration_preferences.json has invalid JSON")
        sys.exit(1)


def get_auth():
    """Get auth key from environment"""
    auth_key = os.getenv('IIITH_MESS_MCP_AUTH_KEY')
    if not auth_key:
        print("✗ ERROR: IIITH_MESS_MCP_AUTH_KEY not set in environment")
        print("  Set it in .env file")
        sys.exit(1)
    return {"auth_key": auth_key}


def get_next_month():
    """Get next month's year and month number"""
    today = datetime.now()
    if today.month == 12:
        return today.year + 1, 1
    return today.year, today.month + 1


def get_current_month():
    """Get current month's year and month number"""
    today = datetime.now()
    return today.year, today.month


async def register_month(prefs, auth, target_year=None, target_month=None):
    """
    Register for all days of specified month with given preferences
    If target_year/month not provided, uses next month
    """
    
    if target_year is None or target_month is None:
        target_year, target_month = get_next_month()
    
    last_day = calendar.monthrange(target_year, target_month)[1]
    
    print(f"\n📅 Registering for {target_month:02d}/{target_year} (days 1-{last_day})")
    print(f"   Breakfast: {prefs.get('breakfast', 'NOT SET')}")
    print(f"   Lunch:     {prefs.get('lunch', 'NOT SET')}")
    print(f"   Dinner:    {prefs.get('dinner', 'NOT SET')}")
    print()
    
    success_count = 0
    fail_count = 0
    failed_registrations = []
    skipped_count = 0
    
    for day in range(1, last_day + 1):
        date_str = f"{target_year}-{target_month:02d}-{day:02d}"
        
        for meal_type, mess_id in prefs.items():
            if not mess_id:
                print(f"  ⊘ {date_str} {meal_type:9s} → SKIPPED (not configured)")
                skipped_count += 1
                continue
                
            try:
                params = CreateRegistrationInput(
                    meal_date=date_str,
                    meal_type=meal_type,
                    meal_mess=mess_id,
                    **auth
                )
                result = await mess_create_registration(params)
                
                if isinstance(result, dict) and result.get("error"):
                    error_msg = result.get("error", {}).get("message", str(result.get("error")))
                    if isinstance(error_msg, dict):
                        error_msg = error_msg.get("message", str(error_msg))
                    
                    # Check if it's a registration window error (normal - not all dates may be open)
                    if "only allowed until" in str(error_msg).lower() or "registration window" in str(error_msg).lower():
                        # Skip with info, don't count as failure
                        print(f"  ⊘ {date_str} {meal_type:9s} @ {mess_id:20s} → Outside registration window")
                        skipped_count += 1
                    else:
                        print(f"  ✗ {date_str} {meal_type:9s} @ {mess_id:20s} → {error_msg}")
                        fail_count += 1
                        failed_registrations.append({
                            "date": date_str,
                            "meal": meal_type,
                            "mess": mess_id,
                            "error": str(error_msg)
                        })
                else:
                    print(f"  ✓ {date_str} {meal_type:9s} @ {mess_id}")
                    success_count += 1
                    
            except Exception as e:
                print(f"  ✗ {date_str} {meal_type:9s} → Exception: {str(e)}")
                fail_count += 1
                failed_registrations.append({
                    "date": date_str,
                    "meal": meal_type,
                    "mess": mess_id,
                    "error": str(e)
                })
    
    print()
    print(f"{'='*60}")
    print(f"Registration Summary:")
    print(f"  ✓ Success:  {success_count}")
    print(f"  ⊘ Skipped:  {skipped_count} (outside registration window)")
    print(f"  ✗ Failed:   {fail_count}")
    print(f"{'='*60}")
    
    if failed_registrations:
        print("\nFailed Registrations (actual errors):")
        for reg in failed_registrations:
            print(f"  - {reg['date']} {reg['meal']} @ {reg['mess']}: {reg['error']}")
    
    if not REGISTER_CURRENT_MONTH:
        print("\n💡 TIP: This script is designed to run on the 27th of each month.")
        print("   If running on other dates, some dates may be outside the registration window.")
        print(f"   To test with current month: Set REGISTER_CURRENT_MONTH = 1 at the top of the script.")
    
    return success_count, fail_count


def main():
    """Main entry point"""
    print("=" * 60)
    print("IIITH Mess - Monthly Auto-Registration")
    print("=" * 60)
    
    # Load preferences
    prefs = load_preferences()
    
    # Get auth
    auth = get_auth()
    
    # Check configuration flag
    if REGISTER_CURRENT_MONTH:
        print("\n⚠️  OVERRIDE: Registering for CURRENT month instead of next month")
        target_year, target_month = get_current_month()
        success, failed = asyncio.run(register_month(prefs, auth, target_year, target_month))
    else:
        # Run registration for next month
        success, failed = asyncio.run(register_month(prefs, auth))
    
    # Exit with appropriate code
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
