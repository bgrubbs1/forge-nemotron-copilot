# RULES-NOTES — verified requirements, quotes, and UNVERIFIED items

All rules text below was fetched on **2026-10-27** with
`curl -sL https://nebiusglobalaihackathon.devpost.com/rules` (stored/parsed locally;
the page returned HTTP 200, 170 KB of HTML). Quotes are verbatim from the Official
Rules. Nebius endpoint/model facts were read from Nebius's own page.

Sources:

1. Rules: <https://nebiusglobalaihackathon.devpost.com/rules>
2. Event page: <https://nebiusglobalaihackathon.devpost.com/>
3. Nebius Token Factory × Nemotron (endpoint + model id): <https://nebius.com/services/token-factory/nemotron>

---

## 1. Deadline (converted)

> "Submission Period: Wednesday, August 26, 2026 (9:00 am Pacific Time) – Friday,
> October 30, 2026 (10:00 am Pacific Time) (“Submission Period”)."

**10:00 PDT on Fri 2026-10-30 = 13:00 EDT (1:00 pm ET) Fri 2026-10-30.** Treat 12:30 pm ET
as the real cutoff for a submitted Devpost entry (uploads/validation take time).
Judging: Dec 1–15, 2026. Winners announced on or around Jan 11, 2027.

## 2. What must be built

> "Entrants must create a working software application that runs on either Nebius Token
> Factory or Nebius AI Cloud and uses at least one NVIDIA open source model, and that fits
> into one of the four hackathon tracks below (each a “Project”)."

> "“Runs on Nebius Token Factory or Nebius AI Cloud” means the project makes a runtime
> call to the Token Factory inference API, or is deployed/run using Nebius AI Cloud compute
> (Serverless Jobs, Serverless Endpoints, or DevPods)."

→ Our app makes a **runtime call** to the Token Factory inference API
(`POST {NEBIUS_BASE_URL}/chat/completions`) in real mode.

> **Coding and Agentic Engineering Track** — "Build coding agents and developer tools:
> agents that write, run, and test code in Token Factory."

→ This is the track. Forge writes, runs and tests code in a sandbox with the model served
by Token Factory. (Other tracks: Best Apps and Agents; Personal AI; Physical AI.)

> "New & Existing: Projects must be either newly created by the Entrant or, if the
> Entrant's Project existed prior to the Hackathon Submission Period, must have been
> significantly updated after the start of the Hackathon Submission Period."

→ Forge was created 2026-10-27, inside the Submission Period (Aug 26 – Oct 30, 2026).
It is new; no prior-work explanation is needed.

## 3. Submission requirements (verbatim, condensed)

> "Provide a URL to a working demo, hosted application, or test build of your Project
> (not required for Physical AI submissions, which are evaluated per the hardware-access
> provision below)."

> "Include a text description that should explain the features and functionality of your
> Project."

> "Provide a URL to your public code repository for judging and testing on either GitHub,
> GitLab or Bitbucket."

> "The repository must contain all necessary source code, assets, and instructions
> required for the project to be functional."

> "The repository must be public and open source by including an open source license file
> (such as Apache 2.0, MIT, or MPL 2.0). This license should be detectable and visible at
> the top of the repository page (in the About section)."

> "Include a README with setup instructions and clear guidance for running your project."

> "Make sure to highlight how you've used NVIDIA Nemotron or other NVIDIA open source
> models and where Token Factory accelerated your workflow and any other Nebius Tools or
> Services used."

> "Include a demonstration video of your Project. The video portion of the Submission:
> should be less than three (3) minutes. Judges are not required to watch beyond three
> minutes … should include footage that shows the Project functioning on the device for
> which it was built … must be uploaded to and made publicly visible on YouTube and a
> link to the video must be provided on the submission form on the Hackathon Website …
> and must not include third party trademarks, or copyrighted music or other material
> unless the Entrant has permission to use such material."

> "Identify which track you are submitting your Project into."

> "Provide feedback on Nebius Token Factory, AI Cloud and any NVIDIA tools, models, or
> technologies used."

Practical consequences for the entrant (see `SUBMISSION.md` checklist):
- GitHub repo must be **public**, **MIT license visible in the About section**, README
  present, and the demo link + YouTube link must be on the Devpost form.
