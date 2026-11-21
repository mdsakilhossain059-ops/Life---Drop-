import os
import psycopg
from psycopg.rows import dict_row

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, g, send_from_directory
)
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "change-this-secret-before-public-launch"
)

DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is missing in Render Environment")


# ==============================
# DATABASE CONNECTION
# ==============================

def db():
    if "db" not in g:
        g.db = psycopg.connect(
            DATABASE_URL,
            sslmode="require",
            row_factory=dict_row
        )
    return g.db


@app.teardown_appcontext
def close_db(exc):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


# ==============================
# DATABASE TABLES
# ==============================

def init_db():
    with app.app_context():
        c = db()

        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id BIGSERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                phone TEXT NOT NULL,
                blood TEXT NOT NULL,
                district TEXT NOT NULL,
                upazila TEXT NOT NULL,
                available INTEGER DEFAULT 1
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS requests (
                id BIGSERIAL PRIMARY KEY,
                patient TEXT NOT NULL,
                blood TEXT NOT NULL,
                district TEXT NOT NULL,
                upazila TEXT NOT NULL,
                hospital TEXT NOT NULL,
                phone TEXT NOT NULL,
                details TEXT
            )
        """)

        c.commit()


init_db()


# ==============================
# PWA MANIFEST
# ==============================

@app.route("/manifest.json")
def manifest():
    response = send_from_directory(
        app.root_path,
        "manifest.json",
        mimetype="application/manifest+json"
    )
    response.headers["Cache-Control"] = "no-cache"
    return response


# ==============================
# PWA SERVICE WORKER
# ==============================

@app.route("/sw.js")
def service_worker():
    response = send_from_directory(
        app.static_folder,
        "sw.js",
        mimetype="application/javascript"
    )

    response.headers["Service-Worker-Allowed"] = "/"
    response.headers["Cache-Control"] = "no-cache"

    return response


# ==============================
# INSTALL APP ON ALL HTML PAGES
# ==============================

@app.after_request
def add_install_button_to_all_pages(response):

    if (
        response.status_code != 200
        or response.mimetype != "text/html"
        or response.direct_passthrough
    ):
        return response

    html = response.get_data(as_text=True)

    # Manifest link for every page
    if 'rel="manifest"' not in html.lower():

        manifest_link = """
        <link rel="manifest" href="/manifest.json">
        <meta name="theme-color" content="#dc2626">
        """

        if "</head>" in html.lower():
            pos = html.lower().rfind("</head>")
            html = html[:pos] + manifest_link + html[pos:]

    # Add install button
    if 'id="life-drop-global-install"' not in html:

        install_code = """
<style>
#life-drop-global-install {
    position: fixed;
    bottom: 20px;
    right: 15px;
    z-index: 999999;
    background: #dc2626;
    color: white;
    border: none;
    border-radius: 30px;
    padding: 13px 19px;
    font-size: 15px;
    font-weight: bold;
    cursor: pointer;
    box-shadow: 0 4px 12px rgba(0,0,0,.25);
}

#life-drop-global-install:active {
    transform: scale(.96);
}
</style>

<button
    id="life-drop-global-install"
    type="button"
    aria-label="Install Life Drop App">
    📲 অ্যাপ ইনস্টল করুন
</button>

<script>
(function() {

    const btn = document.getElementById(
        'life-drop-global-install'
    );

    if (!btn) return;

    let deferredPrompt = null;

    function isInstalled() {
        return (
            window.matchMedia(
                '(display-mode: standalone)'
            ).matches ||
            window.navigator.standalone === true
        );
    }

    if (isInstalled()) {
        btn.style.display = 'none';
        return;
    }

    // Capture browser installation prompt
    window.addEventListener(
        'beforeinstallprompt',
        function(event) {

            event.preventDefault();

            deferredPrompt = event;

            btn.style.display = 'block';
        }
    );

    // Install button
    btn.addEventListener('click', async function() {

        if (deferredPrompt) {

            deferredPrompt.prompt();

            try {
                const result = await deferredPrompt.userChoice;

                if (result.outcome === 'accepted') {
                    btn.style.display = 'none';
                }
            } catch(error) {
                console.error(error);
            }

            deferredPrompt = null;

        } else {

            alert(
                'Chrome-এর উপরের তিন ডট মেনুতে যান। ' +
                'Install app অথবা Add to Home screen নির্বাচন করুন।'
            );

        }
    });

    // After installation
    window.addEventListener('appinstalled', function() {

        btn.style.display = 'none';

        deferredPrompt = null;

    });

    // Register service worker for the entire website
    if ('serviceWorker' in navigator) {

        window.addEventListener('load', function() {

            navigator.serviceWorker.register('/sw.js', {
                scope: '/'
            }).catch(function(error) {

                console.error(
                    'Service Worker Error:', error
                );

            });

        });

    }

})();
</script>
"""

        if "</body>" in html.lower():

            pos = html.lower().rfind("</body>")

            html = (
                html[:pos]
                + install_code
                + html[pos:]
            )

    response.set_data(html)

    return response


# ==============================
# DISTRICTS AND BLOOD GROUPS
# ==============================

DISTRICTS = """Bagerhat, Bandarban, Barguna, Barishal, Bhola, Bogura, Brahmanbaria, Chandpur, Chapainawabganj, Chattogram, Chuadanga, Cox's Bazar, Cumilla, Dhaka, Dinajpur, Faridpur, Feni, Gaibandha, Gazipur, Gopalganj, Habiganj, Jamalpur, Jashore, Jhalokati, Jhenaidah, Joypurhat, Khagrachhari, Khulna, Kishoreganj, Kurigram, Kushtia, Lakshmipur, Lalmonirhat, Madaripur, Magura, Manikganj, Meherpur, Moulvibazar, Munshiganj, Mymensingh, Naogaon, Narail, Narayanganj, Narsingdi, Natore, Netrokona, Nilphamari, Noakhali, Pabna, Panchagarh, Patuakhali, Pirojpur, Rajbari, Rajshahi, Rangamati, Rangpur, Satkhira, Shariatpur, Sherpur, Sirajganj, Sunamganj, Sylhet, Tangail, Thakurgaon""".split(", ")

