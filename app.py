import csv
import io
import os
import secrets
import sqlite3
import psycopg
from psycopg.rows import dict_row
from flask import Flask, jsonify, render_template, request, redirect, url_for, session, Response

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")
DATABASE_URL = os.environ.get("DATABASE_URL")
DB = os.path.join(os.path.dirname(__file__), "key_club.db")
USE_POSTGRES = bool(DATABASE_URL)
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "change-moi")
PARTICIPATION_FEE = "5 €"
DEFAULT_CAPACITY = 20

# Horaires provisoires : ils pourront être remplacés par les vrais horaires.
SCHEDULE = {
    "brawl-stars": {
        "Lundi": ("09:00", "10:00"), "Mardi": ("10:00", "11:00"),
        "Mercredi": ("14:00", "15:00"), "Jeudi": ("15:00", "16:00")},
    "fifa": {
        "Lundi": ("10:00", "11:00"), "Mardi": ("11:00", "12:00"),
        "Mercredi": ("15:00", "16:00"), "Jeudi": ("16:00", "17:00")},
    "echecs": {
        "Lundi": ("09:00", "10:00"), "Mardi": ("11:00", "12:00"),
        "Mercredi": ("14:00", "15:00"), "Jeudi": ("16:00", "17:00")},
    "mario-kart": {
        "Lundi": ("09:00", "10:00"), "Mardi": ("10:00", "11:00"),
        "Mercredi": ("14:00", "15:00"), "Jeudi": ("15:00", "16:00")},
    "dominos": {
        "Lundi": ("11:00", "12:00"), "Mardi": ("12:00", "13:00"),
        "Mercredi": ("15:00", "16:00"), "Jeudi": ("17:00", "18:00")},
    "call-of-duty-mobile": {
        "Lundi": ("11:00", "12:00"), "Mardi": ("12:00", "13:00"),
        "Mercredi": ("16:00", "17:00"), "Jeudi": ("17:00", "18:00")},
}

GAME_IMAGES = {
    "brawl-stars": "/static/images/brawl-stars.png",
    "fifa": "https://upload.wikimedia.org/wikipedia/commons/5/5c/FIFA_series_logo.png",
    "echecs": "https://upload.wikimedia.org/wikipedia/commons/9/98/Chess_pictogram.png",
    "mario-kart": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c1/Mario_Kart_logo.png/960px-Mario_Kart_logo.png",
    "dominos": "https://cdn-icons-png.flaticon.com/512/8936/8936624.png",
    "call-of-duty-mobile": "https://commons.wikimedia.org/wiki/Special:FilePath/Call_of_Duty_Mobile_2023_Logo.png",
}


class DBConnection:
    """Utilise PostgreSQL sur Render et SQLite en local."""
    def __init__(self):
        self.postgres = USE_POSTGRES
        if self.postgres:
            self.conn = psycopg.connect(DATABASE_URL, row_factory=dict_row)
        else:
            self.conn = sqlite3.connect(DB)
            self.conn.row_factory = sqlite3.Row
            self.conn.execute("PRAGMA foreign_keys = ON")

    def _sql(self, query):
        return query.replace("?", "%s") if self.postgres else query

    def execute(self, query, params=()):
        return self.conn.execute(self._sql(query), params)

    def executemany(self, query, params):
        return self.conn.executemany(self._sql(query), params)

    def executescript(self, script):
        if self.postgres:
            for statement in script.split(";"):
                statement = statement.strip()
                if statement:
                    self.conn.execute(statement)
        else:
            self.conn.executescript(script)

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        self.conn.close()


def get_db():
    return DBConnection()


def normalize(value):
    return " ".join(value.strip().split()).casefold()


