from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from contextlib import contextmanager
from typing import Generator

from horror_story.adapters import AdapterFactory
from horror_story.metrics import MetricsCollector


@contextmanager
def _noop_ctx() -> Generator[None, None, None]:
    """No-op context manager used when metrics is None."""
    yield


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
    run_p.add_argument("--seed", type=int, default=None, metavar="N", help="Override manifest seed.")
    run_p.add_argument("--scene", metavar="SCENE_ID", help="Re-run a single scene only.")
    run_p.add_argument("--dry-run", action="store_true", help="Print execution plan without writing files.")
    run_p.add_argument("--validate", action="store_true", help="Validate all artifacts after run.")
    run_p.add_argument("--regen", action="store_true", help="Force a new versioned run directory.")
    run_p.add_argument("--width", type=int, default=None, metavar="W", help="Override render width.")
    run_p.add_argument("--height", type=int, default=None, metavar="H", help="Override render height.")
    run_p.add_argument(
        "--image-adapter",
        metavar="NAME",
        default=None,
        help="Override the image adapter from pipeline.toml (e.g. mock, mflux-schnell).",
    )

    # validate
    validate_p = sub.add_parser("validate", help="Validate artifacts against schemas.")
    validate_p.add_argument("--run-dir", metavar="DIR", help="Run directory to validate.")

    # validate-schemas
    sub.add_parser("validate-schemas", help="Validate all spec JSON schemas are well-formed.")

    # stats
    stats_p = sub.add_parser("stats", help="Show timing summary for recent pipeline runs.")
    stats_p.add_argument("--out", required=True, metavar="DIR", help="Output root directory.")
    stats_p.add_argument("--story", required=True, metavar="ID", help="Story ID.")
    stats_p.add_argument("-n", type=int, default=10, metavar="N", help="Number of recent runs to show.")

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
    elif args.command == "stats":
        _cmd_stats(args)


def _locate_toml(story_path: Path) -> Path:
    candidate = story_path.parent / "pipeline.toml"
    if candidate.exists():
        return candidate
    raise FileNotFoundError(
        f"pipeline.toml not found next to {story_path}. "
        "Create one or point --story at a directory containing pipeline.toml."
    )


def _resolve_latest_run(out_dir: Path, base_run_id: str) -> Path | None:
    """Return the most recent run directory for base_run_id.

    Considers the bare directory (revision 0) and all _r<N> siblings.
    Chooses the one with the highest integer revision number.
    Returns None if no run directory exists at all.
    """
    import re as _re
    candidates: list[tuple[int, Path]] = []
    bare = out_dir / base_run_id
    if bare.exists():
        candidates.append((0, bare))
    for p in out_dir.glob(f"{base_run_id}_r*"):
        m = _re.fullmatch(r".*_r(\d+)", p.name)
        if m and p.is_dir():
            candidates.append((int(m.group(1)), p))
    if not candidates:
        return None
    return max(candidates, key=lambda t: t[0])[1]


def _per_scene_seed(base_seed: int, scene_index: int, stage_index: int) -> int:
    return base_seed ^ (scene_index * 1000) ^ stage_index


def _next_revision(run_dir: Path, scene_id: str) -> int:
    """Return the next 1-based revision number for a --scene re-run.

    Scans video/ for existing scene_<id>_composed_r<n>.mp4 and returns max(n)+1.
    Returns 1 if no versioned artifacts exist yet.
    """
    video_dir = run_dir / "video"
    max_n = 0
    for p in video_dir.glob(f"scene_{scene_id}_composed_r*.mp4"):
        m = re.search(r"_r(\d+)\.mp4$", p.name)
        if m:
            max_n = max(max_n, int(m.group(1)))
    return max_n + 1