BLOOD = [
    "A+", "A-", "B+", "B-",
    "AB+", "AB-", "O+", "O-"
]


# ==============================
# HOME PAGE
# ==============================

@app.route("/")
def home():
    return render_template(
        "index.html",
        districts=DISTRICTS,
        blood=BLOOD
    )


# ==============================
# USER REGISTRATION
# ==============================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        f = request.form

        try:

            db().execute(
                """
                INSERT INTO users
                (name, email, password, phone, blood, district, upazila)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    f["name"].strip(),
                    f["email"].strip().lower(),
                    generate_password_hash(f["password"]),
                    f["phone"].strip(),
                    f["blood"],
                    f["district"],
                    f["upazila"].strip()
                )
            )

            db().commit()

            flash("নিবন্ধন সফল হয়েছে। এখন লগইন করুন।")

            return redirect(url_for("login"))

        except psycopg.errors.UniqueViolation:

            db().rollback()

            flash("এই ইমেইল দিয়ে আগে অ্যাকাউন্ট খোলা হয়েছে।")

    return render_template(
        "register.html",
        districts=DISTRICTS,
        blood=BLOOD
    )


# ==============================
# USER LOGIN
# ==============================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"].strip().lower()
        password = request.form["password"]

        u = db().execute(
            "SELECT * FROM users WHERE email = %s",
            (email,)
        ).fetchone()

        if u and check_password_hash(u["password"], password):

            session["uid"] = u["id"]

            return redirect(url_for("home"))

        flash("ইমেইল অথবা পাসওয়ার্ড সঠিক নয়।")

    return render_template("login.html")


# ==============================
# USER LOGOUT
# ==============================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("home"))


# ==============================
# DONOR LIST
# ==============================

@app.route("/donors")
def donors():

    if not session.get("uid"):
        return render_template("login_required.html")

    blood = request.args.get("blood", "")
    district = request.args.get("district", "")

    sql = """
        SELECT name, blood, district, upazila, phone
        FROM users
        WHERE available = 1
    """

    args = []

    if blood:
        sql += " AND blood = %s"
        args.append(blood)

    if district:
        sql += " AND district = %s"
        args.append(district)

    sql += " ORDER BY district, name"

    rows = db().execute(sql, args).fetchall()

    return render_template(
        "donors.html",
        donors=rows,
        districts=DISTRICTS,
        blood=BLOOD
    )


# ==============================
# DONOR AVAILABILITY
# ==============================

@app.route("/availability", methods=["POST"])
def availability():

    if not session.get("uid"):
        return redirect(url_for("login"))

    available = 1 if request.form.get("available") else 0

    db().execute(
        "UPDATE users SET available = %s WHERE id = %s",
        (available, session["uid"])
    )

    db().commit()

    return redirect(url_for("home"))


# ==============================
# BLOOD REQUEST FORM
# ==============================

@app.route("/request", methods=["GET", "POST"])
def request_blood():

    if not session.get("uid"):
        return render_template("login_required.html")

    if request.method == "POST":

        f = request.form

        db().execute(
            """
            INSERT INTO requests
            (patient, blood, district, upazila, hospital, phone, details)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                f["patient"],
                f["blood"],
                f["district"],
                f["upazila"],
                f["hospital"],
                f["phone"],
                f.get("details", "")
            )
        )

        db().commit()

        flash("রক্তের অনুরোধ প্রকাশ হয়েছে।")

        return redirect(url_for("requests"))

    return render_template(
        "request.html",
        districts=DISTRICTS,
        blood=BLOOD
    )


# ==============================
# BLOOD REQUEST LIST
# ==============================

@app.route("/requests")
def requests():

    if not session.get("uid"):
        return render_template("login_required.html")

    rows = db().execute(
        "SELECT * FROM requests ORDER BY id DESC"
    ).fetchall()

    return render_template(
        "requests.html",
        requests=rows
    )


# ==============================
# RUN APPLICATION
# ==============================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False
)
        