def init_db():
    conn = get_db()
    schema_name = "schema_postgres.sql" if USE_POSTGRES else "schema.sql"
    with open(os.path.join(os.path.dirname(__file__), schema_name), encoding="utf-8") as f:
        conn.executescript(f.read())

    # Migration de la V3 si une ancienne base SQLite existe déjà.
    if not USE_POSTGRES:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(game_days)").fetchall()}
        if "start_time" not in columns:
            conn.execute("ALTER TABLE game_days ADD COLUMN start_time TEXT")
        if "end_time" not in columns:
            conn.execute("ALTER TABLE game_days ADD COLUMN end_time TEXT")
    conn.execute("DROP INDEX IF EXISTS one_active_registration_per_person")

    game_seed = [
        ("Brawl Stars", "brawl-stars", "Affronte les autres joueurs sur Brawl Stars."),
        ("FIFA", "fifa", "Un tournoi FIFA pour départager les meilleurs."),
        ("Échecs", "echecs", "Affronte un autre joueur sur l'échiquier."),
        ("Mario Kart", "mario-kart", "Course et compétition sur Mario Kart."),
        ("Dominos", "dominos", "Un moment de compétition autour des dominos."),
        ("Call of Duty: Mobile", "call-of-duty-mobile", "Affronte les autres joueurs sur Call of Duty: Mobile."),
    ]
    for name, slug, description in game_seed:
        if not conn.execute("SELECT 1 FROM games WHERE slug=?", (slug,)).fetchone():
            conn.execute("INSERT INTO games(name, slug, description) VALUES (?, ?, ?)", (name, slug, description))

    if conn.execute("SELECT COUNT(*) AS count FROM event_days").fetchone()["count"] == 0:
        conn.executemany(
            "INSERT INTO event_days(label, event_date) VALUES (?, ?)",
            [
                ("Lundi", "2026-09-07"),
                ("Mardi", "2026-09-08"),
                ("Mercredi", "2026-09-09"),
                ("Jeudi", "2026-09-10"),
            ],
        )

    games = conn.execute("SELECT id, slug FROM games ORDER BY id").fetchall()
    days = conn.execute("SELECT id, label FROM event_days ORDER BY id").fetchall()
    for g in games:
        for d in days:
            exists = conn.execute("SELECT 1 FROM game_days WHERE game_id=? AND day_id=?", (g["id"], d["id"])).fetchone()
            if not exists:
                start, end = SCHEDULE.get(g["slug"], {}).get(d["label"], ("10:00", "11:00"))
                conn.execute(
                    "INSERT INTO game_days(game_id, day_id, capacity, start_time, end_time) VALUES (?, ?, ?, ?, ?)",
                    (g["id"], d["id"], DEFAULT_CAPACITY, start, end),
                )

    # Les créneaux historiques restent intacts. On ne corrige que des capacités
    # invalides/nulles et les horaires manquants, sans toucher aux inscriptions.
    rows = conn.execute("""
        SELECT gd.id, gd.capacity, gd.start_time, gd.end_time, g.slug, d.label
        FROM game_days gd
        JOIN games g ON g.id = gd.game_id
        JOIN event_days d ON d.id = gd.day_id
    """).fetchall()
    for row in rows:
        start, end = SCHEDULE.get(row["slug"], {}).get(row["label"], ("10:00", "11:00"))
        capacity = row["capacity"] if row["capacity"] and row["capacity"] > 0 else DEFAULT_CAPACITY
        if not row["start_time"] or not row["end_time"] or capacity != row["capacity"]:
            conn.execute("UPDATE game_days SET capacity=?, start_time=?, end_time=? WHERE id=?", (capacity, row["start_time"] or start, row["end_time"] or end, row["id"]))

    conn.commit()
    conn.close()


def get_games():
    conn = get_db()
    rows = conn.execute("""
        SELECT g.id, g.name, g.slug, g.description,
               COALESCE(SUM(CASE WHEN gd.capacity - COUNTS.registered > 0 THEN 1 ELSE 0 END), 0) AS available_days,
               COALESCE(SUM(gd.capacity), 0) AS total_capacity
        FROM games g
        LEFT JOIN game_days gd ON gd.game_id = g.id
        LEFT JOIN (
            SELECT game_day_id, COUNT(*) AS registered
            FROM registrations
            GROUP BY game_day_id
        ) AS COUNTS ON COUNTS.game_day_id = gd.id
        GROUP BY g.id
        ORDER BY g.id
    """).fetchall()
    conn.close()
    games = []
    for row in rows:
        game = dict(row)
        game["image_url"] = GAME_IMAGES.get(game["slug"], "")
        game["participation_fee"] = PARTICIPATION_FEE
        games.append(game)
    return games


