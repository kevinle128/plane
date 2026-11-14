# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Command line: `python -m plane_agent_worker run` or `python -m plane_agent_worker probe`.

`run` polls Plane and runs claimed probes. `probe` runs one local probe without
Plane and prints the report; `--record DIR` also writes scrubbed protocol
transcripts for the driver tests.
"""

import argparse
import json
import logging
import os
import signal
import sys
import threading
from pathlib import Path

from plane_agent_worker.config import ConfigError, load_config
from plane_agent_worker.conformance import TranscriptRecorder, remove_stale_probes, run_probe
from plane_agent_worker.drivers.claude import ClaudeDriver
from plane_agent_worker.loop import WorkerLoop
from plane_agent_worker.plane_client import PlaneClient
from plane_agent_worker.process_registry import ProcessRegistry
from plane_agent_worker.sandbox import Sandboxes

logger = logging.getLogger("plane_agent_worker")


def build_sandboxes(config):
    return Sandboxes(config.sbx_bin, config.home, memory=config.sandbox_memory)


def build_drivers(config, registry, recorder=None):
    driver = ClaudeDriver(
        sandboxes=build_sandboxes(config), run_root=config.run_root, registry=registry, recorder=recorder
    )
    return {"claude_code": driver}


def clean_up_previous_worker(config, registry):
    """Stop the Harness processes of a previous Worker and remove its probe and session folders."""
    stopped = registry.reconcile(cleanup_roots=[config.run_root])
    if stopped:
        logger.info("Stopped %d Harness process group(s) left by a previous Worker", len(stopped))
    removed = remove_stale_probes(config.run_root)
    if removed:
        logger.info("Removed %d probe folder(s) left by a previous Worker", removed)


def command_run(config, registry):
    clean_up_previous_worker(config, registry)
    loop = WorkerLoop(
        client=PlaneClient(config.api_origin, config.read_token()),
        drivers=build_drivers(config, registry),
        run_root=config.run_root,
        token_file=config.token_file,
        plane_checkout=config.plane_checkout,
    )
    stop_event = threading.Event()
    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, lambda *_: stop_event.set())
    logger.info("Worker started; polling %s", config.api_origin)
    loop.run_forever(stop_event, config.poll_seconds)
    return 0


def command_probe(config, registry, harness, record_dir):
    clean_up_previous_worker(config, registry)
    recorder = None
    if record_dir:
        home = os.path.expanduser("~")
        recorder = TranscriptRecorder(
            Path(record_dir).resolve(),
            [(str(config.run_root), "<run_root>"), (home, "<home>"), (os.path.realpath(home), "<home>")],
        )
    drivers = build_drivers(config, registry, recorder)
    if harness not in drivers:
        print(f"No probe for {harness} in this Worker.", file=sys.stderr)
        return 2
    report = run_probe(
        drivers[harness],
        run_root=config.run_root,
        probe_key="local-probe",
        token_file=config.token_file,
        plane_checkout=config.plane_checkout,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if all(check["passed"] for check in report["checks"]) and report["models"] else 1


def main(argv=None):
    parser = argparse.ArgumentParser(prog="plane_agent_worker")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("run", help="Poll Plane and run claimed probes.")
    probe = commands.add_parser("probe", help="Run one local probe and print the report.")
    probe.add_argument("--harness", default="claude_code")
    probe.add_argument("--record", metavar="DIR", help="Write scrubbed protocol transcripts to DIR.")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if sys.platform != "darwin":
        print("The Worker runs only on macOS (the Mac Mini that holds the Harness CLIs).", file=sys.stderr)
        return 2
    try:
        config = load_config(os.environ)
    except ConfigError as error:
        print(f"Configuration error: {error}", file=sys.stderr)
        return 2
    registry = ProcessRegistry(config.run_root / ".processes")
    if args.command == "run":
        return command_run(config, registry)
    return command_probe(config, registry, args.harness, args.record)


if __name__ == "__main__":
    sys.exit(main())
