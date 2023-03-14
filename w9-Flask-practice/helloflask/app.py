from flask import Flask, render_template, request

app = Flask(__name__)

COLORS = ["red", "blue"]


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return render_template("index.html")
    else:
        print("Form submitted!")
        color = request.form.get("color")
        if not color in COLORS:
            return "not allowed"
        return render_template("color.html", color=color)