def _run_scene(
    scene_id: str,
    scene_index: int,
    run_dir: Path,
    manifest: Any,
    index_path: Path,
    *,
    adapters: Any,
    width: int,
    height: int,
    fps: int,
    seed: int,
    suffix: str = "",
    image_style_suffix: str = "",
    audio_assets_dir: str = "",
    translator: Any = None,
    segment_offset: int = 0,
    metrics: MetricsCollector | None = None,
) -> tuple[Path | None, str | None]:
    """Run all per-scene stages, patching artifact_index after each one.

    suffix is appended before each artifact's extension ('' on a full run,
    '_r1' on a --scene re-run). Returns (composed_mp4_path, error_message).
    """
    from horror_story.pipeline.script import generate_script_from_path
    from horror_story.pipeline.timeline import plan_timeline
    from horror_story.pipeline.compositor import compose_scene

    scenes_dir = run_dir / "scenes"
    scripts_dir = run_dir / "scripts"
    audio_dir = run_dir / "audio"
    frames_dir = run_dir / "frames"
    video_dir = run_dir / "video"

    for d in (scripts_dir, audio_dir, frames_dir, video_dir):
        d.mkdir(parents=True, exist_ok=True)

    scene_path = scenes_dir / f"scene_{scene_id}.json"
    story_id = manifest.story_id

    def _rel(p: Path) -> str:
        return str(p.relative_to(run_dir))

    _m = metrics  # shorthand

    try:
        # Stage 2: script
        script_path = scripts_dir / f"script_{scene_id}{suffix}.json"
        print(f"[script] {scene_id} → {script_path}")
        with (_m.stage("script_gen", scene_id=scene_id) if _m else _noop_ctx()):
            script = generate_script_from_path(
                scene_path, manifest,
                translator=translator,
                segment_offset=segment_offset,
            )
            _atomic_write(script_path, json.dumps(script.to_dict(), indent=2))
        _patch_scene_entry(index_path, run_dir, scene_id, "partial",
                           script=_rel(script_path))

        tts = AdapterFactory.get_tts(adapters.tts)
        language = str(manifest.languages.get("primary", "en"))

        # Stage 3: TTS narration + dialogue
        voice_line_sidecars: list[Path] = []
        with (_m.stage("tts", scene_id=scene_id) if _m else _noop_ctx()):
            for seg in script.segments:
                seg_seed = _per_scene_seed(seed, scene_index, 3)
                wav_path = audio_dir / f"narration_{scene_id}_{seg.segment_id}{suffix}.wav"
                print(f"[tts/narration] {scene_id}/{seg.segment_id} → {wav_path}")
                tts.synthesize(
                    text=seg.text_en,
                    voice_id=seg.voice_id,
                    language=language,
                    pacing_ms=seg.pacing_ms,
                    seed=seg_seed,
                    out_path=wav_path,
                    story_id=story_id,
                    scene_id=scene_id,
                    line_ref=seg.segment_id,
                    line_type="narration",
                )
                voice_line_sidecars.append(wav_path.with_suffix(".json"))

            # Stage 4: TTS dialogue
            for dlg in script.dialogue_lines:
                dlg_seed = _per_scene_seed(seed, scene_index, 4)
                wav_path = audio_dir / f"dialogue_{scene_id}_{dlg.line_id}{suffix}.wav"
                print(f"[tts/dialogue] {scene_id}/{dlg.line_id} → {wav_path}")
                tts.synthesize(
                    text=dlg.text_en,
                    voice_id=dlg.voice_id,
                    language=language,
                    pacing_ms=dlg.pacing_ms,
                    seed=dlg_seed,
                    out_path=wav_path,
                    story_id=story_id,
                    scene_id=scene_id,
                    line_ref=dlg.line_id,
                    line_type="dialogue",
                )
                voice_line_sidecars.append(wav_path.with_suffix(".json"))

        # Stage 5: image keyframe
        img_seed = _per_scene_seed(seed, scene_index, 5)
        keyframe_path = frames_dir / f"keyframe_{scene_id}{suffix}.png"
        scene_data = json.loads(scene_path.read_text())
        visual = scene_data.get("visual_description", scene_id)
        suffix_stripped = image_style_suffix.strip()
        prompt = f"{visual}, {suffix_stripped}" if suffix_stripped else visual
        print(f"[image] {scene_id} → {keyframe_path}")
        with (_m.stage("image", scene_id=scene_id) if _m else _noop_ctx()):
            AdapterFactory.get_image(adapters.image).generate(
                prompt=prompt,
                width=width,
                height=height,
                seed=img_seed,
                out_path=keyframe_path,
                story_id=story_id,
                scene_id=scene_id,
            )
        _patch_scene_entry(index_path, run_dir, scene_id, "partial",
                           keyframe=_rel(keyframe_path))

        # Stage 6/7: motion
        mot_seed = _per_scene_seed(seed, scene_index, 6)
        motion_path = frames_dir / f"motion_{scene_id}{suffix}.mp4"
        duration_s = max(_voice_lines_duration_s(voice_line_sidecars), 1.0)
        print(f"[motion] {scene_id} → {motion_path}")
        with (_m.stage("motion", scene_id=scene_id) if _m else _noop_ctx()):
            AdapterFactory.get_motion(adapters.motion).animate(
                frame_path=keyframe_path,
                duration_s=duration_s,
                fps=fps,
                effect="zoom",
                seed=mot_seed,
                out_path=motion_path,
                story_id=story_id,
                scene_id=scene_id,
            )
        _patch_scene_entry(index_path, run_dir, scene_id, "partial",
                           motion=_rel(motion_path))

        # Stage 7: ambient audio
        amb_seed = _per_scene_seed(seed, scene_index, 7)
        ambient_path = audio_dir / f"ambient_{scene_id}{suffix}.wav"
        mood = str(scene_data.get("mood", "dread"))
        print(f"[audio/ambient] {scene_id} → {ambient_path}")
        with (_m.stage("audio", scene_id=scene_id) if _m else _noop_ctx()):
            AdapterFactory.get_audio(adapters.audio, assets_dir=audio_assets_dir).generate(
                mood=mood,
                duration_s=duration_s,
                seed=amb_seed,
                out_path=ambient_path,
                story_id=story_id,
                scene_id=scene_id,
            )
        _patch_scene_entry(index_path, run_dir, scene_id, "partial",
                           ambient=_rel(ambient_path))

        # Stage 7.5: timeline (no typography yet — no index field — internal artifact)
        timeline_path = video_dir / f"timeline_{scene_id}{suffix}.json"
        print(f"[timeline] {scene_id} → {timeline_path}")
        with (_m.stage("timeline", scene_id=scene_id) if _m else _noop_ctx()):
            plan_timeline(
                script_path=script_path,
                motion_sidecar_path=motion_path.with_suffix(".json"),
                ambient_sidecar_path=ambient_path.with_suffix(".json"),
                voice_line_sidecar_paths=voice_line_sidecars,
                out_path=timeline_path,
            )

        # Stage 8: typography (per-segment PNGs + timing manifest)
        typ_seed = _per_scene_seed(seed, scene_index, 8)
        out_timing = video_dir / f"typography_{scene_id}{suffix}_timing.json"
        print(f"[typography] {scene_id} → {out_timing}")
        with (_m.stage("typography", scene_id=scene_id) if _m else _noop_ctx()):
            AdapterFactory.get_typography(adapters.typography).render(
                script=json.loads(script_path.read_text()),
                timeline=json.loads(timeline_path.read_text()),
                scene_id=scene_id,
                seed=typ_seed,
                out_dir=video_dir,
                out_timing=out_timing,
                width=width,
                height=height,
            )
        _patch_scene_entry(index_path, run_dir, scene_id, "partial",
                           typography=_rel(out_timing))

        # Stage 9: compose
        composed_path = video_dir / f"scene_{scene_id}_composed{suffix}.mp4"
        print(f"[compositor] {scene_id} → {composed_path}")
        with (_m.stage("compositor", scene_id=scene_id) if _m else _noop_ctx()):
            compose_scene(timeline_path=timeline_path, timing_path=out_timing, out_path=composed_path)
        _patch_scene_entry(index_path, run_dir, scene_id, "complete",
                           composed=_rel(composed_path))

        return composed_path, None

    except Exception as exc:
        _set_scene_failed(index_path, scene_id)
        return None, str(exc)


