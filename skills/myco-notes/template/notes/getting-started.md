---
summary: For the owner, not for agents: what this notes repository gives you, what the agent does on its own, what needs your yes, your part, your options, and what you can say
---
# Getting started with the {{PROJECT_NAME}} notes

Created {{DATE}}. This page is for you, the owner. Agents read `AGENTS.md`; this page says in plain words what you now have and what is up to you. Change it when something here stops being true (you set up a backup copy, a team joins).

## What you now have
- **Notes that stay true.** After a change you make or ask for, your agent checks the real system, updates the right note and commits it. Every version stays in git, so nothing is lost.
- **A briefing at the start of each session:** what is current, what is unfinished, what is waiting on you.
- **Answers with their source:** ask a question and the agent answers from the notes, naming the note (and the document or date behind it).
- **Any past date:** what the notes said on a given day, and what changed since.
- **A map** of how the notes connect, with backlinks and a replay of their history (built on request, opened in a browser).

## What the agent does without asking
- Updates and commits the notes after a change you made or asked for.
- Saves a quick note when you say "note that…" or "remember…".
- Refuses to commit anything that looks like a password, key or token.
- Marks what it could not check as "not verified" instead of guessing.

## What needs your yes
- Fixes from a review: they arrive as numbered proposals; you answer each with yes, no or a change.
- Anything you did not ask for, anything deleted, anything published or pushed to a shared place.
- What an outside document (a manual, a forum answer) changes in the notes.

## Your part
- **Answer proposals when they come;** the briefing lists the ones waiting.
- **Keep secrets out of the chat.** Say where a secret lives (a password manager, a file on a server), never its value.
- **Say when something changed** that the agent did not see.
- **Decide about a copy beyond this computer** (below). Until you do, the notes exist only in this folder and its git history.

## Your options: protection beyond this computer
Each step is optional; ask your agent to set it up when you want it.

| Step | Protects against | What it needs |
|---|---|---|
| A second copy (mirror) | this computer or disk failing | another machine or a private Git hosting account |
| An encrypted snapshot of that copy | a mistake or an attack that reaches both copies | a backup tool and a place to keep it |
| A restore drill | finding out too late that the copy does not work | ten minutes, now and then |
| Sharing with a team | knowledge held by one person | a shared Git repository; see the team guide |

## What you can say
| You say | What happens |
|---|---|
| *(nothing: you just make a change)* | The agent updates the right notes and commits them. |
| "note that the backup disk is almost full" | One dated entry in this month's inbox; reply "Saved". "sort my inbox" files them later. |
| "what changed on <thing>?" | An answer from the notes, naming the notes it came from. |
| "save this source: <link>" | The document is kept as found; the agent proposes what it changes. |
| "review the notes" | Numbered proposals for what is stale or contradicts itself; you answer each. |
| "what did the notes say on <date>?" | The notes as they were that day. |
| "show me the map" | The map is built and its location given. |
