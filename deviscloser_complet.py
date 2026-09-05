import os
from flask import Flask
app = Flask(__name__)
@app.route("/")
def home():
    return "Devis Closer OK - MoMo 01 56 85 31 49 - Sosthene EDOH - v23 FIXED"
@app.route("/health")
def health():
    return "OK"
