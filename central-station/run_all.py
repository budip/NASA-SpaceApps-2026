"""ONE-COMMAND LAUNCHER for MISSION CONTROL v2 (single-screen redesign). Starts everything in ONE Terminal window:
    server.py                (the dashboard server)
    astra_space_weather.py   (live space weather, uses nasa_api_key.txt)
    simulator.py             (9 fake astronauts)
    pi_poller.py             (the real Raspberry Pi)
then opens the dashboard in your browser.

Run:       python3 run_all.py
Stop all:  press Ctrl+C once in this window

Options (add after the command, for example:  python3 run_all.py --no-sim):
    --no-sim       do not start the fake astronauts
    --no-pi        do not start the real Pi poller
    --no-weather   do not start the live space weather collector
    --no-browser   do not open the browser automatically
"""
import argparse
import os
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = 5002
URL = f"http://localhost:{PORT}"
# Lines the server prints for every page refresh. Hidden so the window stays readable.
NOISY = ("GET /api/", "POST /update", "GET / HTTP", "GET /favicon")
COLORS = {"launcher": "\033[1m", "server": "\033[36m", "weather": "\033[35m", "sim": "\033[33m", "pi": "\033[32m"}
RESET = "\033[0m"
print_lock = threading.Lock()


def say(tag, text):
    with print_lock:
        print(f"{COLORS.get(tag, '')}[{tag:<8}]{RESET} {text}", flush=True)


class Service:
    def __init__(self, tag, script):
        self.tag, self.script = tag, script
        self.proc = None
        self.starts = []            # times we started it, to stop endless crash loops
        self.next_start = 0.0
        self.gave_up = False
        self.last_line, self.last_time = None, 0.0

    def start(self):
        env = dict(os.environ, PYTHONUNBUFFERED="1",
                   ASTRA_WEATHER_FILE=os.path.join(HERE, "astra_space_weather.json"))
        self.proc = subprocess.Popen([sys.executable, "-u", os.path.join(HERE, self.script)], cwd=HERE, env=env,
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        self.starts = [t for t in self.starts if time.time() - t < 60] + [time.time()]
        threading.Thread(target=self.pump, args=(self.proc,), daemon=True).start()

    def pump(self, proc):
        for line in proc.stdout:
            line = line.rstrip()
            if not line:
                continue
            if self.tag == "server" and any(n in line for n in NOISY) and '" 200' in line:
                continue
            now = time.time()
            if line == self.last_line and now - self.last_time < 15:
                continue                    # hide repeats of the same message
            self.last_line, self.last_time = line, now
            say(self.tag, line)

    def check(self):
        """Restart the program if it stopped, unless it keeps crashing."""
        if self.gave_up or self.proc is None or self.proc.poll() is None:
            return
        if self.next_start == 0.0:
            say("launcher", f"{self.script} stopped. Restarting in 3 seconds...")
            self.next_start = time.time() + 3
        elif time.time() >= self.next_start:
            self.next_start = 0.0
            if len(self.starts) >= 5:
                self.gave_up = True
                say("launcher", f"{self.script} keeps stopping. Not restarting it. Scroll up to see why.")
            else:
                self.start()

    def stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()


def port_in_use():
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", PORT)) == 0


def wait_for_server(seconds=20):
    for _ in range(seconds * 4):
        try:
            urllib.request.urlopen(URL + "/api/state", timeout=1).read()
            return True
        except Exception:
            time.sleep(0.25)
    return False


def main():
    ap = argparse.ArgumentParser()
    for flag in ("sim", "pi", "weather", "browser"):
        ap.add_argument("--no-" + flag, action="store_true")
    args = ap.parse_args()

    try:
        import flask, requests  # noqa: F401
    except ImportError as e:
        say("launcher", f"Missing helper program: {e.name}")
        say("launcher", "Run this once, then try again:   python3 -m pip install flask requests")
        return 1
    need = ["server.py", "dashboard.html"] + ([] if args.no_weather else ["astra_space_weather.py"]) \
        + ([] if args.no_sim else ["simulator.py"]) + ([] if args.no_pi else ["pi_poller.py"])
    missing = [f for f in need if not os.path.exists(os.path.join(HERE, f))]
    if missing:
        say("launcher", "These files are missing from this folder: " + ", ".join(missing))
        return 1
    if port_in_use():
        say("launcher", f"Something is already using port {PORT}. A copy of this v2 program is probably still running.")
        say("launcher", "Quit Terminal (Terminal menu > Quit Terminal > Terminate), reopen it, and try again.")
        return 1

    server = Service("server", "server.py")
    others = []
    if not args.no_weather:
        others.append(Service("weather", "astra_space_weather.py"))
    if not args.no_sim:
        others.append(Service("sim", "simulator.py"))
    if not args.no_pi:
        others.append(Service("pi", "pi_poller.py"))
    services = [server] + others

    say("launcher", "Starting: " + ", ".join(s.tag for s in services) + "   (Ctrl+C stops everything)")
    server.start()
    if not wait_for_server():
        say("launcher", "The server did not start. Scroll up to see the error.")
        server.stop()
        return 1
    for s in others:
        s.start()
    say("launcher", f"Dashboard is ready: {URL}")
    if not args.no_browser:
        webbrowser.open(URL)

    last_beat = time.time()
    try:
        while True:
            for s in services:
                s.check()
            if time.time() - last_beat > 60:
                last_beat = time.time()
                alive = [s.tag for s in services if s.proc and s.proc.poll() is None]
                say("launcher", "Running: " + ", ".join(alive))
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    say("launcher", "Stopping everything...")
    for s in services:
        s.stop()
    deadline = time.time() + 4
    for s in services:
        while s.proc and s.proc.poll() is None and time.time() < deadline:
            time.sleep(0.1)
        if s.proc and s.proc.poll() is None:
            s.proc.kill()
    say("launcher", "Stopped. You can close this window.")
    return 0


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, lambda *a: (_ for _ in ()).throw(KeyboardInterrupt()))
    sys.exit(main())
