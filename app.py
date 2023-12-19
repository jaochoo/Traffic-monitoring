from flask import Flask, render_template, jsonify
import main as main
import threading
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:password@localhost/netdb'  # Use the correct database URI for your setup
db = SQLAlchemy(app)

threadProcessing = threading.Thread(target=main.main)
threadProcessing.daemon = True
threadProcessing.start()

# SNMP target device information
target = "135.181.197.1"  # IP address of snmplabs.thola.io, a public SNMP testing device
community = "public"  # SNMP community string for authentication

class Log(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())
    traffic_data = db.Column(db.String(5000))  # Adjust the size as needed

with app.app_context():
    db.create_all()

@app.route("/")
def index():
    return render_template("index.html")

import json

@app.route("/get_data")
def get_data():
    traffic_data = main.fetch_traffic_data(target, community)
    traffic_data_str = json.dumps(traffic_data)
    log_entry = Log(traffic_data=traffic_data_str)
    db.session.add(log_entry)
    db.session.commit()
    return jsonify(traffic_data)

if __name__ == "__main__":
    app.run(debug=True)
