---
description: Run Phase 2 Post Scraping (Manual & Auto)
---
# Phase 2: Post Scraping Workflow

This workflow executes extracting user posts to the `Posts` sheet for profiles identified as "Ready" in the `Profiles` sheet.

## Sheet Structure (Posts Tab)

When this workflow executes, it captures the following columns into the `Posts` sheet:

| Index | Column Header    | Description |
|---|---|---|
| A | **PROFILE ID** | The internal DamaDam Profile ID (Relationship ID to original sheet) |
| B | **NICK NAME**  | User's nickname formatted as a clickable $=HYPERLINK$ back to their URL |
| C | **POST URL**   | The direct link to this specific post's comments |
| D | **POST TYPE**  | Either "Text" or "Image" |
| E | **POST TIME**  | Time text like "5 days ago" or "2 hours ago" |
| F | **CONTENT**    | The body text of the post or the image caption |
| G | **IMAGE URL**  | Direct link to the image source (if an Image post) |
| H | **REPLIES**    | Comments count directly on the post |
| I | **IS TEMPORARY**| Determines if the user disabled comments or if it's a 24-hr expiry post |
| J | **DATETIME SCRAP**| Timestamp of when this row was captured |

## 🚀 Run Operations

### 1. Run Manually (Limit = 10)
Use this command to instantly run exactly 1 batch of 10 profiles for Phase 2. The script will close when finished.
```bash
// turbo
python run.py posts --limit 10
```

### 2. Start Automated Scheduler
Use this command to start the background automation loop. It will run 10 profiles immediately, and then wait 30 minutes before running another 10, repeating endlessly.
```bash
// turbo
python run.py scheduler_posts
```

> **Note**: To stop the automated scheduler, focus the terminal and hit `Ctrl+C`.
