import os
# import datetime
# import decimal

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
# from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd, check_username, check_symbol, get_user_cash

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """ Show portfolio of stocks"""
    current_user_id = session["user_id"]
    user_stocks = db.execute(
        "SELECT share_symbol, share_name, SUM(total_shares) AS total_shares, share_price FROM user_transactions WHERE user_id = ? GROUP BY share_symbol",
        current_user_id)

    user_total_share_value = 0
    for user_stock in user_stocks:
        user_total_share_value += float(
            user_stock['share_price'] * user_stock['total_shares'])

    current_user_cash = get_user_cash(current_user_id)
    user_total_cash = current_user_cash + user_total_share_value
    return render_template("index.html", user_stocks=user_stocks, user_cash=usd(current_user_cash), total=usd(user_total_cash), usd=usd)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        quote = check_symbol(request.form.get("symbol"))
        if quote == 1:
            return apology("Please introduce a symbol", 403)
        elif quote == 2:
            return apology("Symbol not valid", 403)

        shares = request.form.get("n-shares")
        shares = int(shares)
        if shares < 1:
            return apology("Must select shares higher than 0", 403)

        current_user_id = session["user_id"]
        current_user_cash = get_user_cash(current_user_id)
        # round to 2 decimals a float#
        # total_shares_value = decimal.Decimal(quote['price'] * shares).quantize(decimal.Decimal('0.00')) #no need
        total_shares_value = (quote['price'] * shares)
        ## START TRANSACTION##
        if current_user_cash >= total_shares_value:
            # purchase_timestamp = datetime.datetime.now() #no need
            db.execute(
                "INSERT INTO user_transactions(user_id ,share_name, share_price, share_symbol, total_shares, transaction_type) VALUES (?, ?, ?, ?, ?, ?)",
                current_user_id, quote['name'], quote['price'], quote['symbol'], shares, "BUY")

            current_user_cash -= total_shares_value
            db.execute("UPDATE users SET cash = ? WHERE id = ?",
                       current_user_cash, current_user_id)
        else:
            return apology("cannot afford the number of shares at the current price.", 400)

        return redirect("/")
    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    current_user_id = session["user_id"]
    user_stocks = db.execute(
        "SELECT share_symbol, share_name, total_shares, share_price, transaction_type, date_time FROM user_transactions WHERE user_id = ?",
        current_user_id)

    for user_stock in user_stocks:
        user_stock['share_price'] = usd(user_stock['share_price'])

    return render_template("history.html", user_stocks=user_stocks)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get(
                "username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""
    # Forget any user_id
    session.clear()
    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        # print("POSTED")
        quote = check_symbol(request.form.get("symbol"))

        if quote == 1:
            return apology("Please introduce a symbol", 403)
        elif quote == 2:
            return apology("Symbol not valid", 403)

        quote.update(
            {
                "name": quote["name"],
                "price": usd(quote["price"]),
                "symbol": quote["symbol"],
            }
        )

        return render_template("quoted.html", quote=quote)
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    username = request.form.get("username")
    password = request.form.get("password")
    password_confirmation = request.form.get("confirmation")

    if request.method == "POST":
        if not username:
            return apology("Please make sure to provide an Username", 403)
        elif check_username(username):
            return apology("Username already exist", 403)

        if not password:
            return apology("Please make sure to provide a password", 403)
        elif password != password_confirmation:
            return apology("Passwords does not match", 403)

        db.execute(
            "INSERT INTO users (username, hash) VALUES (?, ?)",
            username,
            generate_password_hash(password),
        )
        flash("You were successfully Register!")
        return redirect("/")
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    current_user_id = session["user_id"]

    if request.method == "POST":
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")
        shares = int(shares)
        user_shares = db.execute(
            "SELECT SUM(total_shares) AS total_shares FROM user_transactions WHERE user_id = ? AND share_symbol = ?",
            current_user_id, symbol)[0]['total_shares']

        if not user_shares:
            return apology("User does not own such stock Symbol.")

        if shares < 1:
            return apology("Must select shares higher than 0.", 403)
        elif shares > user_shares:
            return apology("Sorry, seems you don't have enough shares to sell.")

        quote = check_symbol(symbol)
        current_user_cash = get_user_cash(current_user_id)

        ## START TRANSACTION##
        db.execute(
            "INSERT INTO user_transactions(user_id ,share_name, share_price, share_symbol, total_shares, transaction_type) VALUES (?, ?, ?, ?, ?, ?)",
            current_user_id, quote['name'], quote['price'], quote['symbol'], -shares, "SELL")

        current_user_cash += (quote['price'] * shares)
        db.execute("UPDATE users SET cash = ? WHERE id = ?",
                   current_user_cash, current_user_id)

        return redirect("/")
    else:
        user_stock_symbols = db.execute(
            "SELECT share_symbol, SUM(total_shares) AS total_shares FROM user_transactions WHERE user_id = ? GROUP BY share_symbol",
            current_user_id)
        return render_template("sell.html", user_stock_symbols=user_stock_symbols)
