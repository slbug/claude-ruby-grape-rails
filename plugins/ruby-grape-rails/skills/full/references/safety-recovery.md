# Safety Rails & Recovery

## Resume from Interruption

When resuming an interrupted workflow:

1. **Read progress file** `.claude/plans/{slug}/progress.md`
2. **Check plan checkboxes** in `.claude/plans/{slug}/plan.md`:
   - Count `[x]` (completed) vs `[ ]` (pending) tasks
   - Find the first unchecked task to resume from
3. **Validate artifacts**:
   - Ensure plan and progress files exist
   - Ensure completed tasks match checkboxes in plan
4. **Continue from first unchecked task**

Example resume — invokes `/rb:full --resume magic-link-auth`, which
reads `.claude/plans/magic-link-auth/plan.md`, finds the first
unchecked task (e.g. `P2-T3`), and resumes from there:

```bash
/rb:full --resume magic-link-auth
```

Or resume from specific task:

```bash
/rb:work .claude/plans/magic-link-auth/plan.md --from P2-T3
```

## Ralph Wiggum Integration

For fully autonomous execution, use with Ralph Wiggum Loop:

```bash
/ralph-loop:ralph-loop "/rb:full {feature}" --completion-promise "DONE" --max-iterations 50
```

This enables:

- Automatic recovery from context window limits
- Persistent execution across sessions
- True autonomous completion

## Automatic Stops

The cycle stops automatically when:

1. All tasks complete successfully
2. Max cycles reached
3. Max blockers reached
4. Fatal compilation error (unrecoverable)
5. Test suite completely broken (>50% failing)

## Human Checkpoints

Optional checkpoints for human review:

```
/rb:full {feature} --checkpoint-after plan
/rb:full {feature} --checkpoint-after each-phase
```

## Rollback Points

Git commits after each phase enable rollback. To recover, find the
last good commit via `git log --oneline`, then reset to it:

```bash
git log --oneline
git reset --hard {commit}
```

## Task-Level Checkpoints

Each completed task creates a git commit. Recovery operations:

| Goal | Command |
|---|---|
| View task history | `git log --oneline --grep="wip(${SLUG})"` |
| Revert last task (preserve history) | `git revert HEAD` |
| Revert task before last | `git revert HEAD~2` |
| Reset before last task (destructive) | `git reset --hard HEAD~1` |

## State Recovery

Plan checkboxes ARE the state. If progress file is missing,
the plan still contains all state needed to resume:

Check current progress from plan checkboxes, then resume from the
first unchecked task via `/rb:work`:

```bash
COMPLETED=$(grep -c '\[x\]' .claude/plans/${SLUG}/plan.md)
TOTAL=$(grep -c '\[.*\] \[P' .claude/plans/${SLUG}/plan.md)
echo "Progress: $COMPLETED / $TOTAL tasks complete"

/rb:work .claude/plans/${SLUG}/plan.md
```
