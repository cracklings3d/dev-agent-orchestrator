# Controller Worked Examples

## Purpose

This document shows realistic routing cases for the Controller role.

The goal is not to provide exhaustive coverage. The goal is to make the routing policy concrete, show when the Controller should forward an upstream packet unchanged versus synthesize a new rework packet, and expose ambiguity in the contract before platform-portability work begins.

## Reading Guide

Each scenario includes:

1. the upstream packet or report the Controller receives
2. the expected `controller_decision_report`
3. the routing rationale

## Scenario 1: Architect Actionable Packet -> Developer

### Upstream Input

```md
## Packet
- packet_type: architect_task_packet
- source_role: Architect
- target_role: Developer
- blocker_status: none

## Task Summary
Add a `--dry-run` flag to the multi-platform installer so users can preview what would be installed without writing any files.

## Required Outcome
- `python install.py /tmp/test-repo --dry-run` prints the list of files that would be created without creating them

## In Scope
- `integration_layer/installer.py`
- `install.py`

## Out Of Scope
- changes to the GitHub Copilot wrapper script
- changes to quickstart content
- changes to platform rendering logic

## Acceptance Criteria
- --dry-run prints each target path to stdout
- no files are created in the target directory when --dry-run is active
- the exit code is 0
- a test covers the dry-run path

## Constraints
- keep the change surface small: only the installer core and the CLI entry point
- do not change the Copilot-only wrapper

## Required References
- `integration_layer/installer.py`
- `install.py`
```

### Expected Controller Output

```md
## Report
- packet_type: controller_decision_report
- source_role: Controller
- upstream_source_role: Architect
- upstream_packet_type: architect_task_packet
- target_role: Developer
- blocker_status: none

## Task Summary
Add --dry-run flag to multi-platform installer

## Decision
- route_to_developer

## Decision Reason
- Architect produced an actionable task packet with clear scope, acceptance criteria, and no blockers
- the target_role in the upstream packet is Developer
- the packet can be forwarded without reshaping

## Packet Action
- forward_existing_packet

## Next Packet Type
- architect_task_packet

## Next Packet Summary
- forwarding the Architect packet unchanged to Developer for implementation
```

### Why This Route Is Correct

The Architect packet is complete: it has a clear task summary, bounded scope, concrete acceptance criteria, and no blockers. The Controller does not need to modify or re-interpret anything. The correct action is `forward_existing_packet` because the upstream packet is already the right shape for Developer to consume.

---

## Scenario 2: Tester Fail -> Developer (Rework)

### Upstream Input

```md
## Report
- packet_type: tester_validation_report
- source_role: Tester
- target_role: Developer
- blocker_status: none

## Task Summary
Validate --dry-run flag on multi-platform installer

## Overall Status
- fail

## Acceptance Criteria Results
- "--dry-run prints each target path to stdout": fail -- paths are printed but the manifest file is still written
- "no files are created in the target directory when --dry-run is active": fail -- MULTI_PLATFORM_INTEGRATION_MANIFEST.json is created even with --dry-run
- "exit code is 0": pass
- "a test covers the dry-run path": pass

## Validation Commands
- `python install.py /tmp/dry-run-test --dry-run` -> exit code 0, but /tmp/dry-run-test/MULTI_PLATFORM_INTEGRATION_MANIFEST.json exists

## Failure Findings
- the manifest file is written unconditionally in `install_platforms()` after all platform installs complete
- the --dry-run check in `_write_text` and `_copy_file` correctly skips file creation, but the manifest write at the end bypasses the dry-run guard
- root cause: the manifest write call in `install_platforms()` is outside the dry-run conditional path

## Regression Concerns
- none -- the fix is localized to the manifest write call
```

### Expected Controller Output

```md
## Report
- packet_type: controller_decision_report
- source_role: Controller
- upstream_source_role: Tester
- upstream_packet_type: tester_validation_report
- target_role: Developer
- blocker_status: none

## Task Summary
Fix --dry-run flag: manifest file is still written despite dry-run mode

## Decision
- route_to_developer

## Decision Reason
- Tester found a specific, localized failure with a clear root cause
- the scope is the same as the original task -- this is a fix, not a reshape
- the finding is actionable without Architect involvement

## Packet Action
- synthesize_rework_packet

## Next Packet Type
- rework_packet

## Next Packet Summary
- fix the manifest write in install_platforms() so it respects --dry-run mode

## Required Outcome
- no files are written to the target directory when --dry-run is active, including the manifest

## In Scope
- `integration_layer/installer.py` (the manifest write call near the end of install_platforms)

## Out Of Scope
- platform rendering logic
- quickstart content
- the CLI entry point

## Rework Context
- Tester found that MULTI_PLATFORM_INTEGRATION_MANIFEST.json is written even with --dry-run
- root cause: the manifest write at the end of install_platforms() bypasses the dry-run guard
- acceptance criteria that failed: "no files are created in the target directory when --dry-run is active"
- existing tests for --dry-run already pass for individual file writes; the gap is the manifest write

## Required References
- `integration_layer/installer.py`
```

