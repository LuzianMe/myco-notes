#!/usr/bin/env python3
"""build_demo: create the made-up "Greenhouse Sensors" notes tree and its map, for the README screenshots and the live demo.

    python3 examples/demo/build_demo.py OUT_DIR

OUT_DIR must not exist. The script bootstraps a tree with this kit, writes a few dozen invented notes in the method's formats,
commits them with fixed dates from January to March 2026 (so the timeline replay always tells the same story) and builds the map
(OUT_DIR/myco-notes/map/index.html and graph.html). Everything in it is fictional; nothing is read from the machine it runs on.
Standard library and git only, like the tools.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.normpath(os.path.join(HERE, "..", "..", "skills", "myco-notes"))
ENV = dict(os.environ, GIT_AUTHOR_NAME="Demo Owner", GIT_AUTHOR_EMAIL="demo@example.invalid",
           GIT_COMMITTER_NAME="Demo Owner", GIT_COMMITTER_EMAIL="demo@example.invalid")

# (date, commit message, {path under myco-notes/: text}); text starting with "+" is appended to the note instead of replacing it.
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
        "runbook.md": "+\n## How do I swap a node's batteries? (since 2026-03-12)\nOpen the box, swap both cells, wait for the next reading on the dashboard. See `sensor-node.md`.\n\n## What do I do when a frost alert fires? (since 2026-03-12)\nCheck the heater first, then the valves. See `alerting.md` and the frost night incident.\n\n## How do I restore last night's backup? (since 2026-03-12)\nSee `backup-job.md`. Last restore drill: 2026-03-11, 4 minutes. Gateway restarts: `gateway.md`.\n"}),
]


def run(args, cwd, date=None):
    env = dict(ENV)
    if date:
        env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = date + "T10:00:00+00:00"
    return subprocess.run(args, cwd=cwd, env=env, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True).stdout


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    out = os.path.abspath(sys.argv[1])
    if os.path.exists(out):
        sys.exit("build_demo: %s exists; give a new folder" % out)
    env_date = "2026-01-05"
    os.environ.update({"GIT_AUTHOR_DATE": env_date + "T09:00:00+00:00", "GIT_COMMITTER_DATE": env_date + "T09:00:00+00:00"})
    run([sys.executable, os.path.join(KIT, "tools", "bootstrap.py"), out, "--name", "Greenhouse Sensors", "--owner", "Demo Owner",
         "--tz", "UTC", "--new-folders", "add"], HERE, env_date)
    for k in ("GIT_AUTHOR_DATE", "GIT_COMMITTER_DATE"):
        os.environ.pop(k, None)
    notes = os.path.join(out, "myco-notes")
    with open(os.path.join(out, ".myco-notes-map.json"), "w", encoding="utf-8") as fh:
        json.dump({"title": "Greenhouse Sensors (demo)", "groups": [
            {"id": "start", "name": "Start here", "blurb": "Entry point, working agreement, tracker, master record, runbook.",
             "prefixes": ["AGENTS.md", "CLAUDE.md"] + ["myco-notes/" + f for f in ("working-agreement.md", "sync-tracker.md", "state.md", "runbook.md")]},
            {"id": "components", "name": "Components", "blurb": "One note per part of the system.", "prefixes": ["myco-notes/entities/"]},
            {"id": "plans", "name": "Plans and decisions", "blurb": "Backlog and decision records.", "prefixes": ["myco-notes/plans/"]},
            {"id": "logs", "name": "Incidents", "blurb": "What went wrong and what changed.", "prefixes": ["myco-notes/logs/"]},
            {"id": "verify", "name": "Verification", "blurb": "Health checks.", "prefixes": ["myco-notes/verification/"]},
            {"id": "docs", "name": "Method", "blurb": "How the notes are kept.", "prefixes": ["myco-notes/docs/"]},
            {"id": "other", "name": "Other notes", "blurb": "Everything else.", "prefixes": []}]}, fh, indent=1)
    for date, msg, files in STEPS:
        for rel, text in files.items():
            p = os.path.join(notes, *rel.split("/"))
            os.makedirs(os.path.dirname(p), exist_ok=True)
            if text.startswith("+"):
                with open(p, "a", encoding="utf-8", newline="\n") as fh:
                    fh.write(text[1:])
            else:
                with open(p, "w", encoding="utf-8", newline="\n") as fh:
                    fh.write(text)
        run(["git", "add", "-A"], out)
        run(["git", "commit", "-q", "-m", msg], out, date)
    print(run([sys.executable, os.path.join(notes, "tools", "build-notes-map.py")], out).strip())


if __name__ == "__main__":
    main()
