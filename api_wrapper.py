"""
REST API wrapper for IIITH Mess MCP Server
Bridge between MCP server and Siri Shortcuts / external integrations

Usage:
    python api_wrapper.py

Then from Siri Shortcut, make HTTP requests to http://localhost:5000/api/...
"""

import os
import asyncio
from typing import Optional
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Import MCP tools
from iiith_mess_mcp.server import (
    mess_get_registrations,
    mess_create_registration,
    mess_cancel_registration,
    mess_get_menus,
    mess_get_info,
    mess_get_me,
    mess_login_msit,
    GetRegistrationsInput,
    CreateRegistrationInput,
    MealDateTypeInput,
    MsitLoginInput,
)

load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable cross-origin requests (needed for Siri Shortcuts)

# Store active session for current user
current_session = {}

# ─────────────────────────────────────────────
# Helper Functions
# ─────────────────────────────────────────────

def run_async(coro):
    """Run async MCP function in sync context"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


def get_auth_context():
    """Get auth_key from env or session from current_session"""
    auth_key = os.environ.get("MESS_AUTH_KEY")
    session = current_session.get("session")
    return {"auth_key": auth_key, "session": session}


def normalize_mess_name(mess_name):
    """Normalize mess name for comparison (lowercase, remove diacritics)"""
    import unicodedata
    if not mess_name:
        return ""
    # Remove diacritics and convert to lowercase
    nfd = unicodedata.normalize('NFD', mess_name.lower())
    return ''.join(char for char in nfd if unicodedata.category(char) != 'Mn')


def menus_list_to_dict(menus_result):
    """Convert menus result (list) to dict with mess IDs as keys
    
    Expected format: [{"mess": "mess_id", "days": {...}, ...}, ...]
    Returns: {"mess_id": {"days": {...}, ...}, ...}
    """
    # If already a dict, return as is
    if isinstance(menus_result, dict):
        return menus_result
    
    # If list, convert to dict keyed by mess ID
    menus_dict = {}
    if isinstance(menus_result, list):
        for item in menus_result:
            if isinstance(item, dict):
                # Menu objects have a "mess" field with the mess ID
                mess_id = item.get("mess")
                if mess_id:
                    menus_dict[mess_id] = item
    
    # If empty, log for debugging
    if not menus_dict:
        print(f"[DEBUG] menus_list_to_dict: Could not convert menus. Result type: {type(menus_result)}")
        if isinstance(menus_result, list) and menus_result:
            print(f"[DEBUG] First item keys: {list(menus_result[0].keys()) if isinstance(menus_result[0], dict) else 'not a dict'}")
    
    return menus_dict


def find_mess_in_dict(mess_filter, all_menus):
    """Find mess key in all_menus dict, handling different name formats"""
    # First try exact match
    if mess_filter in all_menus:
        return mess_filter
    
    # Then try normalized match
    normalized_filter = normalize_mess_name(mess_filter)
    for mess_key in all_menus.keys():
        if normalize_mess_name(mess_key) == normalized_filter:
            return mess_key
    
    return None


def get_user_last_registered_mess(date=None):
    """
    DEPRECATED: No longer used - registrations are handled via cron job
    Kept for reference only
    """
    try:
        auth = get_auth_context()
        from datetime import datetime, timedelta
        
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        
        # Get user's registrations
        from_date = date
        to_date = date
        params = GetRegistrationsInput(from_date=from_date, to_date=to_date, **auth)
        registrations = run_async(mess_get_registrations(params))
        
        if registrations and isinstance(registrations, list) and len(registrations) > 0:
            # Return the mess_id of the first registration for this date
            return registrations[0].get("mess_id") or registrations[0].get("meal_mess")
        
        return None
    except Exception:
        return None


# ─────────────────────────────────────────────
# Authentication Endpoints
# ─────────────────────────────────────────────

@app.route("/api/auth/login", methods=["POST"])
def login_msit():
    """
    Login with MSIT credentials
    
    Request body:
    {
        "user": "email@msitprogram.net",
        "password": "your_password"
    }
    
    Response: User info + session cookie
    """
    try:
        data = request.get_json()
        user = data.get("user")
        password = data.get("password")
        
        if not user or not password:
            return jsonify({"error": "Missing user or password"}), 400
        
        params = MsitLoginInput(user=user, password=password)
        result = run_async(mess_login_msit(params))
        
        # Store session if successful
        if isinstance(result, dict) and "session_hint" in result:
            current_session["session"] = result["session_hint"]["session"]
            return jsonify({
                "success": True,
                "message": f"Logged in as {result.get('name', user)}",
                "user": result
            }), 200
        
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/auth/logout", methods=["POST"])
def logout():
    """Clear stored session"""
    current_session.clear()
    return jsonify({"success": True, "message": "Logged out"}), 200


@app.route("/api/me", methods=["GET"])
def get_me():
    """Get current user profile"""
    try:
        auth = get_auth_context()
        result = run_async(mess_get_me(auth))
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────
# Meal Registration Endpoints
# ─────────────────────────────────────────────

@app.route("/api/meal/register", methods=["POST"])
def register_meal():
    """
    Register for a meal
    
    Request body:
    {
        "date": "2026-04-04",
        "meal": "lunch",
        "mess": "kadamba-nonveg"
    }
    
    Response: Success message or error
    """
    try:
        data = request.get_json()
        date = data.get("meal_date") or data.get("date")
        meal = data.get("meal_type") or data.get("meal")
        mess = data.get("mess_id") or data.get("mess")
        guests = data.get("guests")
        
        if not all([date, meal, mess]):
            return jsonify({
                "error": "Missing required fields: date, meal, mess",
                "example": {
                    "meal_date": "2026-04-04",
                    "meal_type": "lunch",
                    "meal_mess": "kadamba-nonveg",
                    "guests": 0
                }
            }), 400
        
        auth = get_auth_context()
        params = CreateRegistrationInput(
            meal_date=date,
            meal_type=meal,
            meal_mess=mess,
            guests=guests,
            **auth
        )
        result = run_async(mess_create_registration(params))
        
        if isinstance(result, dict) and "error" not in result:
            return jsonify({
                "success": True,
                "message": f"Registered for {meal.capitalize()} on {date}",
                "data": result
            }), 200
        
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/meal/cancel", methods=["POST"])
def cancel_meal():
    """
    Cancel a meal registration
    
    Request body:
    {
        "date": "2026-04-04",
        "meal": "lunch",
        "mess": "kadamba-nonveg"
    }
    """
    try:
        data = request.get_json()
        date = data.get("meal_date") or data.get("date")
        meal = data.get("meal_type") or data.get("meal")
        mess = data.get("mess_id") or data.get("mess")
        
        if not all([date, meal, mess]):
            return jsonify({"error": "Missing required: date, meal, mess"}), 400
        
        auth = get_auth_context()
        params = MealDateTypeInput(
            meal_date=date,
            meal_type=meal,
            **auth
        )
        result = run_async(mess_cancel_registration(params))
        
        if isinstance(result, dict) and "error" not in result:
            return jsonify({
                "success": True,
                "message": f"Cancelled {meal} on {date}",
                "data": result
            }), 200
        
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/meals/registrations", methods=["GET"])
def get_registrations():
    """
    Get user's meal registrations
    
    Query params:
        from_date (optional): YYYY-MM-DD
        to_date (optional): YYYY-MM-DD
    """
    try:
        from_date = request.args.get("from_date") or request.args.get("from")
        to_date = request.args.get("to_date") or request.args.get("to")
        
        # Default to today and 7 days ahead if not specified
        from datetime import datetime, timedelta
        if not from_date:
            from_date = datetime.now().strftime("%Y-%m-%d")
        if not to_date:
            to_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        
        auth = get_auth_context()
        params = GetRegistrationsInput(from_date=from_date, to_date=to_date, **auth)
        result = run_async(mess_get_registrations(params))
        
        return jsonify({
            "success": True,
            "registrations": result
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────
# Menu & Info Endpoints
# ─────────────────────────────────────────────

# ─────────────────────────────────────────────
# Interactive Siri Endpoint (Single Shortcut)
# ─────────────────────────────────────────────

@app.route("/api/interact", methods=["POST"])
def interact():
    """
    Unified endpoint for Siri interactions
    Handles menu queries and meal cancellations
    (Registrations are automated via cron job)
    
    Request body:
    {
        "action": "cancel" | "menu",
        "date": "2026-04-05" (optional for menu, required for cancel),
        "meal_type": "lunch" (required for cancel)
    }
    
    Response:
    {
        "success": true,
        "spoken": "Cancelled lunch on April 5th",
        "details": {...}
    }
    """
    try:
        data = request.get_json() or {}
        action = data.get("action", "").lower()
        
        if not action:
            return jsonify({
                "success": False,
                "spoken": "Action not specified. Try: cancel or menu"
            }), 400
        
        # CANCEL MEAL
        if action == "cancel":
            date = data.get("date")
            meal_type = data.get("meal_type")
            
            if not all([date, meal_type]):
                return jsonify({
                    "success": False,
                    "spoken": "Missing date or meal type. Please provide both."
                }), 400
            
            auth = get_auth_context()
            params = MealDateTypeInput(
                meal_date=date,
                meal_type=meal_type,
                **auth
            )
            result = run_async(mess_cancel_registration(params))
            
            # Check if error response
            if isinstance(result, dict) and result.get("error"):
                error_msg = result.get("error", {}).get("message", "Unknown error") if isinstance(result.get("error"), dict) else result.get("error")
                return jsonify({
                    "success": False,
                    "spoken": f"Failed to cancel: {error_msg}"
                }), 400
            
            # Success - result is {"ok": true}
            if isinstance(result, dict) and result.get("ok"):
                from datetime import datetime
                try:
                    date_obj = datetime.strptime(date, "%Y-%m-%d")
                    nice_date = date_obj.strftime("%B %d, %Y")
                except:
                    nice_date = date
                    
                return jsonify({
                    "success": True,
                    "spoken": f"Cancelled {meal_type} on {nice_date}",
                    "details": result
                }), 200
            else:
                return jsonify({
                    "success": False,
                    "spoken": f"Failed to cancel: Unexpected response from server"
                }), 400
        
        # GET MENUS (SMART - Based on user's registrations)
        elif action == "menu":
            from iiith_mess_mcp.server import mess_get_menus, MessMenuInput
            from datetime import datetime, timedelta
            
            date = data.get("date")
            if not date:
                date = datetime.now().strftime("%Y-%m-%d")
            
            # SMART: Get user's registrations for this date
            auth = get_auth_context()
            registrations = []
            try:
                params = GetRegistrationsInput(from_date=date, to_date=date, **auth)
                reg_result = run_async(mess_get_registrations(params))
                if isinstance(reg_result, list):
                    registrations = reg_result
            except:
                pass  # If can't get registrations, fall back to showing first mess
            
            # Build a map of meal_type -> mess_id from registrations
            registered_messes = {}
            for reg in registrations:
                meal_type = reg.get("meal_type")
                mess_id = reg.get("meal_mess")
                if meal_type and mess_id:
                    registered_messes[meal_type] = mess_id
            
            # If no registrations, ask for mess_id parameter
            if not registered_messes:
                mess_filter = data.get("mess_id")
                if not mess_filter:
                    return jsonify({
                        "success": False,
                        "spoken": "No registrations for today. Please specify a mess using mess_id parameter."
                    }), 400
                # User specified mess_id, use that for all meals
                registered_messes = {"breakfast": mess_filter, "lunch": mess_filter, "dinner": mess_filter}
            
            # Get all menus
            menus_result = run_async(mess_get_menus(MessMenuInput(on=date)))
            all_menus = menus_list_to_dict(menus_result)
            
            if not all_menus:
                return jsonify({
                    "success": False,
                    "spoken": "No menus available for this date"
                }), 404
            
            # Format response by meal type, showing each registered mess's menu
            today_name = datetime.now().strftime("%A").lower()
            spoken_parts = []
            menu_details = {}
            
            for meal_type in ["breakfast", "lunch", "dinner"]:
                mess_id = registered_messes.get(meal_type)
                if not mess_id:
                    continue
                
                # Find the menu for this mess
                actual_mess_key = find_mess_in_dict(mess_id, all_menus)
                if not actual_mess_key:
                    continue
                
                menu_data = all_menus[actual_mess_key]
                day_menus = menu_data.get("days", {})
                today_menu = day_menus.get(today_name, {})
                
                # Get all items for this meal (not just first 3!)
                if meal_type in today_menu:
                    items = [d["item"] for d in today_menu[meal_type] if d.get("item", "").strip()]
                    if items:
                        items_str = ", ".join(items)
                        spoken_parts.append(f"{meal_type.capitalize()} ({actual_mess_key}): {items_str}")
                        menu_details[meal_type] = {
                            "mess": actual_mess_key,
                            "items": items
                        }
            
            if not spoken_parts:
                return jsonify({
                    "success": False,
                    "spoken": "No menu items found for your registered meals"
                }), 404
            
            spoken = ". ".join(spoken_parts)
            
            return jsonify({
                "success": True,
                "spoken": spoken,
                "details": {
                    "date": date,
                    "day": today_name,
                    "meals": menu_details,
                    "registrations": registered_messes
                }
            }), 200
        
        else:
            return jsonify({
                "success": False,
                "spoken": f"Unknown action: {action}"
            }), 400
    
    except Exception as e:
        return jsonify({
            "success": False,
            "spoken": f"Error: {str(e)}"
        }), 500


@app.route("/api/menus", methods=["GET"])
def get_menus():
    """
    Smart menu endpoint with mess filtering
    
    Query params:
        date (optional): YYYY-MM-DD, defaults to today
        mess (optional): Filter by specific mess (e.g., yuktahar, palash, kadamba-nonveg)
    
    Behavior:
        - If mess param provided: Return only that mess's menu
        - If no mess param: Return user's registered mess menu
        - If no registration: Return all mess menus
    """
    try:
        date = request.args.get("date")
        mess_filter = request.args.get("mess")
        
        from iiith_mess_mcp.server import mess_get_menus, MessMenuInput
        
        # Get all menus
        menus_result = run_async(mess_get_menus(MessMenuInput(on=date)))
        all_menus = menus_list_to_dict(menus_result)
        
        # Normalize date for logging
        from datetime import datetime
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        
        # If specific mess requested, return just that
        if mess_filter:
            actual_mess_key = find_mess_in_dict(mess_filter, all_menus)
            if actual_mess_key:
                return jsonify({
                    "success": True,
                    "date": date,
                    "mess": actual_mess_key,
                    "menus": {actual_mess_key: all_menus[actual_mess_key]}
                }), 200
            else:
                return jsonify({
                    "error": f"Mess '{mess_filter}' not found",
                    "available_messes": list(all_menus.keys())
                }), 404
        
        # Smart mode: Try to get user's registered mess
        user_mess = get_user_last_registered_mess(date)
        if user_mess:
            actual_mess_key = find_mess_in_dict(user_mess, all_menus)
            if actual_mess_key:
                return jsonify({
                    "success": True,
                    "date": date,
                    "mess": actual_mess_key,
                    "mode": "user_registered",
                    "menus": {actual_mess_key: all_menus[actual_mess_key]}
                }), 200
        
        # Fallback: Return all messes
        return jsonify({
            "success": True,
            "date": date,
            "mode": "all_messes",
            "message": "No specific mess requested. Showing all available messes.",
            "menus": all_menus
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/messes", methods=["GET"])
def get_messes():
    """Get all available messes"""
    try:
        result = run_async(mess_get_info())
        
        messes = []
        if isinstance(result, list):
            for mess in result:
                messes.append({
                    "name": mess.get("name"),
                    "id": mess.get("short_name"),
                    "tags": mess.get("tags", [])
                })
        
        return jsonify({
            "success": True,
            "messes": messes
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────
# Health & Debug Endpoints
# ─────────────────────────────────────────────

@app.route("/api/health", methods=["GET"])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "ok",
        "authenticated": bool(current_session.get("session") or os.environ.get("MESS_AUTH_KEY"))
    }), 200


@app.route("/api/help", methods=["GET"])
def help_endpoint():
    """Get API documentation"""
    return jsonify({
        "endpoints": {
            "Authentication": {
                "POST /api/auth/login": "Login with MSIT credentials",
                "POST /api/auth/logout": "Clear session",
                "GET /api/me": "Get current user"
            },
            "Registrations": {
                "POST /api/meal/cancel": "Cancel a meal"
            },
            "Info": {
                "GET /api/menus": "SMART: Get menus for ALL your registered meals today (breakfast at mess1, lunch at mess2, dinner at mess3)",
                "GET /api/menus?mess_id=yuktahar": "Get specific mess menu (if not registered today)",
                "GET /api/menus?date=2026-04-05": "Get menus for specific date (uses your registrations for that date)",
                "GET /api/menus?date=2026-04-05&mess_id=palash": "Get specific mess for specific date"
            }
        },
        "examples": {
            "get_smart_menu": "POST /api/interact with {\"action\": \"menu\"} - shows menus for each of your registered meals",
            "get_specific_mess": "POST /api/interact with {\"action\": \"menu\", \"mess_id\": \"yuktahar\"}",
            "get_for_date": "POST /api/interact with {\"action\": \"menu\", \"date\": \"2026-04-05\"}",
            "cancel_meal": "POST /api/interact with {\"action\": \"cancel\", \"date\": \"2026-04-05\", \"meal_type\": \"lunch\"}"
        }
    }), 200


@app.route("/", methods=["GET"])
def index():
    """Root endpoint with API info"""
    return jsonify({
        "name": "IIITH Mess MCP - Siri Integration API",
        "version": "1.0.0",
        "info": "REST API wrapper for IIITH Mess management",
        "docs": "Visit /api/help for endpoint documentation"
    }), 200


# ─────────────────────────────────────────────
# Error Handlers
# ─────────────────────────────────────────────

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found", "available": "/api/help"}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    print("=" * 60)
    print("IIITH Mess MCP - Siri Integration API")
    print("=" * 60)
    print("Starting server on http://localhost:5000")
    print("API Documentation: http://localhost:5000/api/help")
    print("\nMake sure MESS_AUTH_KEY is set in .env or login first!")
    print("=" * 60)
    
    app.run(debug=True, host="0.0.0.0", port=5500)