def get_game(slug):
    conn = get_db()
    game = conn.execute("SELECT * FROM games WHERE slug = ?", (slug,)).fetchone()
    if not game:
        conn.close()
        return None, []
    days = conn.execute("""
        SELECT gd.id, gd.capacity, gd.start_time, gd.end_time,
               d.id AS day_id, d.label, d.event_date,
               COUNT(r.id) AS registered,
               gd.capacity - COUNT(r.id) AS remaining
        FROM game_days gd
        JOIN event_days d ON d.id = gd.day_id
        LEFT JOIN registrations r ON r.game_day_id = gd.id
        WHERE gd.game_id = ?
        GROUP BY gd.id
        ORDER BY d.event_date
    """, (game["id"],)).fetchall()
    conn.close()
    game = dict(game)
    game["image_url"] = GAME_IMAGES.get(game["slug"], "")
    game["participation_fee"] = PARTICIPATION_FEE
    return game, [dict(r) for r in days]


def current_registrations():
    person = session.get("person")
    if not person:
        return []
    conn = get_db()
    rows = conn.execute("""
        SELECT r.id, r.first_name, r.last_name, r.class_name, r.cancel_token,
               g.name AS game_name, g.slug AS game_slug,
               d.id AS day_id, d.label, d.event_date,
               gd.start_time, gd.end_time
        FROM registrations r
        JOIN game_days gd ON gd.id = r.game_day_id
        JOIN games g ON g.id = gd.game_id
        JOIN event_days d ON d.id = gd.day_id
        WHERE r.first_name = ? AND r.last_name = ? AND r.class_name = ?
        ORDER BY d.event_date, g.id
    """, (person["first_name"], person["last_name"], person["class_name"])).fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.context_processor
def navigation_context():
    """Expose whether the current person has active registrations for the navbar."""
    return {"nav_has_registrations": bool(current_registrations())}


def same_day_registration(first_name, last_name, class_name, day_id):
    conn = get_db()
    row = conn.execute("""
        SELECT r.id, r.cancel_token, g.name AS game_name, d.label, d.event_date
        FROM registrations r
        JOIN game_days gd ON gd.id = r.game_day_id
        JOIN games g ON g.id = gd.game_id
        JOIN event_days d ON d.id = gd.day_id
        WHERE r.first_name=? AND r.last_name=? AND r.class_name=? AND gd.day_id=?
    """, (first_name, last_name, class_name, day_id)).fetchone()
    conn.close()
    return dict(row) if row else None


def set_person_session(first_name, last_name, class_name):
    session["person"] = {
        "first_name": first_name,
        "last_name": last_name,
        "class_name": class_name,
    }


@app.route("/")
def index():
    return render_template("index.html", games=get_games(), registrations=current_registrations())


@app.get("/api/games")
def api_games():
    return jsonify(get_games())

@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/mes-inscriptions")
def my_registrations():
    registrations = current_registrations()
    if not registrations:
        return redirect(url_for("inscription"))
    return render_template("already_registered.html", registrations=registrations)


@app.route("/inscription", methods=["GET", "POST"])
def inscription():
    selected_game = request.args.get("game", "")
    error = None
    person = session.get("person", {})
    form = {
        "first_name": person.get("first_name", ""),
        "last_name": person.get("last_name", ""),
        "class_name": person.get("class_name", ""),
    }

    # Si le profil est déjà mémorisé et qu'un jeu est sélectionné,
    # inutile de redemander le formulaire : on passe directement aux jours.
    if request.method == "GET" and selected_game and all(form.values()):
        game, days = get_game(selected_game)
        if game:
            if any(d["remaining"] > 0 for d in days):
                return render_template(
                    "choose_day.html", game=game, days=days, form=form,
                    registrations=current_registrations()
                )

    if request.method == "POST":
        form = {
            "first_name": normalize(request.form.get("first_name", "")),
            "last_name": normalize(request.form.get("last_name", "")),
            "class_name": normalize(request.form.get("class_name", "")),
        }
        selected_game = request.form.get("game", selected_game)

        if not all(form.values()):
            error = "Tous les champs sont obligatoires."
        else:
            set_person_session(**form)

            # Aucun jeu choisi : on garde le profil et on laisse
            # l'utilisateur sélectionner son jeu ensuite.
            if not selected_game:
                return render_template(
                    "choose_game.html", games=get_games(),
                    registrations=current_registrations(), form=form
                )

            game, days = get_game(selected_game)
            if not game:
                error = "Jeu introuvable."
            else:
                available_days = [d for d in days if d["remaining"] > 0]
                if not available_days:
                    error = "Il n'y a plus de place pour ce jeu."
                else:
                    return render_template(
                        "choose_day.html", game=game, days=days, form=form,
                        registrations=current_registrations()
                    )

    return render_template(
        "inscription.html", games=get_games(), selected_game=selected_game,
        error=error, form=form, registrations=current_registrations()
    )


