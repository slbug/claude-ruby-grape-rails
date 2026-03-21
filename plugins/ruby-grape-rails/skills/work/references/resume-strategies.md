# Resume Strategies

## How State Works

**Plan checkboxes ARE the state.** No separate JSON state files.

- `[x]` = completed
- `[ ]` = pending
- Phase status `[COMPLETED|IN_PROGRESS|PENDING]` tracks phase progress
- BLOCKERs in progress file track failed tasks

## Resume Modes

### Default: Auto-detect

1. Check explicit active plan marker first:

   ```bash
   active-plan-marker.sh get
   ```

2. If marker exists and points to valid plan with unchecked tasks → resume that plan

3. If no marker or invalid → find most recent plan with unchecked tasks (heuristic)

```
/rb:work  # Uses marker if set, otherwise finds newest plan with work remaining
```

**Active Plan Marker:**

- Set by `/rb:plan` when creating a new plan
- Cleared by `/rb:work` when all tasks complete
- Enables session resume detection

### From Specific Task

```
/rb:work .claude/plans/auth/plan.md --from P2-T3
```

Skips directly to P2-T3 regardless of earlier unchecked tasks.

### Skip Blockers

```
/rb:work .claude/plans/auth/plan.md --skip-blockers
```

Continues past tasks that previously failed with BLOCKER status.

## Resume from Interrupted Session

On resume, the plan file itself shows progress:

```markdown
## Phase 1: Schema Design [COMPLETED]
- [x] [P1-T1][active record] Create users migration
- [x] [P1-T2][active record] Add indexes

## Phase 2: Model Implementation [IN_PROGRESS]
- [x] [P2-T1][direct] Generate model
- [ ] [P2-T2][active record] Add validations     <-- Resumes here
- [ ] [P2-T3][direct] Implement User.register
```

No state file to parse. Just find first `[ ]` and continue.

## Consistency Check

On resume, validate:

- All tasks before the target should be `[x]` in plan
- If earlier tasks are unchecked, warn and ask user:
  - Skip them (mark as done)?
  - Go back and complete them?
  - Something else?

## Idempotent Task Execution

Tasks should be safe to re-execute:

| Task Type | Idempotent Approach |
|-----------|---------------------|
| Migration | Use `change` method or check table existence |
| Model | Write complete class, don't patch |
| Service | Write/replace method entirely |
| Controller | Write complete action |
| Test | Write complete test |
| Route | Check route existence before adding |

If re-executing a task creates duplicate code, the task was not
idempotent. Write whole classes, not patches.
