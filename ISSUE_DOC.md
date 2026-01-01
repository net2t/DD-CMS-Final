# Issue Batch 1: December 2025

**Record Keeper:** Checklist for all fixes, status, and notes. Each issue has a title, description, label, assignee, and checklist for step-by-step progress.

---

## 1. Nickname Regex Expansion

- **Label:** enhancement
- **Assignee:** @OutLawZ
- **Description:** Allow more “weird” nicknames by expanding the regex in `sanitize_nickname_for_url`. Approved for implementation.
- [x] Expand regex for nickname validation
- [x] Test with edge-case nicknames
- [x] Mark as done

## 2. Sheet Sync / Race Condition

- **Label:** bug
- **Assignee:** @OutLawZ
- **Description:** If multiple users run the script at once or Google Sheets is slow, race conditions may occur. Investigate and add locking or retry logic if feasible.
- [x] Review concurrency handling
- [x] Add retry/locking if needed
- [x] Mark as done

## 3. Per-Phase Credentials & Sheets

- **Label:** enhancement
- **Assignee:** @OutLawZ
- **Description:** Each phase should use its own `credentials.json` and write to a separate sheet in the same workbook. Consider a shared dashboard for run records.
- [ ] Refactor phase config for credentials
- [ ] Support per-phase sheet output
- [ ] Shared dashboard logic
- [ ] Mark as done

## 4. Dead Code (Stubs)

- **Label:** documentation
- **Assignee:** @OutLawZ
- **Description:** Confirm stub files (e.g., `phase_mehfil.py`, `phase_posts.py`) are empty and clearly documented as placeholders for future phases.
- [ ] Check stub files
- [ ] Add placeholder comments
- [ ] Mark as done

## 5. README/Changelog: Track Fixes

- **Label:** documentation
- **Assignee:** @OutLawZ
- **Description:** Update README and CHANGELOG for each fix. Keep a running log of changes and improvements.
- [ ] Update docs for each fix
- [ ] Add “What’s New”/fix log
- [ ] Mark as done

## 6. RunList Skip Column

- **Label:** enhancement
- **Assignee:** @OutLawZ
- **Description:** Add a 4th column in RunList for skip logic. If a nickname is present in this row, script skips processing and moves to the next.
- [ ] Implement skip column logic
- [ ] Test skip behavior
- [ ] Mark as done

## 7. Dashboard/OnlineLog Row Order

- **Label:** enhancement
- **Assignee:** @OutLawZ
- **Description:** New data should always be inserted at Row 2 in Dashboard and OnlineLog, pushing older data down (consistent with Profiles sheet).
- [x] Refactor row insertion logic
- [x] Test Dashboard/OnlineLog order
- [x] Mark as done

## 8. Fix Blank Columns K, N, O

- **Label:** bug
- **Assignee:** @OutLawZ
- **Description:** Ensure columns K, N, O (Posts, Last Post, Last Post Time) are always populated if data is available.
- [x] Audit and fix extraction logic
- [x] Fix relative time parsing for all variants (sec/min/hour/day etc.) including leading '-' and missing number (e.g. 'min ago')
- [x] Verify on 3-4 profiles (online + target)
- [x] Mark as done

## 10. Fix Last Post Date/Time Logic

- **Label:** bug
- **Assignee:** @OutLawZ
- **Description:** Use dedicated method to extract last post link and date/time from public profile page, as described in provided help. Ensure correct assignment to sheet columns.
- [x] Implement dedicated extraction method
- [x] Assign values to correct columns
- [x] Normalize last-post URLs (clean reply/fragments; convert /content/<id>/.. to /comments/image/<id>)
- [x] Verify on 3-4 profiles
- [x] Mark as done

---

## Notes / Checkpoints

- [x] Checkpoint created on `main`: `checkpoint-2026-01-01_0310`
- [x] POSTS cleanup: remove '+' and ensure digits only (e.g. +999 / 999+)
- [x] Uppercase enforcement for columns H, L, M, O, T, U, W at write-time
- [x] Sheets formatting optimization: apply Quantico font once at end of run (avoid per-row formatting)
- [x] Keep Profiles column as `SKIP/DEL` (no `SOURCE` -> `Mode` rename needed)
- [ ] Sheet output changes approved: multi-line headers, RunList SKIP filtering, Dashboard DIFF, OnlineLog Batch #

---

**Instructions:**

- Work through each issue in order, checking off tasks as completed.
- Update this file after each fix.
- Merge all changes to main branch after all are marked done.
