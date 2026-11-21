# Host Delegation Checklist

> For harnesses where a sandboxed agent delegates execution to a **host it does
> not control** — the developer's laptop, a build box, a runner. Work through
> this before letting such a path run unattended.
>
> A failing item is a blocker; a skipped item needs a written justification.
>
> Vendor-agnostic: the transport may be a spool directory, a queue, or an RPC
> channel, and the executor may be an agent, a script runner, or a CI job. Every
> item below has been the cause of a real, silent production failure.

## Transport durability

- [ ] The channel survives **both ends disappearing** — sandbox suspended mid-task,
      host rebooted, laptop asleep. A held socket or an in-flight HTTP request does not.
- [ ] A submitted task is durable **before** any work begins, so a crash between
      "accepted" and "started" loses nothing.
- [ ] Requests carry an **idempotency key**. A retry after an ambiguous timeout
      must not run a deploy or a migration twice.
- [ ] Results are written **atomically** (write-temp-then-rename), so a reader never
      sees a half-written result and treats it as complete.
- [ ] The reader is **idempotent**: polling a finished task repeatedly returns the
      same answer, so a caller that crashes mid-wait can resume.

## Staleness — the failure nobody tests

- [ ] Queued work has a **maximum age**, not just a maximum runtime. A host that was
      asleep for six hours must not wake up and execute the whole backlog.
- [ ] Expiry produces a **normal, readable result** (a distinct status), not silence.
      The caller has already given up; it needs to know why.
- [ ] Executing hours-late work is treated as **worse than not executing it** for any
      task with side effects — deploys, pushes, notifications.

## Executor liveness

- [ ] "Registered with the service manager" is **not** treated as "running." Health
      is proven by a **round-trip**, not by presence in a process table.
- [ ] The executor cannot enter a state where the supervisor believes it is alive
      while it serves nothing. Verify by killing it in each way it can actually die.
- [ ] A restart loop that **cannot succeed** is detected as such. A supervisor that
      respawns a job failing on a configuration error will do so forever, silently.
- [ ] Startup failures that occur **before** the runtime initialises still produce a
      diagnosable signal. If the process dies before it can log, the logs are empty
      and every symptom points at the wrong layer.
      *(Concrete case: on macOS 13+, a working directory under `~/Documents`,
      `~/Desktop` or `~/Downloads` is TCC-protected. A shell you type into inherits
      consent so it runs by hand; the service manager has none, cannot `chdir`, and
      kills the job with `EX_CONFIG` before any runtime starts. Empty logs, infinite
      respawn, "registered but dead.")*

## Path and identity agreement

- [ ] The writer and the executor **derive the channel location the same way**. If one
      reads an env var and the other a service definition, they will disagree exactly
      once, in production.
- [ ] A disagreement is reported as a **configuration error naming both paths**, not as
      a timeout. "No result in 30s — is the daemon running?" sends the reader to debug
      a healthy executor.
- [ ] Every copy of the client resolves identically, and a test asserts it. Duplicated
      resolution logic drifts silently.

## Trust envelope

- [ ] The executor runs from an **allowlist** it owns, not arbitrary commands from the
      caller. Path traversal out of that allowlist is rejected after resolution.
- [ ] Authentication uses **constant-time comparison**. A token checked with `==` leaks
      its prefix to a patient caller.
- [ ] The caller can **narrow** its own permissions per task but never widen them past
      the host owner's ceiling.
- [ ] Destructive or costly work passes a **plan-approval gate** the host owner controls,
      and the gate's absence fails **closed or explicitly opt-in** — never silently open.
- [ ] Spend and resource ceilings are enforced **host-side**. A ceiling the caller sets
      is a suggestion.

## Output hygiene

- [ ] Output is **bounded** while streaming, keeping the tail, so one runaway task cannot
      exhaust memory or disk.
- [ ] Truncation is **flagged in the result**; a consumer must be able to tell "no output"
      from "output dropped."
- [ ] Secrets are redacted on the **write path**, covering every artifact — result file,
      progress log, status line. Redacting at read time misses whatever already hit disk.
- [ ] Redaction is documented as **best-effort**. An unrecognised secret shape will pass
      through, and pretending otherwise is worse than saying so.

## Diagnosability

- [ ] A single command reports end-to-end health and **exits non-zero on failure**, so it
      is usable from CI and from a support request.
- [ ] Failure messages name the **cause and the fix**, not the symptom. "Registered but not
      running — try starting it" is useless when starting it cannot work.
- [ ] Every distinct failure mode is **distinguishable from the outside**: rejected before
      execution, timed out, failed to spawn, cancelled, expired. Branch on a stable code,
      never on prose.

---

*Contributed from production experience building a filesystem-mediated host
delegation bridge. Each item above corresponds to a failure that shipped and had
to be diagnosed after the fact — the TCC and path-agreement items in particular
were live for weeks while every surface reported healthy.*