def _voice_lines_duration_s(sidecar_paths: list[Path]) -> float:
    """Sum actual_duration_ms (falling back to pacing_ms) across all voice-line sidecars."""
    total_ms = 0
    for p in sidecar_paths:
        data = json.loads(p.read_text())
        actual = data.get("actual_duration_ms")
        total_ms += int(actual) if actual is not None else int(data["pacing_ms"])
    return total_ms / 1000.0


def _atomic_write(path: Path, content: str) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(content)
    tmp.replace(path)


def _patch_scene_entry(
    index_path: Path,
    run_dir: Path,
    scene_id: str,
    status: str,
    **field_updates: str | None,
) -> None:
    """Merge field_updates into the SceneEntry for scene_id and persist the index.

    Called after each individual stage so the index always reflects the last
    known-good state. field_updates keys match SceneEntry field names.
    """
    from horror_story.manifest import ArtifactIndex, SceneEntry

    ai = ArtifactIndex.from_path(index_path)
    existing = ai.scenes.get(scene_id)
    if existing is None:
        existing = SceneEntry(scene=f"scenes/scene_{scene_id}.json")

    # Build an updated dict from the existing entry, then apply overrides.
    current = existing.to_dict()
    current["status"] = status
    for key, val in field_updates.items():
        current[key] = val

    ai.scenes[scene_id] = SceneEntry.from_dict(current)
    ai.write(index_path)


