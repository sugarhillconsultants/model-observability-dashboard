# Real Incidents Encountered Setting Up This Project

Same rationale as the other three projects in this portfolio: an honest
account of what actually happened, not a cleaned-up version of events.

## 1. The now-familiar two-step Azure OIDC setup, confirmed as a repeatable pattern

The first real CI run failed immediately at `azure/login@v2`:
`Not all values are present. Ensure 'client-id' and 'tenant-id' are
supplied.` — this repo simply didn't have `AZURE_CLIENT_ID`,
`AZURE_TENANT_ID`, or `AZURE_SUBSCRIPTION_ID` set yet, since GitHub
secrets don't carry over between repositories even when reusing the
same underlying Azure app registration.

Adding those three secrets immediately traded one error for the exact
next one in the sequence: `AADSTS700213: No matching federated
identity record found`. This is the identical root cause diagnosed
twice already in this portfolio (Project 2 and Project 1) — GitHub's
OIDC subject claim includes stable numeric org/repo IDs once a rename
has ever occurred on the account
(`repo:org@<id>/repo@<id>:ref:refs/heads/main`), and a freshly-created
federated credential using the plain, unqualified repo name will never
match. Fixed the same way as both prior times: trigger the workflow
once to read the exact subject GitHub actually presents from the
resulting error, then delete and recreate the federated credential
with that exact string.

**One self-inflicted wrinkle along the way:** the first attempt to
create this repo's federated credential used a placeholder value
(`<REPO_ID>`) copied directly from example instructions, without
substituting in this repo's actual numeric ID first. That credential
was created successfully but was inert — it could never match anything
GitHub would present, since no real repo ID is literally `<REPO_ID>`.
Caught before wasting a full workflow run by checking
`az ad app federated-credential list` output directly and noticing the
literal angle brackets still present in the stored subject string.

**Why this is worth recording explicitly, even though it's not a new
bug:** this is the same two-step sequence (missing secrets, then
subject-mismatch) now confirmed on its *third* separate repository in
this portfolio. That repetition is itself useful data — it confirms
this isn't a one-off fluke tied to something specific about the first
two projects, but a genuine, predictable cost of adding Azure OIDC to
any new repo under an account that has ever been renamed. A team
maintaining multiple repos this way would be well served by a small
setup script that creates both federated credentials in one pass from
a known repo ID, rather than repeating this manual dance a fourth and
fifth time.

## What's still the real, honestly-stated gap

Getting CI to run green here is infrastructure plumbing, not proof the
project's core purpose works. The `check-drift` job still runs against
a hardcoded `psi_score=0.0` placeholder — there is no live feature data
from Project 1 for the drift engine to actually evaluate yet. See
[`docs/architecture.md`](architecture.md) for exactly what's needed to
close that gap. This incident log covers only the CI/OIDC setup working
correctly, which is a real but comparatively small part of what this
project is meant to do.