### Why This Route Is Correct

The Tester found a specific defect with a clear root cause. The fix is bounded: one code path in one function. There is no ambiguity about what went wrong or where to fix it. The Controller synthesizes a compact rework packet that carries only the distilled finding and the narrowed scope, rather than forwarding the full Tester report plus the original Architect packet plus the Developer report.

---

## Scenario 3: Reviewer Rework -> Developer (Rework)

### Upstream Input

```md
## Report
- packet_type: reviewer_review_report
- source_role: Reviewer
- target_role: Developer
- blocker_status: none

## Task Summary
Review --dry-run flag implementation in multi-platform installer

## Overall Status
- rework

## Findings Ordered By Severity
- the dry-run parameter is threaded through every function signature as a boolean argument, creating a wide change surface in the internal API. Consider moving dry-run behavior into a single write-dispatching helper so each call site does not need to know about dry-run mode.

## Maintainability And Structural Concerns
- `_write_text`, `_copy_file`, and the manifest write each independently check dry-run. If a fourth write path is added later, the author must remember to add the check. A single write-or-skip dispatcher would be more resilient.

## Scope Drift Concerns
- none -- the implementation stays inside the stated scope

## Rework Context
- restructure the write dispatching so dry-run logic lives in one place rather than being scattered across multiple functions
```

### Expected Controller Output

```md
## Report
- packet_type: controller_decision_report
- source_role: Controller
- upstream_source_role: Reviewer
- upstream_packet_type: reviewer_review_report
- target_role: Developer
- blocker_status: none

## Task Summary
Refactor dry-run logic into a single write-dispatching helper

## Decision
- route_to_developer

## Decision Reason
- Reviewer found a maintainability concern that is actionable and bounded
- the rework is structural, not a task reshape
- Developer can address it without Architect involvement

## Packet Action
- synthesize_rework_packet

## Next Packet Type
- rework_packet

## Next Packet Summary
- extract the dry-run check into a single write dispatcher to reduce scattered conditionals

## Required Outcome
- dry-run logic lives in one helper function instead of being repeated in _write_text, _copy_file, and the manifest write
- all existing tests still pass
- a new test verifies the dispatcher behavior

## In Scope
- `integration_layer/installer.py` (internal write helpers)

## Out Of Scope
- public API changes to install_platforms()
- changes to CLI entry points
- changes to platform rendering logic

## Rework Context
- Reviewer found that dry-run checks are scattered across _write_text, _copy_file, and the manifest write call
- concern: if a new write path is added, the author must remember to add a dry-run check there too
- suggestion: extract a single write-or-skip dispatcher that all write paths use

## Required References
- `integration_layer/installer.py`
```

### Why This Route Is Correct

The Reviewer found a maintainability issue, not a functional defect. The fix is bounded to the internal API of one module. The Controller correctly routes this to Developer as rework, and synthesizes a compact packet that captures the distilled finding rather than forwarding the full Reviewer report.

---

## Scenario 4A: Tester Blocked -> Architect (Reshaping)

### Upstream Input

```md
## Report
- packet_type: tester_validation_report
- source_role: Tester
- target_role: Architect
- blocker_status: role-blocked

## Task Summary
Validate installer --platform flag behavior

## Overall Status
- blocked

## Acceptance Criteria Results
- "--platform accepts copilot-vscode, qwen-code, claude-code, glm, or all": pass
- "invalid platform name raises a clear error message": blocked -- the packet does not specify what "clear error message" means. Should it list valid platforms? Should it include the invalid input in the message? Should it exit with code 1 or 2?

## Validation Commands
- `python install.py /tmp/test --platform nonexistent` -> raises ValueError with message "Unsupported platform: nonexistent"
- packet acceptance criteria say "clear error message" but do not define the expected message format or exit code

## Failure Findings
- none -- the code works, but the acceptance criteria are too vague to validate definitively

## Regression Concerns
- none
```

### Expected Controller Output

```md
## Report
- packet_type: controller_decision_report
- source_role: Controller
- upstream_source_role: Tester
- upstream_packet_type: tester_validation_report
- target_role: Architect
- blocker_status: none

## Task Summary
Tester blocked on vague acceptance criteria for error message behavior

## Decision
- route_to_architect

## Decision Reason
- Tester is blocked because the acceptance criteria are underspecified
- the issue is about task shaping, not a code defect
- Architect needs to clarify what "clear error message" means before testing can complete

## Packet Action
- return_for_reshaping

## Next Packet Type
- architect_task_packet

## Next Packet Summary
- reshape the acceptance criteria for error message validation to specify: message format, whether valid platforms should be listed, and expected exit code

## Required References
- `integration_layer/installer.py`
- `install.py`
```

### Why This Route Is Correct

