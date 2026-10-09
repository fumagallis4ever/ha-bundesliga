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

# Optionale Zweitquelle API-Football (api-sports.io)
CONF_API_KEY = "api_football_key"
APIF_URL = "https://v3.football.api-sports.io/fixtures"
APIF_STATUS_URL = "https://v3.football.api-sports.io/status"
APIF_LIGEN = {"bl1": 78, "bl2": 79, "bl3": 80, "dfb": 81}
APIF_INTERVALL = timedelta(minutes=6)  # pro Liga höchstens alle 6 Minuten – reicht für ~4 Spielfenster am Tag im Gratis-Tarif
APIF_NACHLAUF = timedelta(hours=12)  # so lange nach Anstoß wird ein fehlendes Ergebnis nachgeholt
APIF_RESERVE = 3  # verbleibende Tagesabrufe, ab denen pausiert wird
APIF_LIVE = {"1H", "HT", "2H", "ET", "BT", "P", "LIVE", "INT", "SUSP"}
APIF_BEENDET = {"FT", "AET", "PEN", "AWD", "WO"}
APIF_ABGESAGT = {"PST", "CANC", "ABD"}
