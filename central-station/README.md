# Mission Control (ASTRA): crew health monitor

Ground-control dashboard for a NASA Space Apps project: shows suit pressure, suit temperature and
crew vitals for many astronauts on one screen, with space-weather context.

## Run
    pip install flask requests
    python3 run_all.py        # opens http://localhost:5002

## NASA API key (optional)
Copy `nasa_api_key.example.txt` to `nasa_api_key.txt` and paste your key from https://api.nasa.gov .
Without it the space-weather collector uses NASA's shared DEMO_KEY (slower updates). Never commit the real key.

## Data
Nine astronauts are simulated. One (Astronaut-5) reads a real Raspberry Pi with a Sense HAT; its heart rate,
body temperature, blood pressure and blood oxygen are simulated and labeled as such.
Limit sources and which values are placeholders are listed at the top of `server.py`.
