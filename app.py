from flask import Flask, render_template, jsonify
import main as main
import threading

app = Flask(__name__)

threadProcessing = threading.Thread(target=main.main)
threadProcessing.daemon = True
threadProcessing.start()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/get_data")
def get_data():
    return jsonify(main.networkData)


if __name__ == "__main__":
    app.run(debug=True)
