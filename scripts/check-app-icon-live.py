"""Read the launched Mac app's registered Dock icon, closing only our muted process."""
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / 'work/icon'
SWIFT = '''import AppKit
import Foundation
let pid = pid_t(CommandLine.arguments[1])!
guard let app = NSRunningApplication(processIdentifier: pid),
      app.executableURL?.path == CommandLine.arguments[2],
      let icon = app.icon, let tiff = icon.tiffRepresentation,
      let bitmap = NSBitmapImageRep(data: tiff),
      let png = bitmap.representation(using: .png, properties: [:]) else {
    fatalError("No registered running icon for the task's app")
}
try png.write(to: URL(fileURLWithPath: CommandLine.arguments[3]))
'''


def main():
    load = float(subprocess.check_output(['sysctl', '-n', 'vm.loadavg'], text=True).split()[1])
    if load >= 16:
        raise SystemExit('Wait for load below 16 before the live Mac check')
    binary = ROOT / os.environ.get('CLAW_DERIVED_DATA', 'work/MacCatalyst') / 'Build/Products/Release-maccatalyst/Claw.app/Contents/MacOS/Claw'
    WORK.mkdir(parents=True, exist_ok=True)
    swift = WORK / 'read-running-icon.swift'; swift.write_text(SWIFT)
    output = WORK / 'running-mac-icon.png'
    with (WORK / 'live-mac.log').open('w') as log:
        app = subprocess.Popen([str(binary), '--mute'], cwd=ROOT, stdout=log, stderr=log)
        try:
            time.sleep(2)
            assert app.poll() is None, 'Muted Mac app exited before icon inspection'
            subprocess.run(['xcrun', 'swift', str(swift), str(app.pid), str(binary), str(output)], check=True)
        finally:
            if app.poll() is None:
                app.terminate()
                try:
                    app.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    app.kill(); app.wait()
    print(json.dumps(dict(status='pass', pid=app.pid, launch_arguments=['--mute'], registered_icon=str(output), closed_own_process=True)))


if __name__ == '__main__':
    main()
