import argparse
import sys


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="horror-story",
        description="AI-driven cinematic horror narration pipeline.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0",
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    # run
    run_p = sub.add_parser("run", help="Run the full pipeline.")
    run_p.add_argument("--story", required=True, metavar="PATH", help="Path to story .txt file.")
    run_p.add_argument("--out", required=True, metavar="DIR", help="Output root directory.")
    run_p.add_argument("--seed", type=int, default=42, metavar="N", help="Master seed (default: 42).")
    run_p.add_argument("--scene", metavar="SCENE_ID", help="Re-run a single scene only.")
    run_p.add_argument("--dry-run", action="store_true", help="Validate config without writing artifacts.")
    run_p.add_argument("--regen", action="store_true", help="Force a new versioned run directory.")

    # validate
    validate_p = sub.add_parser("validate", help="Validate artifacts against schemas.")
    validate_p.add_argument("--run-dir", metavar="DIR", help="Run directory to validate.")

    # validate-schemas  (validate that spec schemas themselves are well-formed)
    sub.add_parser("validate-schemas", help="Validate all spec JSON schemas are well-formed.")

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    if args.command == "run":
        _cmd_run(args)
    elif args.command == "validate":
        _cmd_validate(args)
    elif args.command == "validate-schemas":
        _cmd_validate_schemas()


def _cmd_run(args: argparse.Namespace) -> None:
    # Stub — pipeline logic implemented in later issues.
    print(f"[run] story={args.story} out={args.out} seed={args.seed}")
    if args.dry_run:
        print("[run] dry-run mode: no artifacts written.")


def _cmd_validate(args: argparse.Namespace) -> None:
    # Stub — full validation implemented in later issues.
    run_dir = getattr(args, "run_dir", None)
    print(f"[validate] run_dir={run_dir}")


def _cmd_validate_schemas() -> None:
    from horror_story.schemas import load_all_schemas
    schemas = load_all_schemas()
    print(f"[validate-schemas] loaded {len(schemas)} schemas — all well-formed.")
