Challenge post: https://developers.notion.com/guides/mcp/mcp

Running through March 29, the Notion MCP Challenge welcomes you to centralize your workflow with AI-powered docs, projects, and notes. Scale side hustles or empires with "human-in-the-loop" systems that run globally without ever hitting snooze!

Whether you're an engineer, a founder, or someone who just likes to build cool things, this is your chance to show the world what AI-powered workflows can accomplish.

Three winners will each receive:

$500 USD
DEV++ Subscription
Exclusive DEV Winner Badge
All participants with a valid submission will receive a completion badge on their DEV profile.

Notion MCP: https://developers.notion.com/guides/mcp/mcp

Challenge Overview and Rules

The Notion MCP Challenge (Mar 4–29, 2026) invites individuals to “build the most impressive system or process using Notion MCP (Model Context Protocol)”. It’s a solo contest (no teams) open to participants 18+. You must use Notion MCP as a core part of your project, and submit via the official DEV Community template. The submission template provides sections like “What I Built”, “Video Demo”, “Show us the code” and “How I Used Notion MCP”, so plan to cover each of those areas. Key dates: the contest runs Mar 4 – Mar 29 (11:59 PM PST), and winners (3 total) are announced on Apr 9. Prizes are $500 USD each plus DEV++ subscriptions and badges. All participants who submit on time get a DEV badge.

Use the official rules and FAQ as a checklist. For example, multiple submissions are allowed, but if the same person would win twice the judges will give the prize to the other entrant. Your entry must be in English to be prize-eligible (non-English can earn a completion badge only). Riffing on existing open-source code is allowed (even encouraged), but you must significantly extend or customize it and clearly document what’s original. AI tools are permitted too – Notion explicitly allows using AI in your submission (just follow all other rules). Ensure you credit any third-party code or libraries. We also recommend choosing a license for your code (e.g. MIT, Apache) as suggested.

Judging Criteria and Tie‑Breakers
Submissions are judged on Originality/Creativity, Technical Complexity, and Practical Implementation. In practice, this means: (1) pick a creative, unique use-case or integration not seen before; (2) show non-trivial technical work (architecture, API integrations, custom code); and (3) make it a working solution that solves a real problem or automates a realistic workflow. The Notion team specifically said “we want to see your sick integrations” and workflows that “give you superpowers”. In case of a tie, the winner is the entry with the most positive DEV reactions (likes, unicorns, etc.) on their post. So, beyond strong technical content, plan to share your post with colleagues and the community to get support.

Learning from Existing Submissions
Browse the #notionchallenge tag on DEV to see how others have approached the prompt. For instance:

AgentOps (“Control Plane”): One top submission turned Notion into a fleet-control dashboard for 18 AI agents. It used multiple Notion databases (Agent Registry, Task Queue, Run Log, etc.) to coordinate agents, with rich screenshots of the Notion pages (see figure below).
Match You CV: Another used Notion as the single source of truth for resumes. The author built an app that pulls data from a user’s Notion resume page, lets an AI tailor it to a job description, and exports a PDF. This integrated Notion OAuth, a resume editor, AI rewriting, and PDF export.
Weather‑Smart Merchandiser: This project put historical sales and weather data into Notion tables and ran a Python MCP server (an AI tool) to suggest store layout changes based on forecasts. Notion was the “control center,” with databases for sales, categories, and actions. The AI (via Claude) would write layout suggestions back into Notion pages.
Archival Intelligence: A creative use-case for rare-book authentication. The creator used Notion databases to model inventory, bibliography, market history and used an AI agent to spot discrepancies (e.g. tiny printing differences) and write audit logs back into Notion.
FurEver Care AI: A pet-health system where caregivers log daily observations in Notion. An AI (Google Gemini) analyzes the logs for trends or emergencies and generates a vet-ready timeline in Notion.
These examples share some patterns: they all build realistic end-to-end workflows, use Notion as both data storage and output (pages/databases), and leverage Notion MCP to let an AI read/write to the workspace. Many include code links and demos. They also use catchy problem domains (resumes, pets, books, stores, AI agents). From these, note the formats that stand out: use clear section headings (What, Code, How Used), include screenshots or diagrams if possible, and explain step-by-step. For example, [14] includes bullet steps of the workflow, [19] has concise list of how Notion enables the solution, etc.

I Turned Notion Into a Control Plane for my 18 OpenClaw AI Agents - DEV Community
Figure: Example Notion dashboard from a top submission. Notion pages were used as an “AgentOps” control plane, with databases for Agents, Tasks, Logs, etc. (source: Vivek V.’s AgentOps project).