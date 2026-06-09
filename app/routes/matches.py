from flask import Blueprint, jsonify
import requests

matches_api = Blueprint('matches_api', __name__)

# TheSportsDB API gratuita
API_KEY = "1"  # la key gratuita
LEAGUE_ID = "4424"  # ID de la liga del Mundial (ajustar si hay actualización)

@matches_api.route('/api/partidos', methods=['GET'])
def get_worldcup_matches():
    url = f"https://www.thesportsdb.com/api/v1/json/{API_KEY}/eventsnextleague.php"
    params = {"id": LEAGUE_ID}
    response = requests.get(url, params=params)
    data = response.json()
    
    partidos = []
    for event in data.get("events", []):
        partidos.append({
            "fecha": event.get("dateEvent"),
            "hora": event.get("strTime"),
            "local": event.get("strHomeTeam"),
            "visitante": event.get("strAwayTeam"),
            "estadio": event.get("strVenue"),
            "round": event.get("intRound")
        })
    
    return jsonify(partidos)