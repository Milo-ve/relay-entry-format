# Step-by-step CLI walkthrough

One task through the whole loop with the `relay` commands: open it, export its context, return a result with evidence, and record a review. It uses the same synthetic pricing scenario as the [demo](../README.md#try-the-synthetic-demo): the demo workspace already contains `inputs/pricing-current.md`. In your own project, point `--select` at your own source.

For the exact behavior of each command, see the [task-layer protocol](RELAY.md). If a command is refused, see [Troubleshooting](TROUBLESHOOTING.md).

```sh
relay start faq --goal "Draft a source-backed pricing FAQ" \
  --accept "Each commercial statement cites the current policy" \
  --select inputs/pricing-current.md --kind draft \
  --owner collaborator --reviewer milo
relay context faq --out faq-context.md
```

Work in your assistant, then save the deliverable and its evidence as separate files:

```sh
relay submit faq --output faq.md --evidence observed-checks.md \
  --checks "Compared each commercial answer with the policy" \
  --questions "Cancellation terms remain unspecified" \
  --next "Milo reviews the draft against the acceptance criteria"
relay show faq
```

Review using the real `submission_id` from that output:

```sh
relay review faq --submission ACTUAL_SUBMISSION_ID --decision accept \
  --actor milo --note "Reviewed this version against the designated source"
```

Task outputs must be separate from selected inputs and control files. This release handles proposal handoffs. Folding an accepted result into a canonical source is a separate action.
