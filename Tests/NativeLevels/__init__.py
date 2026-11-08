"""Level-parameterized original discovery and bounded recovery planning."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORDS = {2: 'two', 3: 'three', 4: 'four', 5: 'five', 6: 'six', 7: 'seven',
         8: 'eight', 9: 'nine', 10: 'ten', 11: 'eleven', 12: 'twelve',
         13: 'thirteen', 14: 'fourteen'}


def output_dir(level):
    return ROOT / ('work/level-two-map' if level == 2 else f'work/level-{level}-map')


def add_level(parser):
    parser.add_argument('--level', type=int, choices=WORDS, required=True)
