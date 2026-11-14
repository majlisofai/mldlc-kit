"""mldlc: the command line behind the skills. Run it in a project folder (one with an mldlc.yaml), or pass -C."""
import argparse
import json
import sys
from pathlib import Path

from mldlc import documents, evidence, gates, ledger, release, scaffold
from mldlc.project import CONFIG_NAME, Project
from mldlc.stages import GATES, ITERATE_SKILL, OPERATE_SKILL, REENTRY, START_SKILL, STAGES


def _print(result) -> int:
    for n in result.notes:
        print("  " + n)
    for p in result.problems:
        print("  PROBLEM: " + p)
    print("  RESULT:", "ok" if result.ok else "not ok")
    return 0 if result.ok else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mldlc", description="Gated ML development life cycle.")
    parser.add_argument("-C", "--project", default=None, help="the project folder (default: the current folder or a parent with an mldlc.yaml)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    ini = sub.add_parser("init", help="start a project here: mldlc.yaml and lifecycle/intent.md, spec.md")
    ini.add_argument("directory", nargs="?", default=".")
    ini.add_argument("--name"); ini.add_argument("--hooks", action="store_true", help="also create mldlc_hooks.py")
    ini.add_argument("--skills", action="store_true", help="also copy the skills into .claude/skills")
    ini.add_argument("--force", action="store_true")

    st = sub.add_parser("status", help="show the gates and the next stage")
    st.add_argument("--require", default="", help="comma-separated gates that must be valid; exit 1 otherwise (for CI)")
    st.add_argument("--json", action="store_true")
    sub.add_parser("info", help="show the project's configuration and commands")
    sub.add_parser("triggers", help="evaluate the spec's triggers against the latest training run")
    chk = sub.add_parser("check", help="run a gate's checks; changes nothing")
    chk.add_argument("gate", choices=list(GATES))
    app = sub.add_parser("approve", help="record a passed gate (G0 to G4)")
    app.add_argument("gate", choices=list(GATES)); app.add_argument("--by", default=""); app.add_argument("--note", default="")
    card = sub.add_parser("card", help="create the model card for a version, with the facts filled in from MLflow")
    card.add_argument("version", nargs="?")
    pro = sub.add_parser("promote", help="G5: set the production alias, only on a person's approval")
    pro.add_argument("--version"); pro.add_argument("--by", default=""); pro.add_argument("--note", default="")
    rb = sub.add_parser("rollback", help="move the production alias back to a version released through G5")
    rb.add_argument("--to", required=True); rb.add_argument("--by", default=""); rb.add_argument("--reason", default="")
    re_ = sub.add_parser("reentry", help="which gate a kind of change re-enters")
    re_.add_argument("kind", choices=list(REENTRY))
    sk = sub.add_parser("skills", help="install the skills into a project")
    sk.add_argument("action", choices=["install", "path"]); sk.add_argument("--dest", default=".claude/skills"); sk.add_argument("--force", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.cmd == "reentry":
        gate, why = REENTRY[args.kind]
        later = [s.gate for s in STAGES[STAGES.index(GATES[gate]):]]
        print(f"A {args.kind} change ({why}) re-enters {gate} ({GATES[gate].title}). Gates to pass again: {', '.join(later)}.")
        print(f"Start with the `{GATES[gate].skill}` skill.")
        return 0
    if args.cmd == "skills":
        if args.action == "path":
            print(scaffold.skills_dir())
            return 0
        made = scaffold.install_skills(Path(args.dest), args.force)
        print(f"installed {len(made)} skills into {args.dest}" if made else "nothing to install; the skills are already there (use --force to replace)")
        return 0
    if args.cmd == "init":
        directory = Path(args.directory if args.project is None else args.project)
        made = scaffold.init_project(directory, args.name, args.hooks, args.force)
        if args.skills:
            made += scaffold.install_skills(directory / ".claude" / "skills", args.force)
        print("created:\n" + "\n".join(f"  {p}" for p in made))
        print(f"\nNext: fill in lifecycle/intent.md with the `{START_SKILL}` skill, or run `mldlc status`.")
        return 0

    project = Project.load(args.project)
    c = evidence.client(project)
    if args.cmd == "info":
        print(f"project            {project.name}   ({project.root / CONFIG_NAME})")
        print(f"lifecycle          {project.lifecycle_dir}")
        print(f"training           experiment {project.training_experiment}, model {project.model_name}, alias {project.alias}")
        print(f"validation         experiment {project.validation_experiment}")
        print(f"data version       {project.data.get('type')} -> {project.data_version() if project.data.get('type') != 'none' else 'not tracked'}")
        print(f"code paths         {project.code_paths}")
        print(f"baseline metric    {project.baseline_metric}; allowed metrics {project.allowed_metrics}")
        print(f"hooks              {project.hooks or 'none'}")
        for name, command in project.commands.items():
            print(f"command {name:<10} {command}")
        return 0
    if args.cmd == "status":
        rows = ledger.status(project, c)
        if args.json:
            print(json.dumps([{"gate": s.gate, "stage": s.title, "state": st, "detail": why, "skill": s.skill} for s, st, why in rows], indent=2))
        else:
            print(f"{project.name}: model {project.model_name}")
            for stage, state, why in rows:
                print(f"  {stage.gate}  {stage.title:<9} {state:<8} {why}")
            nxt = next((s for s, st, _ in rows if st != "valid"), None)
            print("  next:", f"run the `{nxt.skill}` skill ({nxt.gate} {nxt.title})" if nxt else f"all gates valid; operate with `{OPERATE_SKILL}`")
        required = [g.strip() for g in args.require.split(",") if g.strip()]
        unknown = [g for g in required if g not in GATES]
        if unknown:
            raise SystemExit(f"unknown gate(s) in --require: {unknown}")
        failing = [s.gate for s, st, _ in rows if s.gate in required and st != "valid"]
        if failing:
            print(f"required gates not valid: {', '.join(failing)}", file=sys.stderr)
            return 1
        return 0
    if args.cmd == "triggers":
        for t in evidence.evaluate_triggers(project, c):
            print(f"  {'FIRED' if t['fired'] else 'ok   '}  {t['name']}: {t['detail']}" + (f"  -> re-enter via `{ITERATE_SKILL}` ({t['then']})" if t["fired"] else ""))
        return 0
    if args.cmd == "check":
        return _print(gates.run_check(project, args.gate, c))
    if args.cmd == "approve":
        return _print(gates.approve(project, args.gate, args.by, args.note, c))
    if args.cmd == "card":
        print(f"created {release.init_card(project, args.version, c)}")
        return 0
    if args.cmd == "promote":
        return _print(release.promote(project, args.version, args.by, args.note, c))
    return _print(release.rollback(project, args.to, args.by, args.reason, c))


if __name__ == "__main__":
    sys.exit(main())
