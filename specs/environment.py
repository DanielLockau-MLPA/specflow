# SPDX-FileCopyrightText: (C) 2026 ML!PA Consulting GmbH
# SPDX-License-Identifier: MIT

"""behave hooks: one isolated world (git workspace with test keys) per scenario."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "steps"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import exectrace  # noqa: F401  (the behave process takes part in the railguard function trace)
from world import Keys, World


def before_all(context):
    context.keys = Keys()


def after_all(context):
    context.keys.close()


def before_scenario(context, scenario):
    context.world = World(context.keys)


def after_scenario(context, scenario):
    context.world.close()
