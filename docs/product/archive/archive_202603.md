
### [STORY-059] Add Prototype Generation Phase to project-design
> Spec: docs/specs/STORY-059.md

- [x] Modify DESIGN_PROMPT in workflows.py, Add Section 1.6, Renumber sections, Update Does NOT section, Add tests

### STORY-060: Fix /project-init Hang — Non-interactive Guard & Scan Limits
- **Priority**: P1
- **Spec**: `docs/specs/STORY-060.md`
- **Tasks**:
  - [x] T1: Rewrite Phase 0.5 playbook text (remove interactive prompt)
  - [x] T2: Wire enterprise flags through cli.py → deploy()
  - [x] T3: Add enterprise flags to upgrade subparser
  - [x] T4: Update deploy() signature (accept flags, remove **_kwargs)
  - [x] T5: Add MAX_SCAN_FILES=500 truncation to _scan_files()
  - [x] T6: Narrow bare except clauses in visualize.py
