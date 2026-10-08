from datetime import timedelta

DOMAIN = "bundesliga"
CONF_LIGEN = "ligen"

LIGEN = {
    "bl1": "1. Bundesliga",
    "bl2": "2. Bundesliga",
    "bl3": "3. Liga",
    "dfb": "DFB-Pokal",
}
STANDARD_LIGEN = ["bl1", "bl2"]

API_URL = "https://api.openligadb.de/getmatchdata/{}"

INTERVALL_NORMAL = timedelta(minutes=10)
INTERVALL_LIVE = timedelta(minutes=1)

VORLAUF = timedelta(minutes=30)
SPIELDAUER = timedelta(minutes=150)