The Tester did not find a bug. The Tester found that the acceptance criteria are too vague to validate. This is a task-shaping problem, not a code problem. The correct route is back to Architect so the acceptance criteria can be tightened. The Controller does not try to resolve the ambiguity itself -- it escalates to the role responsible for clarification.

---

## Scenario 4B: Architect Blocked -> Human (Escalation)

### Upstream Input (from Architect after reshaping attempt)

```md
## Packet
- packet_type: architect_task_packet
- source_role: Architect
- target_role: Developer
- blocker_status: human-required

## Task Summary
Improve error message clarity for invalid platform names in the installer CLI

## Required Outcome
- when an unsupported platform name is provided, the CLI prints a helpful error message

## In Scope
- `install.py`

## Out Of Scope
- changes to the installer core logic

## Acceptance Criteria
- invalid platform name produces a clear error message
- exit code is non-zero

## Constraints
- <unresolved: the Architect cannot determine from repo context whether the error message should list all supported platforms or just state that the input is invalid. The previous behavior raises a Python ValueError which is not user-friendly. The desired UX depends on user preference.>

## Required References
- `install.py`

## Notes
- BLOCKED: cannot resolve whether the error message should enumerate valid platforms or remain generic. This is a UX decision that requires human input.
```

### Expected Controller Output

```md
## Report
- packet_type: controller_decision_report
- source_role: Controller
- upstream_source_role: Architect
- upstream_packet_type: architect_task_packet
- target_role: Human
- blocker_status: human-required

## Task Summary
Architect blocked on UX decision for error message format

## Decision
- route_to_human

## Decision Reason
- Architect attempted to reshape the task but could not resolve the ambiguity from repo context alone
- the blocker is a genuine UX preference question, not something the Architect can safely assume
- per escalation policy: escalate to Human only when Architect cannot safely resolve the blocker

## Packet Action
- escalate_to_human

## Next Packet Type
- none

## Next Packet Summary
- waiting for human decision on error message format

## Notes
- the Architect needs the human to decide: should the error message list all supported platforms (copilot-vscode, qwen-code, claude-code, glm) or just state "unsupported platform"?
- once resolved, the Architect can finalize the task packet and the loop resumes
```

### Why This Route Is Correct

The Architect attempted to resolve the ambiguity but correctly identified that the error message format is a UX preference, not something derivable from repository context. The Controller correctly routes this to Human because the escalation policy says "escalate to Human only if Architect cannot safely resolve the blocker." The Architect already tried and could not. This is the correct terminal state until Human provides input.

---

## Scenario 5: Reviewer Approve -> Complete

### Upstream Input

```md
## Report
- packet_type: reviewer_review_report
- source_role: Reviewer
- target_role: Complete
- blocker_status: none

## Task Summary
Review --dry-run flag implementation after rework

## Overall Status
- approve

## Findings Ordered By Severity
- none

## Maintainability And Structural Concerns
- none -- the write dispatcher is clean and the dry-run path is well-isolated

## Scope Drift Concerns
- none -- implementation stays inside stated scope

## Rework Context
- n/a
```

### Expected Controller Output

```md
## Report
- packet_type: controller_decision_report
- source_role: Controller
- upstream_source_role: Reviewer
- upstream_packet_type: reviewer_review_report
- target_role: Complete
- blocker_status: none

## Task Summary
--dry-run flag for multi-platform installer

## Decision
- complete

## Decision Reason
- Reviewer approved with no findings, no maintainability concerns, and no scope drift
- Tester previously passed all acceptance criteria
- the task has completed the full loop: Architect -> Developer -> Tester -> Reviewer

## Packet Action
- terminate_complete

## Next Packet Type
- none

## Next Packet Summary
- task complete
```

### Why This Route Is Correct

Both Tester and Reviewer have approved the implementation. There are no open findings, no rework requests, and no blockers. The task has traversed the complete loop successfully. The Controller correctly terminates the task.

---

## Ambiguities Exposed By These Examples

1. **Rework count tracking**: the rework packet does not currently carry a retry counter. If the same defect bounces between Tester and Developer multiple times, the Controller has no way to detect a stuck loop. A `retry_count` field or a `max_retries` policy may be needed.

2. **Complete exit behavior**: when the Controller emits `terminate_complete`, there is no specification for what happens next. Should the Controller produce a final summary? Should the completed packet be archived? This is deferred until a minimal runtime exists.

3. **Partial-pass Tester results**: Scenario 2 shows a clean fail where all criteria are binary. In practice, some criteria may partially pass. The Tester report format supports this, but the Controller routing policy does not yet specify how to handle "3 of 4 criteria pass, 1 is ambiguous."

4. **Reviewer blocked -> Architect**: none of these scenarios cover the case where the Reviewer is blocked (e.g., reviewing code that seems to solve a different problem than the packet described). This would route to Architect for reshaping, similar to Scenario 4A but from the Reviewer.
