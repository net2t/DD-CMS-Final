---
description: Run Phase 1 Online Mode (Auto 15 min)
---
# Phase 1: Online Mode Scheduler (Every 15 min)

This workflow scans the DamaDam `/online` page, collects currently online active users, and executes Phase 1 scraping (Profile details) continuously. 

It is designed to run automatically **every 15 minutes**. It avoids repeats by ensuring previous runs have successfully completed, using lock files.

## 🚀 Run the Online Automator

Use this command to start the continuous Phase 1 Online monitor:

```bash
// turbo
python run.py scheduler --limit 0
```

> **Note**: This will loop endlessly and pull all available online users. To specify a max profile limit per loop, change `--limit 0` to `--limit 50`. To stop the loop entirely, focus the terminal and press `Ctrl+C`.
