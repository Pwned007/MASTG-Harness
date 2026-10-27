# mastg-harness

**By Syed Sadam Hussain Shah** — [LinkedIn](https://qa.linkedin.com/in/syed-sadam-h-950a62336)

A thin coverage harness for Android pentest engagements. It does **not** replace
MobSF — it drives MobSF's REST API for the static heavy-lifting, then maps the
results onto an OWASP MASTG coverage model and tracks every check (static **and**
manual/dynamic) in one engagement file, exporting a single HTML report.

MobSF stays the engine. This layer adds the thing MobSF doesn't give you: a single
PASS/FAIL/REVIEW/MANUAL coverage view across the whole MASTG, with your dynamic
findings folded into the same report.

### Static sources (run in order, results merged)

1. **MobSF** (`collectors/rules.py`) — manifest, certificate, permissions, trackers,
   and MobSF's own `code_analysis` signatures.
2. **Source pass** (`collectors/source.py` + `source_rules.py`) — decompiles the APK
   with **jadx** and greps the full Java/XML tree for patterns MobSF doesn't cover
   (biometrics, deep links, tapjacking, WebView, raw-SQL, world storage, secrets),
   with `file:line` evidence. Fast, zero extra deps. `--no-source` to skip.
3. **SAST pass** (`collectors/sast.py` + `rules_semgrep/`) — runs **Semgrep with our
   own rules** and **mobsfscan** over the decompiled source. Our rules self-map to KB
   checks via `metadata.check` and include real **dataflow/taint** rules (SQLi, path
   traversal) that regex can't do. `--no-sast` to skip; `mastg sast` to run alone.

   SAST and source engines need external CLIs (install once, outside the venv):
   ```bash
   sudo apt install -y jadx
   pipx install semgrep mobsfscan
   ```
   Everything degrades gracefully: whichever engines are present are used, the rest
   are skipped with a note. Our Semgrep rules are the differentiator — edit/extend
   them in `mastg_harness/rules_semgrep/*.yaml` and validate with
   `semgrep --validate --config mastg_harness/rules_semgrep/`.

Source findings merge with MobSF: the stronger status wins and source evidence is
appended, so e.g. a provider flagged "not protected" by MobSF also gains the exact
`rawQuery` concatenation site from source.

**Code evidence in the report.** Every source finding carries its `file:line` *and
the actual line of code*. The HTML report renders these as a collapsible
"code location(s)" block under each check, so the report points directly at the
vulnerable line (e.g. the `db.rawQuery("... '" + input + "'")` behind a SQLi) rather
than just naming the check. The terminal checklist shows the `file:line` summary;
open the HTML report for the code snippets.

## Setup

Kali / any PEP 668 "externally-managed" distro needs a virtualenv:

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

(If `venv` is missing: `sudo apt install -y python3-full python3-venv`.)

For the source-level pass, `jadx` must be on PATH (`sudo apt install -y jadx`). If it
is absent the tool still runs — it just skips the source checks and uses MobSF only.

### MobSF credentials — the API key is NOT the web login

- `mobsf` / `mobsf` is the **web UI login** (browser). It is not used by this tool.
- The **REST API key** is a long hex string. Find it either:
  - in the browser at `http://127.0.0.1:8000` (after logging in) — home page "api_key"
    field, or the top-right menu -> **API Docs**; or
  - in the terminal where MobSF started — it prints `REST API Key: <hex>` on boot.

Save the key **once** so you never export it again (stored owner-only in
`~/.config/mastg-harness/config.json`):

```bash
./mastg config --apikey <hex key>          # --server too if not the default
```

(You can still override per-run with `--apikey`/`--server`, or `MOBSF_APIKEY`/
`MOBSF_URL` env vars. Resolution order: arg > env > saved config > default.)

### No venv activation — use the wrapper

`./mastg` calls the venv's Python directly, so you don't `source venv/bin/activate`
each session:

```bash
./mastg run target.apk --name acme-android
```

## Workflow

One command does everything (upload + scan + correlate + report):

```bash
python mastg.py run target.apk --name acme-android     # or --apikey <hex> --server <url>
```

The longer form, only needed to re-log dynamic findings without re-uploading:

```bash
python mastg.py init target.apk --name acme-android   # 1. create engagement
python mastg.py scan                                   # 2. upload + scan via MobSF
python mastg.py correlate                              # 3. auto-fill static checks
python mastg.py checklist --phase dynamic --todo       # 4. on-device worklist
python mastg.py set RESILIENCE-ROOT FAIL --note "objection bypass worked"
python mastg.py report -o acme-report.html             # 5. export report
```

State lives in `.mastg-engagement.json` in the working directory — one per target.
Run each target from its own folder.

## Status vocabulary

| Status | Meaning |
|--------|---------|
| `PASS`   | Control verified present/correct |
| `FAIL`   | Issue confirmed |
| `WARN`   | Likely issue, needs attention |
| `REVIEW` | MobSF inconclusive — operator must verify |
| `MANUAL` | No automated signal; dynamic/review phase |
| `TODO`   | Not yet assessed |

Automated correlation **never overwrites a manual verdict** unless you pass
`--force`. Record your dynamic findings with `mastg set` and they survive re-runs.

## MASTG coverage model

Checks live in `mastg_harness/kb/android.yaml` — each has a stable local id, cites
the official `MASTG-BEST-*` refs, maps to a MASVS category, and (for static ones)
names a correlation rule in `collectors/rules.py`. Add or tune checks by editing
the YAML; add a new `auto:` rule by registering a function with `@rule("name")`.

Rules are defensive against MobSF version drift: a missing report field yields
`REVIEW` (verify manually), never a silent `PASS`.

## Layout

```
mastg.py                     entry point
mastg_harness/
  cli.py                     argparse CLI
  kb/android.yaml            MASTG coverage knowledge base
  core/kb.py                 KB loader
  core/engagement.py         engagement state (JSON)
  collectors/mobsf.py        MobSF REST client
  collectors/rules.py        report_json -> check status (MobSF)
  collectors/source.py       jadx decompile + SourceIndex
  collectors/source_rules.py regex source rules -> check status
  collectors/sast.py         Semgrep + mobsfscan runner/normalizer
  rules_semgrep/*.yaml       our own Semgrep rules (self-map to checks)
  report/html.py             HTML coverage report w/ code evidence
```

## Sample report

[`vuln-demo-mastg-report.html`](vuln-demo-mastg-report.html) is a real coverage report
generated against a deliberately-vulnerable demo app, showing the PASS/FAIL/WARN/REVIEW/MANUAL
layout and the code-evidence blocks in practice. Download it and open it in a browser (GitHub
renders HTML as source, not as a page).

## Roadmap

- **FlowDroid taint collector (planned, on-demand).** Deep interprocedural taint for
  when a specific finding needs proof a flow is reachable. Heavier: needs a JRE, the
  FlowDroid jar, and android-platforms; slow; XML flow output. Designed as a per-check
  `mastg taint <CHECK-ID>` action rather than part of the default run.
- Dynamic collectors: Frida/objection script runners, logcat capture, proxy evidence
- iOS profile (`kb/ios.yaml`)

## License

MIT — see [LICENSE](LICENSE). Contributions and issues welcome.
