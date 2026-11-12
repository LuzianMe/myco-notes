# Example entries (invented, to show the level of detail)

## Changelog entry (in `notes/state.md`, section 4)
- **2026-03-14 (rotate the object-store backup key, requested by the platform owner):** the key had not been rotated in 14 months and was shared by two jobs. **Built:** new key `backup-writer-2026` in the password manager entry "Backups / object store"; job `nightly-db-dump` (`notes/scripts/db-dump.sh`) and job `weekly-files` (`notes/scripts/files-backup.sh`) each use their own key now. **Backup/rollback:** old key kept disabled (not deleted) for 7 days; to roll back re-enable it in the provider console and revert commit `a1b2c3d`. **Tested:** forced a run of both jobs, both wrote a new object (`ls` size 1.9 GB and 410 MB), restore of the DB dump into a scratch instance took 11 minutes and `SELECT count(*)` matched. **Mistake:** I first changed only the weekly job; the nightly job failed at 02:00 with `AccessDenied`. **Lesson:** rotate all consumers of a key in one change; added to the runbook lessons list. **Follow-up:** delete the old key after 2026-03-21 (owner: platform owner).

## How-to entry (in `notes/runbook.md`)
## How do I restore the database from last night's dump? (since 2026-02-02)
Dumps are in the object store bucket `db-dumps`, one per night, kept 14 days. 1) `scripts/db-restore.sh <date> <target-host>` downloads, verifies the checksum and restores into an empty instance. 2) Verify: row counts of `orders` and `users` match `scripts/db-expected-counts.txt` within 1%. 3) Undo: the script never touches production; drop the scratch instance. Trap: the dump is taken at 02:00 UTC, which is 19:00 the previous day in Phoenix time. Last restore drill: 2026-03-14 (11 minutes).

## Lesson (in `notes/runbook.md`, "What mistakes were made and must not be repeated?")
- Never rotate a shared credential for only one of its consumers: the nightly job failed silently for a night on 2026-03-14. Instead list every consumer first (`grep -r backup-writer notes/scripts/`), change them in one commit, and run each job once.

## Incident record (in `notes/logs/incident-2026-01-09-queue-stall.md`)
## 2026-01-09 INCIDENT: message queue stalled for 41 minutes
Timeline (UTC): 09:12 first alert; 09:20 consumer lag 120k; 09:31 identified full disk on node 2; 09:44 pruned segments; 09:53 recovered. Effect: orders delayed up to 41 minutes, no loss. Cause (proven): retention set to 30 days after a config merge, disk filled. Fix: retention back to 3 days (`notes/scripts/queue-retention.conf`), alert at 70% disk added. Undo: set retention to 30 days again (not recommended). If it recurs: check disk first, then retention. Lesson copied to the runbook.

## Decision record (in `notes/plans/decision-search-engine.md`)
## Decision: search engine for the product catalogue (2026-02-20)
Context: current SQL `LIKE` search takes 1.8 s p95. Options: (1) managed search service, 400 USD/month, 2 days; (2) self-hosted engine on the existing cluster, 0 USD, 6 days, adds an on-call surface; (3) database full-text index, 0 USD, 1 day, p95 expected 300 ms. Chosen: option 3, by the platform owner. Why: lowest change and enough speed. Not chosen: 1 (cost), 2 (operational load). Review trigger: p95 above 500 ms for a week, or more than 5 million products.

## Sync-log line (in `notes/sync-tracker.md`)
- **2026-03-14 change (17:40 UTC, key rotation):** runbook, state.md and both backup scripts updated and committed; mirror pushed. **NOT synced:** the offline recovery copy still holds the old key reference (refresh at the next maintenance window, pending item 3); the search index is two days behind.

## Review proposal (in `notes/plans/review-2026-03-20.md`, method section 21)
The file's header lists what is still waiting (`open: 1, 2, 3` when written, `open: none` when all are answered; the lint checks it):
```
## 2. Two retention periods for the database backups
Kind: contradiction
Where: `state.md` (Backups and recovery, line 31); `runbook.md` ("How do I restore the database?", line 88)
Found: state.md says backups are kept 14 days, the runbook says 30. The backup job's config (scripts/db-backup.conf) says 14.
Proposed fix: runbook.md line 88, replace "kept for 30 days" with "kept for 14 days (scripts/db-backup.conf, verified 2026-03-20; was 30 until the 2026-02-11 change)".
Status: proposed
```
The owner answers "2 yes"; the line becomes `Status: applied 2026-03-20`, the header's `open:` loses the 2, and the fix is committed with the review file.

## Commit messages
- `Rotate backup key per job; document restore drill and the failure of the first attempt`
- `Add decision record for the catalogue search engine (option 3, full-text index)`
- `Mark queue incident follow-ups done; lower disk alert threshold to 70%`