def _set_scene_failed(index_path: Path, scene_id: str) -> None:
    """Mark a scene failed without touching artifact path fields.

    Called when _run_scene() returns an error; the incremental patches already
    recorded whatever stages succeeded, so only the status needs updating.
    """
    from horror_story.manifest import ArtifactIndex

    ai = ArtifactIndex.from_path(index_path)
    existing = ai.scenes.get(scene_id)
    if existing is None:
        return
    # Only downgrade if not already complete (shouldn't happen, but be safe).
    if existing.status != "complete":
        existing.status = "failed"
        ai.write(index_path)


def _render_final_from_index(
    run_dir: Path,
    manifest: Any,
    config: Any,
    seed: int,
    index_path: Path,
) -> None:
    """Read composed scene paths from artifact_index and render the final MP4."""
    from horror_story.manifest import ArtifactIndex
    from horror_story.pipeline.renderer import render_final, ffmpeg_available

    if not ffmpeg_available():
        print("[warning] FFmpeg not available; skipping final render.")
        return

    ai = ArtifactIndex.from_path(index_path)

    incomplete = [
        sid for sid in manifest.scene_order()
        if not (ai.scenes.get(sid) and ai.scenes[sid].status == "complete")
    ]
    if incomplete:
        print(
            f"[error] cannot render final: {len(incomplete)} scene(s) not complete: "
            + ", ".join(incomplete),
            file=sys.stderr,
        )
        sys.exit(1)

    all_composed = [
        run_dir / str(ai.scenes[sid].composed)
        for sid in manifest.scene_order()
    ]

    final_path = run_dir / f"final_{config.story.id}_{seed}.mp4"
    print(f"[renderer] final → {final_path}")
    try:
        render_final(
            manifest=manifest.to_dict(),
            scene_paths=all_composed,
            out_path=final_path,
        )
    except Exception as exc:
        print(f"[error] final render failed: {exc}", file=sys.stderr)
        sys.exit(1)

    rj_path = final_path.with_name("render_job.json")
    sha: str | None = None
    if rj_path.exists():
        rj = json.loads(rj_path.read_text())
        sha = rj.get("sha256")

    ai = ArtifactIndex.from_path(index_path)
    ai.final = {
        "path": final_path.name,
        "sha256": sha,
        "status": "complete",
    }
    ai.write(index_path)
    print(f"[done] {final_path}")


