---
description: Run Phase 2 Hourly (Auto 20 Profiles)
---
# Phase 2: Hourly Post Scraping Automation

This workflow actively tracks and scrapes posts for profiles marked as "Ready" across your DamaDam list. 
It is configured to run automatically **every hour** (60 minutes) and will process exactly **20 profiles** per hour.

## 🚀 Run the Hourly Automator

Use this command to start the background automation loop:

```bash
// turbo
python run.py scheduler_posts --interval 60 --limit 20
```

> **Note**: This will instantly process the first 20 profiles. It will then sleep for 60 minutes, and repeat. Leave the terminal open. To pause or stop this automation, focus the terminal and hit `Ctrl+C`.