- Video must be **on YouTube, public, < 3:00**; no third-party trademarks (avoid showing
  other companies' logos) and no copyrighted music. Screen recording + own voice only.

## 4. Judging criteria (equally weighted)

> "**Technological Implementation:** How well is the project built, and how effectively
> does it use Nebius Token Factory or AI Cloud model(s), and NVIDIA Nemotron or other
> NVIDIA open source models as part of the solution?"

> "**Design:** Does the project deliver a complete, coherent product experience not just a
> technical proof of concept?"

> "**Potential Impact:** Does the project make a credible, specific case for solving a real
> problem for a real audience and does the solution actually address it based on what's
> demonstrated?"

> "**Quality of the Idea:** Is this a creative, non-obvious use of Nebius Token Factory or
> AI Cloud model(s) … and does the team show genuine understanding of the problem space?"

Stage One is a pass/fail viability screen: "A Project reasonably fits the theme if it is a
genuine attempt at the track's stated goal, not a superficial rebrand of an unrelated idea."

## 5. Prizes (relevant lines)

> Grand Prize $20,000 USD ×1; 2nd Place $10,000 ×1; 3rd Place $6,000 ×1
> "Coding and Agentic Engineering Track Winner — NVIDIA Jetson Orin Nano ×1"
> "Best Use of Tavily — $3,000 USD ×1 … that make a functional, runtime call to the Tavily API"
> "Most Valuable Feedback — $100 USD + NVIDIA swag pack ×10"
> "Each Project is eligible for one (1) Overall Award OR one (1) Track Award and one (1)
> Bonus Award."

→ Forge is eligible for the overall awards + the Coding/Agentic track award. The
**Most Valuable Feedback** ($100 + swag) requires only a feedback submission — free
upside; draft included in `SUBMISSION.md`. Tavily is *not* integrated (would be a new
dependency), so that bonus does not apply.

## 6. Eligibility

> "The Hackathon IS open to: Individuals who are at least the age of majority where they
> reside as of the time of entry … Teams … Organizations …"
> Not open to residents of comprehensively sanctioned countries (Brazil, Quebec, Russia,
> Crimea, Cuba, Iran, North Korea listed).
> Fee: "NO PURCHASE OR PAYMENT NECESSARY TO ENTER OR WIN."

→ US-based individual entrant is eligible. Winner forms: W-9 for US residents.

## 7. Nebius platform facts — VERIFIED from Nebius's own page

From <https://nebius.com/services/token-factory/nemotron> (fetched 2026-10-27), verbatim
code sample on the page:

```python
client = OpenAI(
    base_url="https://api.tokenfactory.us-central1.nebius.com/v1/",
    api_key=os.environ.get("NEBIUS_API_KEY"))
response = client.chat.completions.create(
    model="nvidia/nemotron-3-super-120b-a12b", messages=[...])
```

Also stated on that page, verbatim fragments:

> "Nemotron 3 Nano 30b — Compact MoE model optimized for efficient reasoning, chat, and
> coding with strong multilingual support and long-context RAG/agent workflows."
> "Nemotron 3 Super 120b — Hybrid MoE model optimized for efficient multi-agent AI and
> complex reasoning tasks."
> "Nemotron 3 Ultra 550b — Frontier hybrid MoE model optimized for long-running autonomous
> agents, deep research, and high-throughput workflows."

So: the endpoint **is OpenAI-compatible** (`/v1/chat/completions`), the key env var is
`NEBIUS_API_KEY`, and `nvidia/nemotron-3-super-120b-a12b` is a real, documented model id.
This is why the app is stdlib-only `urllib` — no SDK needed.

## 8. UNVERIFIED items (do not state these as facts)

| Item | Status | How the entrant can confirm |
| --- | --- | --- |
| Exact model ids for Nemotron 3 **Nano** / **Ultra** (`nvidia/nemotron-3-nano-30b-a3b`, `nvidia/nemotron-3-ultra-550b`) | UNVERIFIED — guesses from naming pattern | `python3 -m forge --models --real` lists live ids |
| Whether `https://api.tokenfactory.nebius.com/v1` (without region) also serves the same API | UNVERIFIED — community sources say yes; official sample uses the `us-central1` host | try both; the `us-central1` host is the one Nebius documents |
| Free-credit amount / whether a payment method or card is required to create a Nebius account or get an API key | UNVERIFIED — not on the rules page; may depend on promotion | create the account early (Day-1 step in the checklist) |
| Whether judges will run the app themselves | Rules: "Judges are not required to test the Project" | assume video is decisive |
| Tavily bonus eligibility | Requires a "functional, runtime call to the Tavily API" — not implemented | intentionally skipped |

## 9. Things a third party (the assistant) must NOT do

Per the task constraints and common sense: no account creation, no registration, no
submission, no organizer contact, no personal data (email, phone, tax info, payment) ever
handled. Everything in this repo is content the entrant reviews and submits themselves.
