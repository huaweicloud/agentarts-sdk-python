# Triage Labels

The skills speak in terms of five canonical triage roles. This file maps those roles to the actual label strings used in this repo's issue tracker.

| Label in mattpocock/skills | Label in our tracker | Meaning                                  |
| -------------------------- | -------------------- | ---------------------------------------- |
| `needs-triage`             | `needs-triage`       | Maintainer needs to evaluate this issue  |
| `needs-info`               | `needs-info`         | Waiting on reporter for more information |
| `ready-for-agent`          | `ready-for-agent`    | Fully specified, ready for an AFK agent  |
| `ready-for-human`          | `ready-for-human`    | Requires human implementation            |
| `wontfix`                  | `wontfix`            | Will not be actioned                     |

When a skill mentions a role (e.g. "apply the AFK-ready triage label"), use the corresponding label string from this table.

Edit the right-hand column to match whatever vocabulary you actually use.

## Notes

- The vocabulary above is the default, kept as-is. All five strings now exist in the `huaweicloud/agentarts-sdk-python` label set (`wontfix` predated this file; the other four were created on 2026-10-12), together with the five `wayfinder:*` labels below.
- The repo also carries `agent/triaged`, which predates this vocabulary and marks "triaged by an agent". It is not one of the five roles; reconcile or retire it separately rather than mapping a role onto it.

### Bootstrap

Already applied on 2026-10-12 — every label below exists, so re-running these commands is only necessary if the tracker is rebuilt or a label is deleted.

```bash
# triage roles (this file)
gh label create needs-triage    --color fbca04 --description "Maintainer needs to evaluate this issue"
gh label create needs-info      --color d4c5f9 --description "Waiting on reporter for more information"
gh label create ready-for-agent --color 0e8a16 --description "Fully specified, ready for an AFK agent"
gh label create ready-for-human --color 1d76db --description "Requires human implementation"
# wontfix already exists — skip

# wayfinding (see issue-tracker.md)
gh label create wayfinder:map       --color 5319e7 --description "Wayfinding map"
gh label create wayfinder:research  --color c5def5 --description "Wayfinding ticket: research"
gh label create wayfinder:prototype --color bfdadc --description "Wayfinding ticket: prototype"
gh label create wayfinder:grilling  --color d93f0b --description "Wayfinding ticket: grilling"
gh label create wayfinder:task      --color 0e8a16 --description "Wayfinding ticket: task"
```
