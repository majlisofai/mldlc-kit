# Adopting mldlc in a project

## A new project

```bash
mldlc init --hooks --skills        # mldlc.yaml, lifecycle/, mldlc_hooks.py, .claude/skills
# edit mldlc.yaml: experiment and model names, how the data is versioned, your commands
# add `mlruns/` (and any local database) to .gitignore
mldlc status
```

Then, in Claude Code, `/mldlc`. Without it: fill `lifecycle/intent.md`, run `mldlc check G0`, get a person to
`mldlc approve G0 --by "<name>"`, and continue down the gates. Add the ten lines from the README to your
validation and training scripts.

## An existing project

You can adopt it at any stage. Write the intent and the spec for the model you already have (the skills help),
connect the training script, retrain once from committed code, and walk the gates. The spec's inputs must
match what the code really uses, which is often the first useful discovery.

## A monorepo with several models

Give each model its own folder with an `mldlc.yaml`, and run the command with `-C`:

```bash
mldlc -C models/churn status
mldlc -C models/fraud status --require G1
```

Teams that must not touch each other's models can own their folder with CODEOWNERS. Keep shared training code
outside `code_paths`, or add it to the paths of every project that uses it so its changes mark runs dirty.

## CI

`mldlc status --require G1,G2` exits 1 unless those gates are valid, so a pipeline can refuse to train a model
whose spec is not approved, or to deploy one whose data gate is stale. A GitLab example is in
`examples/ci/gitlab-ci.yml`.

CI needs access to the MLflow store (`MLFLOW_TRACKING_URI`) and to the repository, where `gates.yaml` and the
documents live.

## Where the skills come from

Two ways, and you can use both:

| Way | When | Updates |
|---|---|---|
| the plugin (`claude plugin install mldlc@mldlc-kit`) | many projects, one place to update | `claude plugin update mldlc` |
| vendored (`mldlc init --skills`, or `mldlc skills install`) | the project owns and may edit its skills; works without the plugin | `mldlc skills install --force` replaces them |

Vendored skills are copies: improvements to the kit do not reach them until you refresh.

## Releasing the kit

`pyproject.toml`, `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` must carry the same
version (a test enforces it). `claude plugin tag` creates the release tag once they agree.
