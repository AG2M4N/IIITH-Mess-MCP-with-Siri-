# IIITH Mess MCP

MCP server for the IIIT Hyderabad Mess System. Lets LLMs check registrations, view menus, manage meals, and track billing — all conversationally.

Requires IIIT VPN or intranet access.

## Examples of what you can ask

- "What am I eating today?"
- "Cancel all my Friday lunches"
- "Register me for dinner at Kadamba tomorrow"
- "What's on the menu tonight?"
- "Every week, register my favourite meals for the week"
- "Estimate the nutrition for tonight's dinner"
- "How much is my mess bill this month?"

## Prerequisites

- Python 3
- An auth key from [mess.iiit.ac.in](https://mess.iiit.ac.in) (Settings > Auth Keys), or a session cookie

## Setup

Clone the repo and create a `.env` file:

```
MESS_AUTH_KEY=your-auth-key-here
```

## Adding to Claude Code

Clone this repo and ask Claude to add it as an MCP.

Verify it connected:

```bash
claude mcp list
```

## Adding to GitHub Copilot (VS Code)

Create or edit `.vscode/mcp.json` in your workspace:

```json
{
  "servers": {
    "iiith-mess": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/IIITH-Mess-MCP", "python", "server.py"],
      "env": {
        "MESS_AUTH_KEY": "your-auth-key-here"
      }
    }
  }
}
```

Alternatively, run `MCP: Add Server` from the VS Code command palette for a guided setup.

---

Made with <3 at IIITH
