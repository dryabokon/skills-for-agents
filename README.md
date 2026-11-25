# skills-for-agents

Skills that let a coding agent (Claude Code, Codex, Cursor, Copilot, Gemini CLI) do the work around the code:
slide decks and diagrams in one consistent style, and answers from Azure DevOps — *why did the build fail,
where is my PR stuck*. The agent **checks its own output before handing it to you**, and every skill
can be run by hand with the same commands.

## What you can ask

> **"Make a 6-slide deck for the steering committee from design-note.md, with an architecture diagram
> that shows what exists today and what is proposed. I also need a PDF to send."**

![Four of the six slides the agent produced](.github/media/story-deck.png)

<sub>Real, unedited output of one Claude Code run on that sentence. Input: [design-note.md](.github/media/design-note.md) ·
result: [the PDF](.github/media/story-deck.pdf).</sub>

You get a single HTML file (open it in any browser, arrow keys to present) and a PDF. Behind the scenes the
agent picked a layout per slide, drew the diagram with a status legend, ran a layout check for overflowing,
clipped or too-small text, looked at a screenshot of every slide, fixed what it found — and told you what
it had to assume (*"the note has no author or date, so the title slide says 'Data platform · November 2026'"*).

> **"Why did the latest failed aspnetcore-helix-matrix build fail? Tell me the root cause and what to fix."**

The agent fetched the latest failed build, read the step that failed *first* and its log, and answered
(shortened and translated from one real run against the public .NET CI):

> **Root cause:** step *Build shared fx* failed NuGet restore with 34 × `NU1603` — projects on `release/11.0`
> reference `Microsoft.Extensions.*` **10.11.1**, which is not on the configured feeds; NuGet resolved 11.0.0
> instead and warnings-as-errors turned that into a failure. *Monitor Helix Jobs* failed only as a consequence
> (0 jobs were submitted). **Fix:** update the versions through the dependency flow (`eng/Versions.props`,
> `darc update-dependencies`) rather than by hand; don't silence NU1603. *I did not open the repository — the
> file and the exact target version are inferred from the log; verify them in code.*

Other requests the skills are built for:

| You say | You get |
|---|---|
| "Turn these meeting notes into 5 slides for Monday" | a deck in the same style as every other deck you make |
| "Draw how an order flows through our services; mark what's confirmed, proposed and still unclear" | an SVG/PNG diagram with a status legend |
| "Make a flowchart of the release process from RELEASE.md" | a Mermaid diagram rendered in the same theme |
| "Restyle the deck in our brand colour #0f766e" | the same deck and diagrams, recoloured from one theme file |
| "Put the architecture diagram on a slide after the problem statement" | the diagram inlined in the deck, still one file |
| "What's the status of my PR?" | votes still missing, failing policies with their builds, open review threads by file |
| "What's assigned to me this sprint?" | your open work items, newest first |
| "Open a PR for feature/x into develop, linked to #1146" | a draft to confirm first — nothing is created until you say so |

## Install

**Claude Code** — one plugin; skills appear as `skills-for-agents:slides`, `…:diagrams`, `…:azure-devops`:

```text
/plugin marketplace add dryabokon/skills-for-agents
/plugin install skills-for-agents@dryabokon
```

**Other agents** read the same `skills/<name>/` folders:

```bash
npx skills add dryabokon/skills-for-agents                                            # Codex, Cursor, ... (.agents/skills/)
gh skill install dryabokon/skills-for-agents slides                                  # GitHub Copilot (gh preview)
gemini skills install https://github.com/dryabokon/skills-for-agents --path skills/slides   # Gemini CLI
```

**Requirements:** Python 3.9+ and a Chromium-based browser (Chrome, Edge, Chromium) — no pip packages.
Mermaid diagrams also need Node.js 18+. No Chrome (Linux, WSL, CI)? One command, no root:
`npx @puppeteer/browsers install chrome-headless-shell@stable --path ~/.cache/puppeteer`.
Services read their settings from environment variables or the nearest `.env` (current folder or any parent).
Copy [.env.example](.env.example) to `.env` — in this repo for the examples, in your own project for daily use;
each skill also documents its variables in its own `.env.example`. `.env` is git-ignored, and `check.py` refuses
anything that looks like a token in files git would commit.

## Skills

| Skill | Does | Details |
|---|---|---|
| **slides** | single-file HTML decks, 16:9, 8 layouts (title, section, bullets, two columns, big numbers, figure, quote, table), PDF export, layout check, screenshots | [SKILL.md](skills/slides/SKILL.md) · [layouts](skills/slides/references/layouts.md) |
| **diagrams** | Mermaid for quick auto-layout, hand-made SVG when layout matters; one theme and status legend (confirmed / proposed / unclear); geometry check | [SKILL.md](skills/diagrams/SKILL.md) · [SVG conventions](skills/diagrams/references/svg-conventions.md) |
| **azure-devops** | PR status (votes, policies, open review threads), why a build failed (first failing step, errors, log tail), work items, wiki, agent pools; prepares PRs but creates one only on confirmation; never merges or approves | [SKILL.md](skills/azure-devops/SKILL.md) · [.env.example](skills/azure-devops/.env.example) |

Your style: colours and fonts are CSS variables. Put `:root { --accent: #0f766e; }` into `.agent-theme.css`
in your project and every deck and diagram the agent makes there follows it.

## See it without an agent

Every skill ships `examples/*.sh` — plain lists of the same commands the agent runs, so you can reproduce
any result by hand:

```bash
git clone https://github.com/dryabokon/skills-for-agents
cd skills-for-agents/skills/slides   && bash examples/build-a-deck.sh    # -> out/streaming.html, .pdf, -shots/
cd ../diagrams && bash examples/svg-and-check.sh                          # -> themed SVG + what the check reports
cd ../diagrams && bash examples/mermaid-flow.sh                           # -> Mermaid flowchart, SVG + PNG
cd ../azure-devops && bash examples/why-did-build-fail.sh                 # -> latest failed build: cause, errors, log tail
```

<details>
<summary>WSL: use the Windows fonts so renders match Windows</summary>

```bash
mkdir -p ~/.config/fontconfig && printf '<?xml version="1.0"?>\n<fontconfig><dir>/mnt/c/Windows/Fonts</dir></fontconfig>\n' > ~/.config/fontconfig/fonts.conf && fc-cache -f
```
</details>

## Contributing

```
skills/<name>/   SKILL.md · scripts/ (one CLI) · assets/ (templates, theme) · references/ · examples/*.sh
.claude-plugin/  plugin + marketplace manifests        .github/  CI and check.py
```

`python .github/check.py` validates the Agent Skills spec rules, that every skill has an example, that files
two skills both carry (`scripts/_browser.py`, `assets/theme.css`) stay identical, secrets, and
`claude plugin validate`. A skill never reaches outside its own folder; no credentials or company-specific
hosts in code.

## License

[MIT](LICENSE)
