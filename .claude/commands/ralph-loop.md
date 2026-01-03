# Ralph Wiggum Development Loop

## Overview
This command initiates an iterative development loop using the Ralph Wiggum methodology. The AI agent will continuously work on the specified task until completion criteria are met.

## Usage
```
/ralph-loop [task description]
```

## How It Works

1. **Task Definition**: You provide a clear task with completion criteria
2. **Iterative Execution**: The agent works on the task, commits changes, runs tests
3. **Self-Correction**: If tests fail, the agent analyzes errors and fixes them
4. **Completion**: Loop ends when all tests pass and criteria are met

## Best Practices

### Good Task Definitions
- "Implement patient CRUD service with 90% test coverage"
- "Create calendar UI component that passes all visual tests"
- "Build voice intent parser with 95% accuracy on test dataset"

### Always Include
- Clear success criteria
- Specific test commands to run
- Maximum iteration limit

## Development Workflow Integration

When starting any significant feature from `speckit.tasks.md`:

1. Read the task definition and completion criteria
2. Check current state (git log, test results)
3. Implement incrementally
4. Run verification after each change
5. Commit working code
6. Continue until complete

## Spec-Kit Integration

**ALWAYS** reference these documents during development:

| Document | Purpose |
|----------|---------|
| `speckit.constitution.md` | Core principles and constraints |
| `speckit.specify.md` | Feature requirements and acceptance criteria |
| `speckit.plan.md` | Technical architecture and approach |
| `speckit.tasks.md` | Detailed task breakdown with status |

## Example Session

```
User: /ralph-loop Implement appointment booking service

Agent: Starting Ralph loop for appointment booking service.

[Iteration 1]
- Reading specifications from speckit.specify.md
- Creating appointment_service.py
- Writing initial implementation
- Running tests: 3 passed, 2 failed

[Iteration 2]
- Analyzing failures: conflict detection not working
- Fixing conflict detection logic
- Running tests: 4 passed, 1 failed

[Iteration 3]
- Fixing edge case with overlapping slots
- Running tests: 5 passed
- All tests passing, committing changes

Task completed successfully.
```

## Context Window Reset

If context resets during a Ralph loop:

1. This document will remind you of the methodology
2. Check git log for recent commits and progress
3. Run tests to see current state
4. Resume from where you left off
5. Reference speckit.tasks.md for remaining items

## Important Notes

- **Never skip tests**: Always verify after changes
- **Commit frequently**: Each working state should be committed
- **Max iterations**: Default is 50, can be overridden
- **Fail gracefully**: If stuck after 10 iterations on same issue, ask for help

---

*This methodology ensures persistent, self-correcting development regardless of context limitations.*
