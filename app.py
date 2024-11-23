import os
import sqlite3
import pytz
from flask import Flask, request, jsonify
from datetime import datetime
import requests
from flasgger import Swagger
from flask_cors import CORS

# Initialize Flask app
app = Flask(__name__)
swagger = Swagger(app)
CORS(app, resources={r"/*": {"origins": "*"}})

IST = pytz.timezone('Asia/Kolkata')

start_time_obj=""

# Database Initialization Function
def init_db():
    conn = sqlite3.connect('assessment.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS assessments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assessment_start_time TEXT,
            assessment_end_time TEXT,
            total_time INTEGER,
            assessment_id INTEGER
        )
    ''')
    conn.commit()
    conn.close()

# Function to get GitHub repository fork time (as assessment_start_time)
def get_github_fork_time():
    try:
        token = os.environ.get('GITHUB_TOKEN')  # Replace with your GitHub token if needed
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

# API Route to Start Assessment
@app.route('/start_assessment', methods=['GET'])
def start_assessment():
    """
    Start the assessment by fetching the GitHub fork time.
    --- 
    responses:
        200:
            description: Assessment started successfully.
            schema:
                type: object
                properties:
                    message:
                        type: string
                        example: "Assessment started successfully."
                    assessment_start_time:
                        type: string
                        example: "2024-11-23T13:45:00Z"
        500:
            description: Error in fetching GitHub data.
    """
    start_time = get_github_fork_time()
    start_time_obj=start_time
    if not start_time:
        return jsonify({"error": "Unable to fetch GitHub fork time."}), 500
    
    # Save start time in the database
    with sqlite3.connect('assessment.db') as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO assessments (assessment_start_time) VALUES (?)", (start_time,))
        conn.commit()

    return jsonify({
        "message": "Assessment started successfully.",
        "assessment_start_time": start_time
    })

# API Route to Complete Assessment
@app.route('/complete_assessment', methods=['POST'])
def complete_assessment():
    """
    Complete the assessment by providing the end time.
    ---
    parameters:
        - name: assessment_end_time
          in: formData
          description: The end time in ISO 8601 format
          required: true
          type: string
          example: "2024-11-23T14:45:00Z"
    responses:
        200:
            description: Assessment completed successfully.
            schema:
                type: object
                properties:
                    message:
                        type: string
                        example: "Assessment completed successfully."
                    assessment_end_time:
                        type: string
                        example: "2024-11-23T14:45:00Z"
                    total_time:
                        type: integer
                        example: 3600
        400:
            description: Invalid request or missing parameters.
        404:
            description: No ongoing assessment found.
    """
    assessment_end_time = request.form.get('assessment_end_time')


    # Parse the end time

    end_time_obj = assessment_end_time.split("T")[1].rstrip('Z')

    print(end_time_obj)
       


    return jsonify({
        "message": "Assessment completed successfully.",
        "assessment_end_time": assessment_end_time,
    })

# Initialize the database
init_db()

if __name__ == "__main__":
    app.run(debug=True)