def _cmd_run(args: argparse.Namespace) -> None:
    from horror_story.config import PipelineConfig
    from horror_story.manifest import Manifest, initialize_run
    from horror_story.pipeline.parse import parse_story

    story_path = Path(args.story)
    out_dir = Path(args.out)

    if not story_path.exists():
        print(f"[error] story file not found: {story_path}", file=sys.stderr)
        sys.exit(1)

    toml_path = _locate_toml(story_path)
    config = PipelineConfig.from_toml(toml_path)

    import dataclasses
    if args.seed is not None or args.width is not None or args.height is not None:
        story_cfg = config.story
        render_cfg = config.render
        if args.seed is not None:
            story_cfg = dataclasses.replace(story_cfg, seed=args.seed)
        if args.width is not None or args.height is not None:
            w = args.width if args.width is not None else render_cfg.width
            h = args.height if args.height is not None else render_cfg.height
            render_cfg = dataclasses.replace(render_cfg, width=w, height=h)
        config = dataclasses.replace(config, story=story_cfg, render=render_cfg)

    if args.image_adapter is not None:
        config = dataclasses.replace(
            config,
            adapters=dataclasses.replace(config.adapters, image=args.image_adapter),
        )

    seed = config.story.seed
    width = config.render.width
    height = config.render.height
    fps = config.render.fps

    story_text = story_path.read_text()
    base_run_id = f"run_{config.story.id}_{seed}"
    base_run_dir = out_dir / base_run_id

    if args.dry_run:
        scenes = parse_story(story_text, config.story.id)
        print(f"[dry-run] run_id={base_run_id}")
        print(f"[dry-run] story={story_path} out={out_dir} seed={seed} "
              f"width={width} height={height}")
        for i, scene in enumerate(scenes):
            print(f"[dry-run]   scene[{i}] {scene.scene_id}")
        if args.scene:
            print(f"[dry-run] single-scene mode: {args.scene}")
        print("[dry-run] no artifacts written.")
        return

    # --scene: load existing run, write _r<n> artifacts, update index, re-render
    if args.scene:
        resolved_run_dir = _resolve_latest_run(out_dir, base_run_id)
        if resolved_run_dir is None:
            print(
                f"[error] no existing run at {out_dir / base_run_id}. "
                "Run without --scene first.",
                file=sys.stderr,
            )
            sys.exit(1)
        base_run_dir = resolved_run_dir

        manifest = Manifest.from_path(base_run_dir / "manifest.json")
        scenes = parse_story(story_text, config.story.id)
        scene_index_map = {s.scene_id: s.index for s in scenes}

        if args.scene not in scene_index_map:
            print(f"[error] scene '{args.scene}' not found in story.", file=sys.stderr)
            sys.exit(1)

        revision = _next_revision(base_run_dir, args.scene)
        suffix = f"_r{revision}"
        index_path = base_run_dir / "artifact_index.json"

        scene_metrics = MetricsCollector(
            story_id=config.story.id,
            run_id=base_run_dir.name,
            scene_id=args.scene,
        )

        _translator = _build_translator(story_path, config)
        _scene_offset = _segment_offset_for_scene(args.scene, scenes, story_text, config)

        composed_path, error = _run_scene(
            scene_id=args.scene,
            scene_index=scene_index_map[args.scene],
            run_dir=base_run_dir,
            manifest=manifest,
            index_path=index_path,
            adapters=config.adapters,
            width=width,
            height=height,
            fps=fps,
            seed=seed,
            suffix=suffix,
            image_style_suffix=config.image.style_suffix,
            audio_assets_dir=config.audio.assets_dir,
            translator=_translator,
            segment_offset=_scene_offset,
            metrics=scene_metrics,
        )

        if error:
            print(f"[error] {args.scene}: {error}", file=sys.stderr)
            sys.exit(1)

        print(f"[composed] {args.scene} → {composed_path}")

        _render_final_from_index(base_run_dir, manifest, config, seed, index_path)

        scene_metrics.write(base_run_dir / "metrics.json")

        if args.validate:
            _validate_run_dir(base_run_dir)
        return

    # Full run
    run_id = base_run_id
    run_dir = base_run_dir

    if run_dir.exists() and not args.regen:
        print(
            f"[error] run directory already exists: {run_dir}. "
            "Use --regen to create a new versioned run.",
            file=sys.stderr,
        )
        sys.exit(1)

    if args.regen:
        n = 1
        while (out_dir / f"{run_id}_r{n}").exists():
            n += 1
        run_id = f"{run_id}_r{n}"
        run_dir = out_dir / run_id

    run_metrics = MetricsCollector(story_id=config.story.id, run_id=run_id)

    with run_metrics.stage("parse"):
        manifest, _, scenes = initialize_run(
            config, story_text, story_path.name, out_dir, run_id_override=run_id
        )

    scene_index_map = {s.scene_id: s.index for s in scenes}
    index_path = run_dir / "artifact_index.json"
    errors: list[tuple[str, str]] = []

    run_translator = _build_translator(story_path, config)
    seg_offset = 0

    for scene in scenes:
        scene_id = scene.scene_id
        composed_path, error = _run_scene(
            scene_id=scene_id,
            scene_index=scene_index_map[scene_id],
            run_dir=run_dir,
            manifest=manifest,
            index_path=index_path,
            adapters=config.adapters,
            width=width,
            height=height,
            fps=fps,
            seed=seed,
            suffix="",
            image_style_suffix=config.image.style_suffix,
            audio_assets_dir=config.audio.assets_dir,
            translator=run_translator,
            segment_offset=seg_offset,
            metrics=run_metrics,
        )
        from horror_story.pipeline.script import _split_narration as _sn
        seg_offset += len(_sn(scene.text))

        if error:
            errors.append((scene_id, error))
            print(f"[error] {scene_id}: {error}", file=sys.stderr)
        else:
            print(f"[composed] {scene_id} → {composed_path}")

    if errors:
        print(f"[summary] {len(errors)} scene(s) failed; skipping final render.")
        sys.exit(1)

    with run_metrics.stage("render"):
        _render_final_from_index(run_dir, manifest, config, seed, index_path)

    run_metrics.write(run_dir / "metrics.json")

    if args.validate:
        _validate_run_dir(run_dir)


