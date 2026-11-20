
import os, sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash, g, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-before-public-launch")
DB = os.environ.get("DATABASE_PATH", "life_drop.db")

@app.route("/manifest.json")
def manifest():
    return send_from_directory(
        app.root_path,
        "manifest.json",
        mimetype="application/manifest+json"
    )

def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exc):
    conn = g.pop("db", None)
    if conn:
        conn.close()

def init_db():
    with app.app_context():
        c = db()
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users(
          id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
          email TEXT UNIQUE NOT NULL, password TEXT NOT NULL,
          phone TEXT NOT NULL, blood TEXT NOT NULL, district TEXT NOT NULL,
          upazila TEXT NOT NULL, available INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS requests(
          id INTEGER PRIMARY KEY AUTOINCREMENT, patient TEXT NOT NULL,
          blood TEXT NOT NULL, district TEXT NOT NULL, upazila TEXT NOT NULL,
          hospital TEXT NOT NULL, phone TEXT NOT NULL, details TEXT
        );
        """)
        c.commit()

init_db()

DISTRICTS = """Bagerhat, Bandarban, Barguna, Barishal, Bhola, Bogura, Brahmanbaria, Chandpur, Chapainawabganj, Chattogram, Chuadanga, Cox's Bazar, Cumilla, Dhaka, Dinajpur, Faridpur, Feni, Gaibandha, Gazipur, Gopalganj, Habiganj, Jamalpur, Jashore, Jhalokati, Jhenaidah, Joypurhat, Khagrachhari, Khulna, Kishoreganj, Kurigram, Kushtia, Lakshmipur, Lalmonirhat, Madaripur, Magura, Manikganj, Meherpur, Moulvibazar, Munshiganj, Mymensingh, Naogaon, Narail, Narayanganj, Narsingdi, Natore, Netrokona, Nilphamari, Noakhali, Pabna, Panchagarh, Patuakhali, Pirojpur, Rajbari, Rajshahi, Rangamati, Rangpur, Satkhira, Shariatpur, Sherpur, Sirajganj, Sunamganj, Sylhet, Tangail, Thakurgaon""".split(", ")

BLOOD = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]

@app.route("/")
def home():
    return render_template("index.html", districts=DISTRICTS, blood=BLOOD)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        f = request.form
        try:
            db().execute(
                "INSERT INTO users(name,email,password,phone,blood,district,upazila) VALUES(?,?,?,?,?,?,?)",
                (f["name"], f["email"].lower(), generate_password_hash(f["password"]),
                 f["phone"], f["blood"], f["district"], f["upazila"])
            )
            db().commit()
            flash("নিবন্ধন সফল হয়েছে। এখন লগইন করুন।")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("এই ইমেইল দিয়ে আগে অ্যাকাউন্ট খোলা হয়েছে।")
    return render_template("register.html", districts=DISTRICTS, blood=BLOOD)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = db().execute(
            "SELECT * FROM users WHERE email=?",
            (request.form["email"].lower(),)
        ).fetchone()

        if u and check_password_hash(u["password"], request.form["password"]):
            session["uid"] = u["id"]
            return redirect(url_for("home"))

        flash("ইমেইল অথবা পাসওয়ার্ড সঠিক নয়।")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/donors")
def donors():
    if not session.get("uid"):
        flash("তালিকা দেখতে নিবন্ধন করুন।")
        return redirect(url_for("register"))

    blood = request.args.get("blood", "")
    district = request.args.get("district", "")
    sql = "SELECT name,blood,district,upazila,phone FROM users WHERE available=1"
    args = []

    if blood:
        sql += " AND blood=?"
        args.append(blood)

    if district:
        sql += " AND district=?"
        args.append(district)

    rows = db().execute(sql + " ORDER BY district,name", args).fetchall()

    return render_template(
        "donors.html",
        donors=rows,
        districts=DISTRICTS,
        blood=BLOOD
    )

@app.route("/availability", methods=["POST"])
def availability():
    if not session.get("uid"):
        return redirect(url_for("login"))

    db().execute(
        "UPDATE users SET available=? WHERE id=?",
        (1 if request.form.get("available") else 0, session["uid"])
    )
    db().commit()
    return redirect(url_for("home"))

@app.route("/request", methods=["GET", "POST"])
def request_blood():
    if request.method == "POST":
        f = request.form
        db().execute(
            "INSERT INTO requests(patient,blood,district,upazila,hospital,phone,details) VALUES(?,?,?,?,?,?,?)",
            (f["patient"], f["blood"], f["district"], f["upazila"],
             f["hospital"], f["phone"], f.get("details", ""))
        )
        db().commit()
        flash("রক্তের অনুরোধ প্রকাশ হয়েছে।")
        return redirect(url_for("requests"))

    return render_template("request.html", districts=DISTRICTS, blood=BLOOD)

@app.route("/requests")
def requests():
    if not session.get("uid"):
        flash("তালিকা দেখতে নিবন্ধন করুন।")
        return redirect(url_for("register"))

    rows = db().execute(
        "SELECT * FROM requests ORDER BY id DESC"
    ).fetchall()

    return render_template("requests.html", requests=rows)

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False
        )
    
