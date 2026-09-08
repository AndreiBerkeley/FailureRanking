#!/usr/bin/env python3
"""Rebuild data/ifbench from its sources. Thin wrapper around the shared script."""
import runpy, sys
sys.argv = ["migrate_gepa_artifact_benchmark.py", "--benchmark", "ifbench"] + sys.argv[1:]
runpy.run_path(__file__.rsplit("/data/", 1)[0] + "/data/scripts/migrate_gepa_artifact_benchmark.py", run_name="__main__")
