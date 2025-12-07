from main import app as application   # or your actual flask file
from flask import Flask, jsonify

app = Flask(__name__)

@app.route("/")
def home():
    return jsonify({"status": "success", "message": "Flask on Vercel working!"})