def _build_translator(story_path: Path, config: Any) -> Any:
    """Return a ParallelTextTranslator if a secondary-language file exists, else None."""
    from horror_story.pipeline.translate import ParallelTextTranslator
    secondary_lang = str(getattr(config.story, "secondary_language", ""))
    if not secondary_lang:
        return None
    # Convention: <story_stem>_<lang>.txt alongside the story file.
    candidate = story_path.with_name(
        story_path.stem.replace("_EN", "") + f"_{secondary_lang}.txt"
    )
    # Also try exact convention used by this project: pijons_from_hell.txt
    alt_candidate = story_path.parent / story_path.name.replace("_EN.txt", ".txt").replace(
        "pigeons_from_hell", "pijons_from_hell"
    )
    for path in (candidate, alt_candidate):
        if path.exists():
            print(f"[script/translate] using parallel text: {path.name}")
            return ParallelTextTranslator(path.read_text())
    print(f"[script/translate] fallback: parallel text not found for lang={secondary_lang!r}")
    return None


def _segment_offset_for_scene(
    scene_id: str,
    scenes: list[Any],
    story_text: str,
    config: Any,
) -> int:
    """Count narration segments in all scenes that come before scene_id."""
    from horror_story.pipeline.script import _split_narration as _sn
    offset = 0
    for scene in scenes:
        if scene.scene_id == scene_id:
            break
        offset += len(_sn(scene.text))
    return offset


# Maps glob patterns (relative to run_dir) to schema filenames.
_GLOB_SCHEMA: list[tuple[str, str]] = [
    ("manifest.json",                "manifest.schema.json"),
    ("artifact_index.json",          "artifact_index.schema.json"),
    ("render_job.json",              "render_job.schema.json"),
    ("scenes/scene_*.json",          "scene.schema.json"),
    ("scripts/script_*.json",        "script.schema.json"),
    ("audio/narration_*.json",       "voice_line.schema.json"),
    ("audio/dialogue_*.json",        "voice_line.schema.json"),
    ("audio/ambient_*.json",         "ambient_artifact.schema.json"),
    ("frames/keyframe_*.json",       "keyframe.schema.json"),
    ("frames/motion_*.json",         "motion_artifact.schema.json"),
    ("video/typography_*_timing.json", "typography_timing.schema.json"),
    ("video/timeline_*.json",        "timeline.schema.json"),
    ("video/scene_*_composed.json",   "composed_scene.schema.json"),
    ("video/scene_*_composed_r*.json", "composed_scene.schema.json"),
    ("metrics.json",                  "metrics.schema.json"),
]


