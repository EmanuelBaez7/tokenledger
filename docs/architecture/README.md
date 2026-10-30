# Architecture diagram

`tokenledger.architecture.json` is the editable Archify source for the runtime
overview. It preserves the repository revision and relative source references
used to verify the diagram. Internal API modules are logical components, not
independently deployed services.

Keep this JSON and these instructions in Git. Generated HTML and validation
receipts belong under `.archify/`, which is ignored. Receipts may contain local
machine paths and should not be committed.

## Generate the HTML

Requires Node.js and an existing Archify installation. The source was authored
with Archify 3.2.0; Archify is not an application dependency.

Set `ARCHIFY_HOME` in your shell to your local Archify installation directory.
From the repository root, run in PowerShell:

```powershell
$archifyCli = Join-Path $env:ARCHIFY_HOME 'bin/archify.mjs'
node $archifyCli finalize architecture docs/architecture/tokenledger.architecture.json .archify/tokenledger/tokenledger.html --repo-root . --quality showcase --json
```

Open `.archify/tokenledger/tokenledger.html` after all gates pass. When changing
the diagram after a browser check, append a fresh evidence directory such as
`--out-dir .archify/tokenledger/review-2` to the command.

When updating the architecture, inspect the affected code and update the pinned
revision and source ranges together. Do not cite uncommitted changes as evidence
for a committed revision.
