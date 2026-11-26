# Verification Gates That Can Fail

> A gate that has never been seen red is a hypothesis, not a gate. Every item below is here because
> it caught a real false PASS in a real gate, most of them on the same day.
> A failing item is a blocker; a skipped item needs a written justification.

## 1. Prove the gate can fail, before trusting it to pass

- [ ] A deliberately invalid input is run through the gate in the same test suite, and the gate exits non-zero
- [ ] The invalid input is injected into the **behaviour under test**, not into an assertion about it
      (removing an assertion still passes; breaking the code it checks does not)
- [ ] The gate names what it saw (`FAIL: <subject> <reason>`), not just that something failed

## 2. The gate must judge the subject you named

- [ ] A wrapper that interpolates a path into a shell string quotes it, or passes an argv array
      (unquoted, `--dir "/a /b"` splits into two arguments and the gate validates the wrong one — fail-open)
- [ ] When scanning for an API or a capability, a **known-bogus path is probed alongside the real ones**;
      a single-page app answers 200 to everything, and only the control tells you which 200s are real
- [ ] The subject named in the output equals the subject you passed;
      if the tool prints your input back **as its way of failing**, compare exit code and stderr too,
      because stdout alone cannot distinguish success from an echo
- [ ] Verdicts are decided by the **value**, not by where the value lives:
      a real-format secret under `tests/` is still a secret, and a placeholder under `src/` is still a placeholder

## 3. Read the verdict correctly

- [ ] The exit code is read without a pipe (`cmd | head` returns head's status; `$?` lies)
- [ ] A machine-readable `pass`/`ok` field is derived from the same condition as the exit code —
      a payload that says `pass: true` while exiting 1 is read as green by everything downstream
- [ ] "No data" is not "pass": an empty corpus, a missing file, or a zero-file scan is `unmeasurable` (exit 3), never green

## 4. A fix must not break what already worked

- [ ] After changing a classifier or gate, the **existing fixture the artefact is known by** is re-run and its
      aggregate numbers compared — a bucket moving from 33 to 0 is a different product even if every new test is green
- [ ] If the old behaviour cannot be re-run, it is reported as unverified rather than assumed to have survived

## 5. Ratchets and baselines

- [ ] Every baseline exemption carries a reason and an expiry, and an **approver that is a human**
- [ ] The tool that grants approval refuses to accept an agent identity, defaults to dry-run, and prints each
      entry with its reason before writing
- [ ] Removing an entry from an "unmeasurable" baseline is itself a change to the measurement domain and
      needs the same approval as adding one

## 6. Pre-registered falsifiers

- [ ] The condition that would falsify the claim is written down **before** the measurement, with a date
- [ ] Interim evidence is recorded against that condition without moving the criterion
- [ ] A claim that survives only because the test that would refute it was never built is marked as such
