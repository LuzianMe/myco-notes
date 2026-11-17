# Restore drill and health check

*Part of the Myco Notes skill: read `SKILL.md` (the folder above) first for `<KIT>`, `<notes>`, `<tools>` and the guard rails, which always apply.*

**When:** Proving the backup restores; checking the repository's kit version, hook, layout and settings.

## Restore drill
`<tools>/restore-drill <restored dir or archive>` (two verdicts: history and working copy; report both).

## Health check
`<tools>/doctor` (read-only) reports the repository's kit version, the hook, the layout and missing settings. Run `python3 "<KIT>/tools/doctor.py" --root <project>` from the kit to also see whether the repository's tools are older than the kit; if they are, offer the `relocate` refresh in `setup.md`.
