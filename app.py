import sqlite3
from flask import Flask, request, jsonify
import requests
from datetime import datetime
import os
from flasgger import Swagger
import pytz
from flask_cors import CORS

# Initialize Flask app
app = Flask(__name__)
swagger = Swagger(app)
CORS(app, resources={r"/*": {"origins": "*"}}) 

IST = pytz.timezone('Asia/Kolkata')

def init_db():
    conn = sqlite3.connect('timer.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS timer (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_time TEXT,
            end_time TEXT,
            total_time INTEGER
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/')
def home():
    return "Welcome to the API"


def get_github_fork_time():
    try:
        token = os.environ.get('GITHUB_TOKEN')
        url = "https://api.github.com/repos/Sravaniyenumala/fs-assessment"
        headers = {
            'Authorization': f'token {token}'
        }
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            repo_details = response.json()
            fork_created_at = repo_details.get('created_at')
            if fork_created_at:
                utc_time = datetime.strptime(fork_created_at, '%Y-%m-%dT%H:%M:%SZ')
                utc_time = pytz.utc.localize(utc_time)  
                ist_time = utc_time.astimezone(IST) 
                return ist_time.strftime('%Y-%m-%dT%H:%M:%S') 
            else:
                print("Could not find 'created_at' timestamp for this repository.")
                return None
        else:
            print(f"Error fetching repository details: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error: {str(e)}")
        return None

@app.route('/start_assessment', methods=['GET'])
def start_assessment():
    """
    This endpoint retrives start time from github
    ---
    responses:
        200:
            description: Assessment started successfully
            schema:
                type: object
                properties:
                    message:
                        type: string
                        example: Assessment started
                    start_time:
                        type: string
                        example: "2024-11-23T13:45:00Z"
        500:
            description: Unable to fetch GitHub fork time
            schema:
                type: object
                properties:
                    error:
                        type: string
                        example: Unable to fetch GitHub fork time.
    """
    fork_time = get_github_fork_time()
    if not fork_time:
        return jsonify({"error": "Unable to fetch GitHub fork time."}), 500
   
    conn = sqlite3.connect('timer.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO timer (start_time) VALUES (?)", (fork_time,))
    conn.commit()
    conn.close()
    
    return jsonify({"message": "Assessment started", "start_time": fork_time})

@app.route('/complete_assessment', methods=['POST'])
def complete_assessment():
    """
    Complete the assessment by providing the end time.
    ---
    parameters:
        - name: end_time
          in: body
          description: The end time in ISO 8601 format
          required: true
          schema:
            type: string
            format: date-time
            example: "2024-11-23T14:45:00Z"
    responses:
        200:
            description: Assessment completed successfully
            schema:
                type: object
                properties:
                    message:
                        type: string
                        example: "Assessment completed"
                    end_time:
                        type: string
                        example: "2024-11-23T14:45:00Z"
                    total_time:
                        type: integer
                        example: 3600
        400:
            description: Invalid request format or missing parameters
        404:
            description: No ongoing assessment found
    """
    data = request.get_json(silent=True)
    if not request.is_json or not data or 'end_time' not in data:
        return jsonify({"error": "End time is required in JSON format"}), 400

    end_time = data['end_time']
    print(f"Received end_time: {end_time}")  # Log the end_time for debugging purposes

    try:
        # Try parsing the end_time with different formats
        end_time_obj = datetime.strptime(end_time, '%Y-%m-%dT%H:%M:%S')
        end_time_obj = IST.localize(end_time_obj) if end_time_obj.tzinfo is None else end_time_obj
    except ValueError as e:
        # Log the error for debugging
        print(f"Error parsing end_time: {str(e)}")
        return jsonify({"error": "Invalid end_time format. Use ISO 8601 format like '2024-11-23T14:45:00Z'"}), 400

    with sqlite3.connect('timer.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, start_time FROM timer WHERE end_time IS NULL ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()

        if not row:
            return jsonify({"error": "No ongoing assessment found."}), 404

        assessment_id, start_time = row
        try:
            start_time_obj = datetime.strptime(start_time, '%Y-%m-%dT%H:%M:%S')
            start_time_obj = IST.localize(start_time_obj) if start_time_obj.tzinfo is None else start_time_obj
        except ValueError:
            return jsonify({"error": "Invalid start_time format in database"}), 500

        total_time = int((end_time_obj - start_time_obj).total_seconds())
        cursor.execute("UPDATE timer SET end_time = ?, total_time = ? WHERE id = ?", 
                       (end_time, total_time, assessment_id))

    return jsonify({
        "message": "Assessment completed",
        "end_time": end_time,
        "total_time": total_time
    })

init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
