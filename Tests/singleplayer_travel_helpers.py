"""Read-only reuse of frozen command oracle; all compiled outputs are private."""
from pathlib import Path
source=Path(__file__).with_name('special_command_helpers.py').read_text()
source=source.replace("'work/special-command-agent'", "'work/singleplayer-travel-agent'")
exec(compile(source,str(Path(__file__).with_name('special_command_helpers.py')),'exec'),globals())
