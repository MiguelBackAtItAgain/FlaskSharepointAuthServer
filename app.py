import os
import requests
from flask import Flask, jsonify, Response, request
from flask_cors import CORS 
from dotenv import load_dotenv
from functools import wraps
from urllib.parse import urlencode

load_dotenv()

TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
SITE_ID = os.getenv("SITE_ID")
LIST = os.getenv("LIST")
USERNAME = os.getenv("FLASK_USERNAME")
PASSWORD = os.getenv("PASSWORD")

app = Flask(__name__)

CORS(app, resources={r"/*": {"origins": "https://siyuanprod.us.plumsail.io"}})

def check_auth(username, password):
    return username == USERNAME and password == PASSWORD

def authenticate():
    return Response('Incorrect login credentials', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def validate_info(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return validate_info


def get_access_token():
    token_url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": "https://graph.microsoft.com/.default"
    }

    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    response = requests.post(token_url, data=urlencode(data), headers=headers)
    response_json = response.json()

    if "access_token" in response_json:
        return response_json["access_token"]
    else:
        print("Error getting token: ", response_json)
        return None

@app.route('/', methods=["GET"])
def home():
    return jsonify({"message": "The service is live!"})

@app.route('/get-courses-data', methods=['GET'])
@requires_auth
def get_sharepoint_data():
    
    token = get_access_token()

    if not token:
        return jsonify({"error": "Failed to get access token"}), 500
    
    url = f"https://graph.microsoft.com/v1.0/sites/{SITE_ID}/lists/{LIST}/items?$expand=fields($select=ID,NombreCursoEstandar,ContadorDiasGracia)"

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        items = response.json().get("value", [])
        formatted_items = [
            {
                "ID": item.get("fields", {}).get("id"),
                "NombreCursoEstandar": item.get("fields", {}).get("NombreCursoEstandar")
            }
            for item in items
            if item.get("fields", {}).get("ContadorDiasGracia") < 30
        ]
        print(len(formatted_items))
        return jsonify(formatted_items)
    else:
        return jsonify({"error": "Failed to fetch SharePoint data"}), response.status_code
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)