@app.post("/inscription/confirm")
def confirm_inscription():
    person = session.get("person")
    if not person:
        first_name = normalize(request.form.get("first_name", ""))
        last_name = normalize(request.form.get("last_name", ""))
        class_name = normalize(request.form.get("class_name", ""))
        if not first_name or not last_name or not class_name:
            return "Informations incomplètes", 400
        set_person_session(first_name, last_name, class_name)
        person = session["person"]

    game_day_id = request.form.get("game_day_id", "")
    if not game_day_id:
        return "Jour incomplet", 400

    conn = get_db()
    try:
        conn.execute("BEGIN")
        gd = conn.execute("""
            SELECT gd.id, gd.capacity, gd.day_id, g.name AS game_name, g.slug AS game_slug,
                   d.label, d.event_date, gd.start_time, gd.end_time
            FROM game_days gd
            JOIN games g ON g.id = gd.game_id
            JOIN event_days d ON d.id = gd.day_id
            WHERE gd.id = ?
        """, (game_day_id,)).fetchone()
        if not gd:
            conn.rollback()
            return "Jour introuvable", 404

        existing_same_day = conn.execute("""
            SELECT r.id, g.name AS game_name
            FROM registrations r
            JOIN game_days old_gd ON old_gd.id = r.game_day_id
            JOIN games g ON g.id = old_gd.game_id
            WHERE r.first_name=? AND r.last_name=? AND r.class_name=? AND old_gd.day_id=?
        """, (person["first_name"], person["last_name"], person["class_name"], gd["day_id"])).fetchone()
        if existing_same_day:
            conn.rollback()
            return render_template(
                "choose_day.html", game={"name": gd["game_name"], "slug": gd["game_slug"]},
                days=get_game(gd["game_slug"])[1], form=person,
                registrations=current_registrations(),
                error=f"Tu es déjà inscrit à {existing_same_day['game_name']} le {gd['label']}. Choisis un autre jour."
            )

        count = conn.execute(
            "SELECT COUNT(*) AS count FROM registrations WHERE game_day_id = ?", (game_day_id,)
        ).fetchone()["count"]
        if count >= gd["capacity"]:
            conn.rollback()
            return render_template(
                "choose_day.html", game={"name": gd["game_name"], "slug": gd["game_slug"]},
                days=get_game(gd["game_slug"])[1], form=person,
                registrations=current_registrations(),
                error="Ce jour vient d'être complet. Choisis un autre jour."
            )

        token = secrets.token_urlsafe(24)
        conn.execute("""
            INSERT INTO registrations(game_day_id, first_name, last_name, class_name, cancel_token)
            VALUES (?, ?, ?, ?, ?)
        """, (game_day_id, person["first_name"], person["last_name"], person["class_name"], token))
        conn.commit()
        return render_template("success.html", registration={
            "first_name": person["first_name"], "last_name": person["last_name"], "class_name": person["class_name"],
            "game_name": gd["game_name"], "label": gd["label"], "event_date": gd["event_date"],
            "start_time": gd["start_time"], "end_time": gd["end_time"]
        }, registrations=current_registrations())
    except (sqlite3.IntegrityError, psycopg.IntegrityError):
        conn.rollback()
        return "Impossible d'enregistrer cette inscription.", 409
    finally:
        conn.close()


@app.post("/annuler")
def cancel_registration():
    token = request.form.get("cancel_token", "")
    person = session.get("person")
    if not token or not person:
        return redirect(url_for("index"))

    conn = get_db()
    conn.execute("""
        DELETE FROM registrations
        WHERE cancel_token=? AND first_name=? AND last_name=? AND class_name=?
    """, (token, person["first_name"], person["last_name"], person["class_name"]))
    conn.commit()
    remaining = conn.execute("""
        SELECT COUNT(*) AS count FROM registrations
        WHERE first_name=? AND last_name=? AND class_name=?
    """, (person["first_name"], person["last_name"], person["class_name"])).fetchone()["count"]
    conn.close()
    if remaining == 0:
        session.pop("person", None)
    return render_template("cancelled.html", registrations=current_registrations())


