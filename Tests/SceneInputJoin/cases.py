"""Reuse sealed original-derived cases without replacing any game routine."""
import importlib.util
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INPUT = {0x430d30, 0x430d80, 0x430ec0, 0x431300, 0x4b3430, 0x4b3490, 0x4b3ab0}


def cases(random_source):
    for family in ('scene_camera', 'application_input_configuration'):
        path = ROOT / 'Tests' / 'families' / (family + '.cases.py')
        spec = importlib.util.spec_from_file_location('join_' + family, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for case in module.cases(random_source):
            if family == 'application_input_configuration' and case.function not in INPUT:
                continue
            if os.environ.get('CLAW_JOIN_MISSING') and case.function not in INPUT | {0x46c860}:
                continue
            yield case