def _validate_run_dir(run_dir: Path) -> None:
    import jsonschema
    from horror_story.schemas import validate

    if not run_dir.is_dir():
        print(f"[validate] run directory not found: {run_dir}", file=sys.stderr)
        sys.exit(1)

    errors: list[str] = []

    for glob_pattern, schema_name in _GLOB_SCHEMA:
        for path in sorted(run_dir.glob(glob_pattern)):
            try:
                instance = json.loads(path.read_text())
                validate(instance, schema_name)
                print(f"[validate] OK {path.relative_to(run_dir)}")
            except jsonschema.ValidationError as exc:
                msg = f"{path.relative_to(run_dir)}: {exc.message}"
                errors.append(msg)
                print(f"[validate] FAIL {msg}", file=sys.stderr)
            except Exception as exc:
                msg = f"{path.relative_to(run_dir)}: {exc}"
                errors.append(msg)
                print(f"[validate] FAIL {msg}", file=sys.stderr)

    if errors:
        print(f"[validate] {len(errors)} validation error(s).", file=sys.stderr)
        sys.exit(1)
    else:
        print("[validate] all artifacts valid.")


def _cmd_validate(args: argparse.Namespace) -> None:
    run_dir = getattr(args, "run_dir", None)
    if run_dir is None:
        print("[validate] --run-dir required.", file=sys.stderr)
        sys.exit(1)
    _validate_run_dir(Path(run_dir))


def _cmd_validate_schemas() -> None:
    from horror_story.schemas import load_all_schemas
    schemas = load_all_schemas()
    print(f"[validate-schemas] loaded {len(schemas)} schemas — all well-formed.")


# Column names for the stats table.
_STATS_STAGES = ["parse", "script_gen", "tts", "image", "motion", "audio", "timeline", "typography", "compositor", "render"]


def _fmt_s(value: float | None) -> str:
    """Format a duration in seconds for the stats table."""
    if value is None:
        return "-"
    if value < 10:
        return f"{value:.1f}s"
    return f"{round(value)}s"


def _cmd_stats(args: argparse.Namespace) -> None:
    out_dir = Path(args.out)
    story_id: str = args.story
    n: int = args.n

    pattern = str(out_dir / story_id / "run_*" / "metrics.json")
    import glob as _glob
    paths = sorted(_glob.glob(pattern))

    if not paths:
        print(f"[stats] no metrics.json files found under {out_dir / story_id}")
        return

    # Sort by run_id (parent directory name) descending, take last N.
    paths.sort(key=lambda p: Path(p).parent.name, reverse=True)
    paths = paths[:n]

    # Collect typed records from each metrics file.
    run_ids: list[str] = []
    totals: list[float] = []
    stage_maps: list[dict[str, float]] = []

    for p in paths:
        data = json.loads(Path(p).read_text())
        sm: dict[str, float] = {}
        for entry in data.get("stages", []):
            stage_name = str(entry["stage"])
            duration = float(entry["duration_s"])
            # Accumulate per-stage totals (multiple scene entries for same stage).
            sm[stage_name] = sm.get(stage_name, 0.0) + duration
        run_ids.append(str(data.get("run_id", Path(p).parent.name)))
        totals.append(float(data.get("total_s", 0.0)))
        stage_maps.append(sm)

    # Pick only stages that appear in at least one run, preserving canonical order.
    present_stages = [s for s in _STATS_STAGES if any(s in sm for sm in stage_maps)]

    # Build header.
    run_id_w = max(len("run-id"), max(len(rid) for rid in run_ids))
    col_w = 8

    header_parts = [f"{'run-id':<{run_id_w}}", f"{'total':>{col_w}}"]
    for s in present_stages:
        header_parts.append(f"{s[:col_w]:>{col_w}}")
    print("  ".join(header_parts))

    for rid, total, sm in zip(run_ids, totals, stage_maps):
        total_str = _fmt_s(total)
        row_parts = [f"{rid:<{run_id_w}}", f"{total_str:>{col_w}}"]
        for s in present_stages:
            row_parts.append(f"{_fmt_s(sm.get(s)):>{col_w}}")
        print("  ".join(row_parts))
