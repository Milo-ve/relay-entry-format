# Independent held-out navigation fixture

Morrowglass Kilnworks is an entirely fictional ceramics manufacturer. Every
organization, role, address, measurement, product and procedure here is synthetic.
The procedures are evaluation text, not instructions for operating real equipment.
This fixture was written by a Codex session identified as GPT-6 that had not seen
the method design. It has not been reviewed by a human.

The goals-only commit is `baedd8f`. Its tree contains only `goals.json` under this
fixture. No held-out knowledge file existed when that commit was made. The entire
goals file has remained byte-identical since that commit. If an inconsistency is
found, correct the knowledge base rather than changing the expected sets.

There are 20 goals: 17 source-backed goals and three gaps:

- `h15-extraction-capacity`: the proposed third booth has no filed engineering
  requirements; its calculation link is unresolved.
- `h16-opalveil-ratios`: the only formulation records are denied.
- `h18-food-contact-certificate`: no jurisdiction-specific certificate is filed.

`h07-crate-pool-contact` requires the sole recorded source with an explicit stale
warning. A recorded old assignment is not proof that it remains current.

There are 46 valid readable concepts, including two under the denied folder,
leaving 44 permitted concepts. One additional Markdown file has valid concept
front matter but a deliberately sensitive `.env`-prefixed filename. It contains
only an invented display preference, with no secret or credential. The normal
reader excludes it. Reserved `index.md` files are not concepts.

The corpus includes superseded, stale, draft and unverified records, ambiguous
names, one untrusted instruction injection, and a fieldbook hub linked from every
other concept. The generated index snapshot predates the measurement manual and
the Vela drawing, so their folder indexes omit them intentionally. Do not refresh
the indexes as part of evaluation preparation.

## Reference access and format decisions

The reference fixture and baseline script were absent from this checkout. Only
the permitted reference material was read from this worktree's local Git history:
the fixture at `c782ee3` and `examples/navigation_baselines.py` at `30ab651`.
One concept's front matter was examined; its body was not read. No other worktree
or method design was consulted. No baseline or method was executed.

- The reference `config.json` does not contain `deny_paths`. Those rules live in
  `context/relay/settings.json`; this fixture follows that actual location.
- Section expectations use lowercase heading slugs. Runtime section selection
  uses the original heading text. Validation resolves each slug to its exact
  `##` heading before calling the existing section extractor.
- The original acceptance metadata says it was declared before any method
  existed. That historical claim cannot be made for this second fixture. Its
  `declared_before_any_navigator_exists` value is therefore false, with an explicit
  declaration scope. The acceptance criteria, metric definitions and baseline
  definitions are preserved from the reference; metrics and baselines compare
  equal in their entirety.
- `verified` events model synthetic machine-confirmed metadata signals, not
  human review, real operational verification, organizational authorization or
  product acceptance. Intentionally unverified concepts omit those events.

## Validation at creation

The original fixture check is hardcoded to its path, exact concept count and
specific traps; it has no alternate-path argument. It was inspected but not
modified or run against this fixture. Direct read-only checks used the existing
knowledge parser, metadata validator, bundle inspector, settings matcher, bounded
path reader and section extractor. They established:

- All 47 concept-shaped files parse and validate directly; the bundle inspector
  reports 46 concepts and exactly the intentional sensitive-path exclusion.
- All expected IDs exist, all 19 expected section references resolve, and no
  expected source is denied or sensitive. Only the declared `must_warn` source
  is hazardous among expected sources.
- The bundle has all required lifecycle/trust/freshness traps, exactly one
  unresolved local link, a hub link from each other concept, and two concepts
  omitted from their generated indexes.
- The complete frozen goals file is byte-identical to commit `baedd8f`, and the
  reference metric and baseline objects are unchanged.

The existing repository suite was run with:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -v
```

All 240 tests passed with loopback networking enabled. The initial sandboxed run
had 13 socket-bind permission errors in existing HTTP tests. `python3` was used
because no `python` executable was available. The existing suite does not
automatically discover this data fixture; the direct checks above cover it.
These checks are fixture validation, not evidence of method quality or savings.
