# Attribution

This implementation was developed from the project's own OKF + ICM design.
It is inspired by two independent upstream projects:

- [Interpretable Context Methodology](https://github.com/RinDig/Interpretable-Context-Methodology),
  created by Jake Van Clief: staged Markdown workflows, scoped context and editable handoffs.
- [Open Knowledge Format](https://github.com/GoogleCloudPlatform/open-knowledge-format),
  GoogleCloudPlatform: portable knowledge concepts and their metadata conventions.

The executable CLI and its packet/run protocol are original to this project.
The default stage wording is independently authored. No upstream reference-agent
implementation is bundled. Upstream names identify inspiration and compatibility
targets; they do not imply endorsement.

Runtime dependency: [PyYAML](https://pyyaml.org/). It is installed separately;
its license and notices remain applicable to that dependency.

The original CLI and methodology were developed in the local OKF + ICM proposal.
Relay Method adds adaptive-effort recommendations and a lightweight task/review
layer. This repository does not bundle the historical v0.1 scaffold and does not
claim to be an official branch of either upstream methodology. The optional Jev
adapter uses TypeSafe's documented HTTP API; no proprietary model is bundled.
