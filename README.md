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

- An auth key from [mess.iiit.ac.in](https://mess.iiit.ac.in) (Settings > Auth Keys), or a session cookie
- uv

## Adding to Claude Code

### Via uv (recommended)

```bash
claude mcp add iiith-mess -e MESS_AUTH_KEY=your-auth-key -- uvx iiith-mess-mcp
```

### Via local clone

```bash
git clone https://github.com/Kallind/IIITH-Mess-MCP
claude mcp add iiith-mess -e MESS_AUTH_KEY=your-auth-key -- uv run --directory IIITH-Mess-MCP python iiith_mess_mcp/server.py
```

Verify it connected:

```bash
claude mcp list
```

## Adding to GitHub Copilot (VS Code)

Simplest way: Just ask Copilot to set it up by providing this repository URL.

### Via uvx

Create or edit `.vscode/mcp.json` in your workspace:

```json
{
  "servers": {
    "iiith-mess": {
      "type": "stdio",
      "command": "uvx",
      "args": ["iiith-mess-mcp"],
      "env": {
        "MESS_AUTH_KEY": "your-auth-key-here"
      }
    }
  }
}
```

### Via local clone

```json
{
  "servers": {
    "iiith-mess": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--directory", "/path/to/IIITH-Mess-MCP", "python", "iiith_mess_mcp/server.py"],
      "env": {
        "MESS_AUTH_KEY": "your-auth-key-here"
      }
    }
  }
}
```

---

Made with <3 at IIITH by [Kallind Soni](https://github.com/Kallind) and [Arihant Tripathy](https://github.com/Arihant25)
