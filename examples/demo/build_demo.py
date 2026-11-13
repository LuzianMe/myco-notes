#!/usr/bin/env python3
"""build_demo: create the made-up "Greenhouse Sensors" notes tree and its map, for the README screenshots and the live demo.

    python3 examples/demo/build_demo.py OUT_DIR

OUT_DIR must not exist. The script bootstraps a tree with this kit, writes a few dozen invented notes in the method's formats,
commits them with fixed dates from January to March 2026 (so the timeline replay always tells the same story) and builds the map
(OUT_DIR/myco-notes/map/index.html and graph.html). Everything in it is fictional; nothing is read from the machine it runs on.
Standard library and git only, like the tools.
"""
import datetime
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.normpath(os.path.join(HERE, "..", "..", "skills", "myco-notes"))
# The demo's git identity and dates are set as variables of this process only, inherited by the git and kit commands it runs.
DEMO_GIT = {"GIT_AUTHOR_NAME": "Demo Owner", "GIT_AUTHOR_EMAIL": "demo@example.invalid",
            "GIT_COMMITTER_NAME": "Demo Owner", "GIT_COMMITTER_EMAIL": "demo@example.invalid"}

# (date, commit message, {path under myco-notes/: text}); text starting with "+" is appended to the note, "^" is a sync-log line put
# at the top of the log, "=old|new" replaces one line; any other text replaces the note (with its summary from SUMMARIES).
STEPS = [
    ("2026-01-06", "Sensor node: hardware, power budget and where the nodes hang", {
        "entities/sensor-node.md": """# Sensor node

Battery-powered node that measures air temperature, humidity and light every 5 minutes and sends them over LoRa.

- Hardware: ESP32 board, SHT41 sensor, 2 x AA lithium, IP65 box. Twelve nodes, inventory in `state.md`.
- Power budget: 38 uA asleep, 9 s awake per reading; measured life 14 months (bench test 2026-01-04).
- Sends to: `gateway.md`. Firmware: see the entity note for the firmware once it exists.
- How to replace batteries: `runbook.md`, "How do I swap a node's batteries?".
"""}),
    ("2026-01-09", "Gateway: the LoRa receiver in the potting shed", {
        "entities/gateway.md": """# LoRa gateway

Receives the readings from every `sensor-node.md` and publishes them to the broker.

- Where: potting shed, 2 m up, outdoor antenna. Power over Ethernet from the shed switch.
- Publishes to: `mqtt-broker.md`, topic `greenhouse/<house>/<node>/<metric>`.
- Health: `checks.md` pings it every minute; the inventory row is in `state.md`.
"""}),
    ("2026-01-12", "Broker: MQTT on the small server", {
        "entities/mqtt-broker.md": """# MQTT broker

Mosquitto 2.0 on the small server; every reading passes through it.

- Fed by: `gateway.md`. Read by: the time-series database (`timeseries-db.md`).
- Access: one account per client; the passwords live in the password manager, entry "Greenhouse / MQTT", never here.
- Restart and log locations: `runbook.md`.
"""}),
    ("2026-01-15", "Store the readings in a time-series database", {
        "entities/timeseries-db.md": """# Time-series database

Keeps every reading for two years (about 40 MB a month).

- Subscribes to `mqtt-broker.md`; schema: one measurement per metric, tags `house` and `node`.
- Version and size are in `state.md`; backups: see the backup job note when it exists.
"""}),
    ("2026-01-19", "Dashboard for the growers", {
        "entities/dashboard.md": """# Dashboard

One page per greenhouse: temperature, humidity, light, the valve state and the forecast.

- Reads from `timeseries-db.md`. Panels that turn red come from `alerting.md`.
"""}),
    ("2026-01-22", "Frost and heat alerts", {
        "entities/alerting.md": """# Alerting

Sends a phone notification when a greenhouse leaves its range for 10 minutes.

- Rules on top of `timeseries-db.md`: below 4 C (frost), above 35 C (heat), no reading from a node for 30 minutes.
- Shown on `dashboard.md`. What to do when an alert fires: `runbook.md`.
"""}),
    ("2026-01-26", "Decision: LoRa instead of Wi-Fi for the nodes", {
        "plans/decision-lora-vs-wifi.md": """# Decision: radio for the sensor nodes (2026-01-26)

Context: the greenhouses are 120 m from the house; Wi-Fi reached two of three in tests.
Options: (1) Wi-Fi with a mesh extender in each greenhouse; (2) LoRa with one `gateway.md`.
Chosen: option 2, by the owner. Why: one receiver covers all houses and a `sensor-node.md` lasts a year on batteries.
Not chosen: Wi-Fi (three extenders to power and patch; battery life about 6 weeks).
Review trigger: more than 40 nodes, or a reading every minute.
"""}),
    ("2026-01-30", "Irrigation valves, switched over MQTT", {
        "entities/irrigation-valve.md": """# Irrigation valve

24 V solenoid valves, one per bed, driven by a relay board that listens on `mqtt-broker.md`.

- A valve that stays open longer than 20 minutes raises an alert (`alerting.md`).
- Manual override: the switch on the relay box; see `runbook.md`.
"""}),
    ("2026-02-02", "Weather forecast feed", {
        "entities/weather-feed.md": """# Weather feed

Hourly forecast pulled from a public weather service and written to `timeseries-db.md`, so the dashboard can show it next to the readings.
"""}),
    ("2026-02-05", "Backlog", {
        "plans/backlog.md": """# Backlog

- Soil moisture per bed, so the valves open on need instead of on a timer (`irrigation-valve.md`).
- A second page on `dashboard.md` for the yearly comparison.
- Solar charging for the far nodes: see `solar-panel.md` (not written yet).
"""}),
    ("2026-02-09", "Nightly backup of the database", {
        "entities/backup-job.md": """# Backup job

Dumps `timeseries-db.md` every night at 02:00 to the NAS and once a week to an offline disk.

- Restore steps and the last restore drill: `runbook.md`. Status line in `state.md`.
"""}),
    ("2026-02-12", "Health checks", {
        "verification/checks.md": """# Health checks

A script runs every 5 minutes and reports pass / warn / fail:

- `gateway.md` answers ping; `mqtt-broker.md` accepts a test message; `backup-job.md` ran in the last 26 hours;
  every node in `sensor-node.md` reported in the last 30 minutes; `alerting.md` sent its daily test notification.
"""}),
    ("2026-02-16", "Greenhouse A", {
        "entities/greenhouse-a.md": """# Greenhouse A (tomatoes)

Four nodes (`sensor-node.md`), three beds, three valves (`irrigation-valve.md`). Shade cloth closes above 30 C.
"""}),
    ("2026-02-19", "Greenhouse B", {
        "entities/greenhouse-b.md": """# Greenhouse B (seedlings)

Five nodes (`sensor-node.md`), heated bench, two valves (`irrigation-valve.md`). Same layout as `greenhouse-a.md` otherwise.
"""}),
    ("2026-02-23", "Firmware 2.1 for the nodes", {
        "entities/firmware.md": """---
last_confirmed: 2026-02-23
review_after: 2026-03-01
---
# Node firmware

Version 2.1 on all nodes since 2026-02-23 (`sensor-node.md`). Why LoRa and not Wi-Fi: `decision-lora-vs-wifi.md`.

- Changed in 2.1: reading interval configurable, battery voltage sent with every reading.
- Calibration of the humidity offset is due again; see the review date above.
"""}),
    ("2026-02-27", "Incident: frost night in greenhouse B", {
        "logs/2026-02-frost-night.md": """# 2026-02-26 INCIDENT: frost night in greenhouse B

Timeline: 03:10 frost alert (`alerting.md`), 03:25 heater found off, 03:40 heater on, 04:30 back above 6 C.
Effect: some seedling trays damaged. Cause (proven): the heater's timer reset after a power cut.
Fix: the valve and heater schedule moved to the relay board (`irrigation-valve.md`), which keeps time.
The forecast had shown -3 C (`weather-feed.md`); a forecast-based warning is now on the backlog.
"""}),
    ("2026-02-28", "Source: RB-8 relay board manual; the valve note cites it", {
        "sources/2026-02-28-rb-8-relay-board-manual.md": '---\nsummary: Manual of the RB-8 relay board (excerpt): relays, clock backup, stored schedules\nsource_url: https://example.invalid/rb8-manual\nretrieved: 2026-02-28\nkind: manual\nsha256: 0fbb4725aecbbed419718f3da61d87f9921b02d643cadcf18abbbad6023f70dd\n---\n# RB-8 relay board manual\n\nRetrieved 2026-02-28 from https://example.invalid/rb8-manual. Kept as found (method section 22): not edited after saving.\n\nRelay board RB-8 (excerpt kept: timing and power)\n\n- Eight relays, 24 V coils, MQTT client built in.\n- Real-time clock with a supercapacitor: keeps time for 72 hours without power.\n- Schedules are stored on the board and run without the network.\n',
        "entities/irrigation-valve.md": "+\n## Why the schedule lives on the board (since 2026-02-28)\n- The board keeps time for 72 hours without power, per `2026-02-28-rb-8-relay-board-manual.md` (not tested here yet). That is why the frost-night fix moved the schedule here.\n"}),
    ("2026-03-02", "Soil probes arrived (not wired up yet)", {
        "entities/soil-probe.md": """# Soil probe

Capacitive soil moisture probes, six bought for a test in one bed. Not connected to anything yet.
"""}),
    ("2026-03-04", "Node note: firmware and where they hang", {
        "entities/sensor-node.md": "+\n## Since 2026-03-04\n- Firmware: `firmware.md`. Placement per house: `greenhouse-a.md`, `greenhouse-b.md`.\n"}),
    ("2026-03-06", "Broker topics for the valves and the checks", {
        "entities/mqtt-broker.md": "+\n## Topics (since 2026-03-06)\n- `greenhouse/valves/#` for `irrigation-valve.md`; `greenhouse/check` for `checks.md`.\n"}),
    ("2026-03-08", "Database: retention, backups, dashboard", {
        "entities/timeseries-db.md": "+\n## Retention and copies (since 2026-03-08)\n- Two years of raw data, then hourly means. Backed up by `backup-job.md`; read by `dashboard.md`.\n"}),
    ("2026-03-10", "Master record: inventory and headline facts", {
        "state.md": "+\n## Demo inventory (2026-03-10)\n| Name | Role | Note |\n|---|---|---|\n| Sensor nodes (12) | readings every 5 minutes | `sensor-node.md` |\n| LoRa gateway | radio to network | `gateway.md` |\n| MQTT broker | message bus | `mqtt-broker.md` |\n| Time-series database | storage, two years | `timeseries-db.md` |\n| Dashboard | for the growers | `dashboard.md` |\n"}),
    ("2026-03-12", "Runbook: batteries, alerts, restore", {
        "sync-tracker.md": "^- **2026-03-12 change:** runbook entries for batteries, frost alerts and restores; inventory in `state.md` (2026-03-10). Map rebuilt.\n",
        "runbook.md": "+\n## How do I swap a node's batteries? (since 2026-03-12)\nOpen the box, swap both cells, wait for the next reading on the dashboard. See `sensor-node.md`.\n\n## What do I do when a frost alert fires? (since 2026-03-12)\nCheck the heater first, then the valves. See `alerting.md` and the frost night incident.\n\n## How do I restore last night's backup? (since 2026-03-12)\nSee `backup-job.md`. Last restore drill: 2026-03-11, 4 minutes. Gateway restarts: `gateway.md`.\n"}),
    ("2026-03-15", "Review 2026-03-15 (scope: full): 3 proposals, nothing applied", {
        "plans/review-2026-03-15.md": '---\nsummary: Full review of 2026-03-15: node count, a missing link to the forecast, the firmware review date; nothing applied yet\nscope: full\nopen: 1, 2, 3\n---\n# Review 2026-03-15\n\nMade at the owner\'s request. Nothing in the notes has been changed: this file is the only thing committed. Answer per number: yes, no, or a change.\n\n## 1. Twelve nodes, but the houses list nine\nKind: contradiction\nWhere: `state.md` (Demo inventory); `greenhouse-a.md`; `greenhouse-b.md`\nFound: the inventory and `sensor-node.md` say twelve nodes; greenhouse A has four and greenhouse B five. Three are not placed anywhere in the notes.\nProposed fix: add to `backlog.md`:\n```\n- Where are the other three sensor nodes? `state.md` says 12, the houses list 9 (owner; found in the review of 2026-03-15).\n```\nStatus: proposed\n\n## 2. The dashboard shows the forecast but does not name its source\nKind: missing relation\nWhere: `dashboard.md` (first line)\nFound: the dashboard shows "the forecast", which comes from `weather-feed.md`; the dashboard note does not name it.\nProposed fix: in `dashboard.md` replace\n```\n- Reads from `timeseries-db.md`.\n```\nwith\n```\n- Reads from `timeseries-db.md` (the forecast comes from `weather-feed.md`).\n```\nStatus: proposed\n\n## 3. Firmware: the review date has passed\nKind: superseded\nWhere: `firmware.md` (header `review_after: 2026-03-01`)\nFound: the humidity calibration was due on 2026-03-01; nothing says it was done.\nProposed fix: calibrate one node against the reference sensor, then move `last_confirmed` and `review_after` (2026-09-01).\nStatus: proposed\n'}),
    ("2026-03-16", "Apply the review of 2026-03-15: forecast link (2); 3 declined, 1 waiting", {
        "plans/review-2026-03-15.md": '---\nsummary: Full review of 2026-03-15: forecast link applied, firmware calibration declined until April, the node count still waiting\nscope: full\nopen: 1\n---\n# Review 2026-03-15\n\nMade at the owner\'s request. When it was written nothing in the notes had been changed. On 2026-03-16 the owner answered: 2 yes (applied), 3 no, 1 not yet (waiting).\n\n## 1. Twelve nodes, but the houses list nine\nKind: contradiction\nWhere: `state.md` (Demo inventory); `greenhouse-a.md`; `greenhouse-b.md`\nFound: the inventory and `sensor-node.md` say twelve nodes; greenhouse A has four and greenhouse B five. Three are not placed anywhere in the notes.\nProposed fix: add to `backlog.md`:\n```\n- Where are the other three sensor nodes? `state.md` says 12, the houses list 9 (owner; found in the review of 2026-03-15).\n```\nStatus: proposed\n\n## 2. The dashboard shows the forecast but does not name its source\nKind: missing relation\nWhere: `dashboard.md` (first line)\nFound: the dashboard shows "the forecast", which comes from `weather-feed.md`; the dashboard note does not name it.\nProposed fix: in `dashboard.md` replace\n```\n- Reads from `timeseries-db.md`.\n```\nwith\n```\n- Reads from `timeseries-db.md` (the forecast comes from `weather-feed.md`).\n```\nStatus: applied 2026-03-16\n\n## 3. Firmware: the review date has passed\nKind: superseded\nWhere: `firmware.md` (header `review_after: 2026-03-01`)\nFound: the humidity calibration was due on 2026-03-01; nothing says it was done.\nProposed fix: calibrate one node against the reference sensor, then move `last_confirmed` and `review_after` (2026-09-01).\nStatus: declined 2026-03-16: the calibration is planned for April with the new reference sensor\n',
        "entities/dashboard.md": "=- Reads from `timeseries-db.md`.|- Reads from `timeseries-db.md` (the forecast comes from `weather-feed.md`).",
        "sync-tracker.md": "^- **2026-03-16 review:** applied 2 of `plans/review-2026-03-15.md` (dashboard names the forecast feed); declined 3 (calibration in April); 1 waiting.\n"}),
]

