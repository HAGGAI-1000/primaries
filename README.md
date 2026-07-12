# Primaries Candidate Selector

An AI assistant that helps you choose who to vote for in party primaries, by matching your priorities against the candidates' own published materials. Currently covers the Democrats party (מפלגת הדמוקרטים) primaries on 20.7.2026; other parties may be added as their candidate lists are published. There is no application code — the flow is defined in `AGENTS.md` and runs inside an AI assistant, which guides you through a short questionnaire (in Hebrew) and matches your priorities against the candidates' published materials.

## Using via a chat website (Claude / ChatGPT / Gemini)

Copy this single prompt into a new conversation (web browsing must be
enabled):

```
Fetch https://haggai-1000.github.io/primaries/AGENTS.md and follow the instructions in it. If that fails, fetch https://github.com/HAGGAI-1000/primaries/blob/main/AGENTS.md instead.
```

That's it — the assistant fetches everything it needs from this
repository and opens the questionnaire in Hebrew.

If the assistant reports it cannot retrieve the data (no web browsing on
your plan, or fetching blocked), try a different chat platform, or use a
coding agent as described below.

Notes:
- The conversation is processed by whichever LLM provider you choose;
  their data-retention policies apply. Avoid sharing identifying
  personal details.

## Using via a coding agent (Claude Code / Copilot CLI / Codex)

1. Clone this repository.
2. Open your agent in the repository folder.
3. The instructions load automatically (`AGENTS.md`, imported by
   `CLAUDE.md` for Claude Code). Just start the session — the assistant
   opens the questionnaire in Hebrew.

## Repository layout

- `AGENTS.md` — the full questionnaire and matching flow (the "program")
- `CLAUDE.md` — one-line import of AGENTS.md, for Claude Code
- `data/primaries_criteria.json` — selection-criteria topics and items
- `data/ideology.json` — ideological positions (paired opposing stances)
- `data/candidates1.json`, `data/candidates2.json`, `data/candidates3.json` — candidate bios, resumes, and links, split
  into 3 parts so each can be fetched whole by chat assistants
- `scripts/` — data collection and maintenance scripts

## Disclaimer

This tool ranks candidates only by how well their own published materials
match the criteria you select. A low rank may reflect missing information
rather than an actual mismatch. It never recommends who to vote for —
review the leading candidates' own pages before voting. The choice is
yours.