def admin_data():
    conn = get_db()
    days = conn.execute("""
        SELECT d.id AS day_id, d.label, d.event_date,
               gd.id AS game_day_id, g.id AS game_id, g.name AS game_name, g.slug,
               gd.capacity, gd.start_time, gd.end_time,
               COUNT(r.id) AS registered, gd.capacity - COUNT(r.id) AS remaining
        FROM event_days d
        JOIN game_days gd ON gd.day_id = d.id
        JOIN games g ON g.id = gd.game_id
        LEFT JOIN registrations r ON r.game_day_id = gd.id
        GROUP BY d.id, d.label, d.event_date, gd.id, g.id, g.name, g.slug, gd.capacity, gd.start_time, gd.end_time
        ORDER BY d.event_date, g.id
    """).fetchall()
    registrations = conn.execute("""
        SELECT r.id, r.first_name, r.last_name, r.class_name, r.created_at,
               gd.id AS game_day_id, g.id AS game_id, g.name AS game_name, g.slug,
               d.id AS day_id, d.label, d.event_date, gd.start_time, gd.end_time
        FROM registrations r
        JOIN game_days gd ON gd.id = r.game_day_id
        JOIN games g ON g.id = gd.game_id
        JOIN event_days d ON d.id = gd.day_id
        ORDER BY d.event_date, g.id, r.last_name, r.first_name, r.id
    """).fetchall()
    conn.close()
    days_list = [dict(row) for row in days]
    regs = [dict(row) for row in registrations]
    for r in regs:
        if r.get("created_at") is not None:
            r["created_at"] = str(r["created_at"])
    by_game_day = {}
    for r in regs:
        by_game_day.setdefault(str(r["game_day_id"]), []).append(r)
    for d in days_list:
        d["participation_fee"] = PARTICIPATION_FEE
        d["registrations"] = by_game_day.get(str(d["game_day_id"]), [])
    return {"days": days_list, "registrations": regs}


@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST" and not session.get("admin"):
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if secrets.compare_digest(username, ADMIN_USERNAME) and secrets.compare_digest(password, ADMIN_PASSWORD):
            session["admin"] = True
            return redirect(url_for("admin"))
        return render_template("admin.html", login=True, error="Identifiant ou mot de passe incorrect.")

    if not session.get("admin"):
        return render_template("admin.html", login=True)

    data = admin_data()
    return render_template("admin.html", days=data["days"], registrations=data["registrations"])


@app.get("/admin/api/data")
def admin_api_data():
    if not session.get("admin"):
        return jsonify({"error": "Non autorisé"}), 401
    return jsonify(admin_data())


@app.post("/admin/inscription/<int:registration_id>/supprimer")
def admin_delete_registration(registration_id):
    if not session.get("admin"):
        return jsonify({"error": "Non autorisé"}), 401
    conn = get_db()
    try:
        cur = conn.execute("DELETE FROM registrations WHERE id=?", (registration_id,))
        conn.commit()
        if cur.rowcount == 0:
            return jsonify({"error": "Inscription introuvable"}), 404
        return jsonify({"ok": True})
    finally:
        conn.close()


@app.get("/admin/export.csv")
def export_csv():
    if not session.get("admin"):
        return redirect(url_for("admin"))
    conn = get_db()
    rows = conn.execute("""
        SELECT g.name, d.label, d.event_date, gd.start_time, gd.end_time,
               r.first_name, r.last_name, r.class_name, r.created_at
        FROM registrations r
        JOIN game_days gd ON gd.id = r.game_day_id
        JOIN games g ON g.id = gd.game_id
        JOIN event_days d ON d.id = gd.day_id
        ORDER BY d.event_date, g.name, r.last_name
    """).fetchall()
    conn.close()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Jeu", "Jour", "Date", "Début", "Fin", "Prénom", "Nom", "Classe", "Inscrit le"])
    for row in rows:
        writer.writerow([row["name"], row["label"], row["event_date"], row["start_time"], row["end_time"], row["first_name"], row["last_name"], row["class_name"], row["created_at"]])
    return Response(output.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=inscriptions.csv"})


@app.post("/logout")
def logout():
    session.pop("admin", None)
    return redirect(url_for("admin"))


init_db()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