# One-line summaries (method 10.1), added as a header to every note the demo writes in full.
SUMMARIES = {
    "entities/sensor-node.md": "The battery LoRa nodes: hardware, power budget, where they send; read before changing a node or its batteries",
    "entities/gateway.md": "The LoRa gateway in the potting shed: where it hangs, what it publishes to, how it is checked",
    "entities/mqtt-broker.md": "The MQTT broker every reading passes through: clients, topics, where its passwords live",
    "entities/timeseries-db.md": "The time-series database: what it keeps for how long, its schema, backups and readers",
    "entities/dashboard.md": "The growers' dashboard: one page per greenhouse and where each panel's data comes from",
    "entities/alerting.md": "Frost, heat and silent-node alerts: the rules, where they show and what to do when one fires",
    "plans/decision-lora-vs-wifi.md": "Why the nodes use LoRa and not Wi-Fi (2026-01-26), what was not chosen and when to decide again",
    "entities/irrigation-valve.md": "The 24 V bed valves on the relay board: how they are switched, the 20-minute alert, manual override",
    "entities/weather-feed.md": "The hourly forecast feed written to the database and shown on the dashboard",
    "plans/backlog.md": "Parked ideas and open questions, each with what it waits on",
    "entities/backup-job.md": "Nightly database dump to the NAS and weekly offline copy; where restores are described",
    "verification/checks.md": "The 5-minute health check: what it tests and what pass, warn and fail mean",
    "entities/greenhouse-a.md": "Greenhouse A (tomatoes): its nodes, beds, valves and shade cloth",
    "entities/greenhouse-b.md": "Greenhouse B (seedlings): its nodes, heated bench and valves",
    "entities/firmware.md": "Node firmware version and what changed; the humidity calibration and its review date",
    "logs/2026-02-frost-night.md": "Frost night in greenhouse B (2026-02-26): timeline, cause, fix",
    "entities/soil-probe.md": "Six capacitive soil probes bought for a test; not connected yet",
}


