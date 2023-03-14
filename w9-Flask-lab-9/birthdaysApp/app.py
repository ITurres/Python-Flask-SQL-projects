import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///birthdays.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        name = request.form.get("name")
        month = request.form.get("month")
        day = request.form.get("day")

        try:
            month = int(month)
            day = int(day)
        except ValueError:
            return render_template(
                "index.html", value_failure="Only Integers as Month and Day"
            )

        if name.isalpha() and (month >= 1 and month <= 12) and (day >= 1 and day <= 31):
            db.execute(
                "INSERT INTO birthdays (name, month, day) VALUES (?, ?, ?)",
                name,
                month,
                day,
            )
            return redirect("/")
        else:
            return render_template(
                "index.html", value_failure="Make sure to choose valid Name/Month/Day"
            )

    else:
        birthdays_data = db.execute("SELECT * FROM birthdays")
        return render_template("index.html", birthdays=birthdays_data)


@app.route("/delete", methods=["POST"])
def delete():
    id = request.form.get("id")
    if id:
        db.execute("DELETE FROM birthdays WHERE id == ?", id)
    return redirect("/")