def with_summary(rel, text):
    """The note's text with its summary in the header (an existing header gets the line added)."""
    s = SUMMARIES.get(rel)
    if not s:
        return text
    if text.startswith("---\n"):
        return "---\nsummary: " + s + "\n" + text[4:]
    return "---\nsummary: " + s + "\n---\n" + text


def run(args, cwd, date=None):
    os.environ.update(DEMO_GIT)
    if date:
        os.environ.update({"GIT_AUTHOR_DATE": date + "T10:00:00+00:00", "GIT_COMMITTER_DATE": date + "T10:00:00+00:00"})
    else:
        for k in ("GIT_AUTHOR_DATE", "GIT_COMMITTER_DATE"):
            os.environ.pop(k, None)
    return subprocess.run(args, cwd=cwd, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True).stdout


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    out = os.path.abspath(sys.argv[1])
    if os.path.exists(out):
        sys.exit("build_demo: %s exists; give a new folder" % out)
    run([sys.executable, os.path.join(KIT, "tools", "bootstrap.py"), out, "--name", "Greenhouse Sensors", "--owner", "Demo Owner",
         "--tz", "UTC", "--new-folders", "add"], HERE, "2026-01-05")
    notes = os.path.join(out, "myco-notes")
    today = datetime.date.today().isoformat()
    for dp, dn, fn in os.walk(out):
        dn[:] = [d for d in dn if d != ".git"]
        for f in fn:
            if f.endswith((".md", ".conf")):
                fp = os.path.join(dp, f)
                with open(fp, encoding="utf-8") as fh:
                    cur = fh.read()
                if today in cur:
                    with open(fp, "w", encoding="utf-8", newline="\n") as fh:
                        fh.write(cur.replace(today, "2026-01-05"))
    run(["git", "commit", "-q", "-a", "--amend", "--no-edit"], out, "2026-01-05")
    with open(os.path.join(out, ".myco-notes-map.json"), "w", encoding="utf-8") as fh:
        json.dump({"title": "Greenhouse Sensors (demo)", "groups": [
            {"id": "start", "name": "Start here", "blurb": "Entry point, working agreement, tracker, master record, runbook.",
             "prefixes": ["AGENTS.md", "CLAUDE.md"] + ["myco-notes/" + f for f in ("working-agreement.md", "sync-tracker.md", "state.md", "runbook.md")]},
            # The components are split by what they do, so the map shows several colours instead of one.
            {"id": "field", "name": "In the field", "blurb": "Nodes, radio, firmware and probes.",
             "prefixes": ["myco-notes/entities/" + f for f in ("sensor-node.md", "gateway.md", "firmware.md", "soil-probe.md")]},
            {"id": "data", "name": "Data path", "blurb": "Broker, database, forecast and backups.",
             "prefixes": ["myco-notes/entities/" + f for f in ("mqtt-broker.md", "timeseries-db.md", "weather-feed.md", "backup-job.md")]},
            {"id": "logs", "name": "Incidents", "blurb": "What went wrong and what changed.", "prefixes": ["myco-notes/logs/"]},
            {"id": "houses", "name": "Greenhouses", "blurb": "The houses, their beds and valves.",
             "prefixes": ["myco-notes/entities/" + f for f in ("greenhouse-a.md", "greenhouse-b.md", "irrigation-valve.md")]},
            {"id": "plans", "name": "Plans and decisions", "blurb": "Backlog and decision records.", "prefixes": ["myco-notes/plans/"]},
            {"id": "people", "name": "For the growers", "blurb": "What the growers see and hear.",
             "prefixes": ["myco-notes/entities/" + f for f in ("dashboard.md", "alerting.md")]},
            {"id": "verify", "name": "Verification", "blurb": "Health checks.", "prefixes": ["myco-notes/verification/"]},
            {"id": "docs", "name": "Method", "blurb": "How the notes are kept.", "prefixes": ["myco-notes/docs/"]},
            {"id": "other", "name": "Other notes", "blurb": "Everything else.", "prefixes": []}]}, fh, indent=1)
    for date, msg, files in STEPS:
        for rel, text in files.items():
            p = os.path.join(notes, *rel.split("/"))
            os.makedirs(os.path.dirname(p), exist_ok=True)
            if text.startswith("+"):                      # append
                with open(p, "a", encoding="utf-8", newline="\n") as fh:
                    fh.write(text[1:])
            elif text.startswith(("^", "=")):              # ^: newest-first sync-log line; =old|new: replace one line
                with open(p, encoding="utf-8") as fh:
                    cur = fh.read()
                if text[0] == "^":
                    head = "## Sync log (newest first)\n"
                    assert head in cur, rel
                    cur = cur.replace(head, head + text[1:], 1)
                else:
                    old, new = text[1:].split("|", 1)
                    assert cur.count(old) == 1, (rel, old)
                    cur = cur.replace(old, new)
                with open(p, "w", encoding="utf-8", newline="\n") as fh:
                    fh.write(cur)
            else:
                with open(p, "w", encoding="utf-8", newline="\n") as fh:
                    fh.write(with_summary(rel, text))
        run(["git", "add", "-A"], out)
        run(["git", "commit", "-q", "-m", msg], out, date)
    print(run([sys.executable, os.path.join(notes, "tools", "build-notes-map.py")], out).strip())


if __name__ == "__main__":
    main()
