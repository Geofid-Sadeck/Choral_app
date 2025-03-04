from flask import Flask, render_template, request, redirect, send_file, session, flash
import sqlite3
import pandas as pd
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'votre_secret_key'  # Clé secrète pour les sessions

# Code secret pour l'exportation Excel
CODE_SECRET = "24010"

# Initialisation de la base de données
def init_db():
    conn = sqlite3.connect('chorale.db')
    c = conn.cursor()
    
    # Table des utilisateurs
    c.execute('''CREATE TABLE IF NOT EXISTS utilisateurs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nom_utilisateur TEXT UNIQUE,
                    mot_de_passe TEXT,
                    role TEXT,
                    bloque INTEGER DEFAULT 0
                )''')
    
    # Table des membres
    c.execute('''CREATE TABLE IF NOT EXISTS membres (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nom TEXT,
                    prenom TEXT,
                    date_naissance TEXT,
                    numero TEXT,
                    utilisateur_id INTEGER,
                    statut TEXT DEFAULT 'Nouveau'
                )''')
    
    # Table des présences
    c.execute('''CREATE TABLE IF NOT EXISTS presences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    membre_id INTEGER,
                    type_rencontre TEXT,
                    date TEXT,
                    presence TEXT,
                    FOREIGN KEY(membre_id) REFERENCES membres(id)
                )''')
    
    conn.commit()
    conn.close()

# Ajouter l'utilisateur admin
def ajouter_admin():
    conn = sqlite3.connect('chorale.db')
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO utilisateurs (nom_utilisateur, mot_de_passe, role) VALUES (?, ?, ?)",
              ('admin', 'admin24010', 'admin'))
    conn.commit()
    conn.close()

# Route pour la page d'accueil
@app.route('/')
def index():
    if 'nom_utilisateur' not in session:
        return redirect('/connexion')

    conn = sqlite3.connect('chorale.db')
    c = conn.cursor()
    if session.get('role') == 'admin':
        c.execute("SELECT * FROM membres")
    else:
        c.execute("SELECT * FROM membres WHERE utilisateur_id = ?", (session['utilisateur_id'],))
    membres = c.fetchall()
    conn.close()
    return render_template('index.html', membres=membres, role=session.get('role'))

# Route pour la page de connexion
@app.route('/connexion', methods=['GET', 'POST'])
def connexion():
    if request.method == 'POST':
        nom_utilisateur = request.form['nom_utilisateur']
        mot_de_passe = request.form['mot_de_passe']

        conn = sqlite3.connect('chorale.db')
        c = conn.cursor()
        c.execute("SELECT * FROM utilisateurs WHERE nom_utilisateur = ? AND mot_de_passe = ?", (nom_utilisateur, mot_de_passe))
        utilisateur = c.fetchone()
        conn.close()

        if utilisateur:
            session['nom_utilisateur'] = utilisateur[1]
            session['role'] = utilisateur[3]
            session['utilisateur_id'] = utilisateur[0]
            return redirect('/')
        else:
            flash('Nom d\'utilisateur ou mot de passe incorrect', 'error')
    return render_template('connexion.html')

# Route pour la page d'inscription
@app.route('/inscription', methods=['GET', 'POST'])
def inscription():
    if request.method == 'POST':
        nom_utilisateur = request.form['nom_utilisateur']
        mot_de_passe = request.form['mot_de_passe']

        conn = sqlite3.connect('chorale.db')
        c = conn.cursor()

        # Vérifier si le nom d'utilisateur existe déjà
        c.execute("SELECT * FROM utilisateurs WHERE nom_utilisateur = ?", (nom_utilisateur,))
        utilisateur_existant = c.fetchone()

        if utilisateur_existant:
            flash('Ce nom d\'utilisateur est déjà pris !', 'error')
        else:
            # Ajouter l'utilisateur
            c.execute("INSERT INTO utilisateurs (nom_utilisateur, mot_de_passe, role) VALUES (?, ?, ?)",
                      (nom_utilisateur, mot_de_passe, 'utilisateur'))
            conn.commit()
            flash('Inscription réussie ! Vous pouvez maintenant vous connecter.', 'success')

        conn.close()
        return redirect('/connexion')
    return render_template('inscription.html')

# Route pour ajouter un membre
@app.route('/ajouter_membre', methods=['POST'])
def ajouter_membre():
    if 'nom_utilisateur' not in session:
        flash('Vous devez être connecté pour ajouter un membre.', 'error')
        return redirect('/connexion')

    nom = request.form['nom']
    prenom = request.form['prenom']
    date_naissance = request.form['date_naissance']
    numero = request.form['numero']

    conn = sqlite3.connect('chorale.db')
    c = conn.cursor()

    # Vérifier si le membre existe déjà
    c.execute("SELECT * FROM membres WHERE nom = ? AND prenom = ?", (nom, prenom))
    membre_existant = c.fetchone()

    if membre_existant:
        flash('Ce membre existe déjà !', 'error')
    else:
        # Ajouter le membre
        c.execute("INSERT INTO membres (nom, prenom, date_naissance, numero, utilisateur_id) VALUES (?, ?, ?, ?, ?)",
                  (nom, prenom, date_naissance, numero, session['utilisateur_id']))
        conn.commit()
        flash('Membre ajouté avec succès !', 'success')

    conn.close()
    return redirect('/')

# Route pour supprimer un membre
@app.route('/supprimer_membre/<int:membre_id>')
def supprimer_membre(membre_id):
    if 'nom_utilisateur' not in session:
        flash('Vous devez être connecté pour supprimer un membre.', 'error')
        return redirect('/connexion')

    conn = sqlite3.connect('chorale.db')
    c = conn.cursor()
    c.execute("DELETE FROM membres WHERE id = ?", (membre_id,))
    conn.commit()
    conn.close()
    flash('Membre supprimé avec succès !', 'success')
    return redirect('/')

# Route pour enregistrer une présence
@app.route('/enregistrer_presence', methods=['POST'])
def enregistrer_presence():
    if 'nom_utilisateur' not in session:
        flash('Vous devez être connecté pour enregistrer une présence.', 'error')
        return redirect('/connexion')

    membre_id = request.form['membre_id']
    type_rencontre = request.form['type_rencontre']
    presence = request.form['presence']
    date = request.form['date']

    conn = sqlite3.connect('chorale.db')
    c = conn.cursor()
    c.execute("INSERT INTO presences (membre_id, type_rencontre, date, presence) VALUES (?, ?, ?, ?)",
              (membre_id, type_rencontre, date, presence))
    conn.commit()
    conn.close()
    flash('Présence enregistrée avec succès !', 'success')
    return redirect('/')

# Route pour le suivi des présences
@app.route('/suivi_presences')
def suivi_presences():
    if 'nom_utilisateur' not in session:
        return redirect('/connexion')

    conn = sqlite3.connect('chorale.db')
    c = conn.cursor()

    # Récupérer les présences des 3 derniers mois
    trois_mois_avant = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
    c.execute('''
        SELECT m.nom, m.prenom, p.date, p.presence, p.type_rencontre
        FROM presences p
        JOIN membres m ON p.membre_id = m.id
        WHERE p.date >= ?
        ORDER BY p.date DESC
    ''', (trois_mois_avant,))
    presences = c.fetchall()

    # Calculer le statut des membres
    c.execute('''
        SELECT m.id, m.nom, m.prenom, COUNT(p.id) AS nb_presences
        FROM membres m
        LEFT JOIN presences p ON m.id = p.membre_id AND p.date >= ?
        GROUP BY m.id
    ''', (trois_mois_avant,))
    membres_statut = c.fetchall()

    for membre in membres_statut:
        nb_presences = membre[3]
        if nb_presences >= 8:  # Régulier
            statut = 'Régulier'
        elif nb_presences >= 3:  # Saisonnier
            statut = 'Saisonnier'
        else:  # Nouveau
            statut = 'Nouveau'
        
        c.execute("UPDATE membres SET statut = ? WHERE id = ?", (statut, membre[0]))
        conn.commit()

    conn.close()
    return render_template('suivi_presences.html', presences=presences)

# Route pour les requêtes simples
@app.route('/requetes', methods=['GET', 'POST'])
def requetes():
    if 'nom_utilisateur' not in session:
        return redirect('/connexion')

    conn = sqlite3.connect('chorale.db')
    c = conn.cursor()

    # Récupérer la liste des membres
    c.execute("SELECT id, nom, prenom FROM membres")
    membres = c.fetchall()

    resultats = None
    if request.method == 'POST':
        membre_id = request.form['membre_id']
        date_debut = request.form['date_debut']
        date_fin = request.form['date_fin']

        # Requête pour compter les présences et absences
        c.execute('''
            SELECT 
                SUM(CASE WHEN presence = 'Présent' THEN 1 ELSE 0 END) AS nb_presences,
                SUM(CASE WHEN presence = 'Absent' THEN 1 ELSE 0 END) AS nb_absences
            FROM presences
            WHERE membre_id = ? AND date BETWEEN ? AND ?
        ''', (membre_id, date_debut, date_fin))
        resultats = c.fetchone()

    conn.close()
    return render_template('requetes.html', membres=membres, resultats=resultats)

# Route pour exporter les données en Excel
@app.route('/exporter_excel', methods=['GET', 'POST'])
def exporter_excel():
    if 'nom_utilisateur' not in session or session.get('role') != 'admin':
        return redirect('/connexion')

    if request.method == 'POST':
        code_saisi = request.form['code_secret']
        if code_saisi == CODE_SECRET:
            conn = sqlite3.connect('chorale.db')
            df_membres = pd.read_sql_query('''
                SELECT id, nom, prenom, date_naissance, numero, utilisateur_id
                FROM membres
            ''', conn)
            df_presences = pd.read_sql_query('''
                SELECT p.id, m.nom, m.prenom, p.type_rencontre, p.date, p.presence
                FROM presences p
                JOIN membres m ON p.membre_id = m.id
            ''', conn)
            conn.close()

            with pd.ExcelWriter('chorale_presences.xlsx') as writer:
                df_membres.to_excel(writer, sheet_name='Membres', index=False)
                df_presences.to_excel(writer, sheet_name='Presences', index=False)

            return send_file('chorale_presences.xlsx', as_attachment=True)
        else:
            flash('Code secret incorrect !', 'error')
            return redirect('/')

    return render_template('export_excel.html')

# Route pour le tableau de bord administrateur
@app.route('/admin')
def admin():
    if 'nom_utilisateur' not in session or session.get('role') != 'admin':
        return redirect('/connexion')

    conn = sqlite3.connect('chorale.db')
    c = conn.cursor()

    # Récupérer tous les utilisateurs
    c.execute("SELECT * FROM utilisateurs")
    utilisateurs = c.fetchall()

    # Récupérer tous les membres
    c.execute("SELECT * FROM membres")
    membres = c.fetchall()

    # Récupérer les activités récentes
    c.execute('''
        SELECT u.nom_utilisateur, m.nom, m.prenom, p.date, p.type_rencontre, p.presence
        FROM presences p
        JOIN membres m ON p.membre_id = m.id
        JOIN utilisateurs u ON m.utilisateur_id = u.id
        ORDER BY p.date DESC
        LIMIT 10
    ''')
    activites = c.fetchall()

    conn.close()
    return render_template('admin.html', utilisateurs=utilisateurs, membres=membres, activites=activites)

# Route pour bloquer/débloquer un utilisateur
@app.route('/bloquer_utilisateur/<int:user_id>')
def bloquer_utilisateur(user_id):
    if 'nom_utilisateur' not in session or session.get('role') != 'admin':
        return redirect('/connexion')

    conn = sqlite3.connect('chorale.db')
    c = conn.cursor()
    c.execute("UPDATE utilisateurs SET bloque = 1 WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    flash('Utilisateur bloqué avec succès !', 'success')
    return redirect('/admin')

@app.route('/debloquer_utilisateur/<int:user_id>')
def debloquer_utilisateur(user_id):
    if 'nom_utilisateur' not in session or session.get('role') != 'admin':
        return redirect('/connexion')

    conn = sqlite3.connect('chorale.db')
    c = conn.cursor()
    c.execute("UPDATE utilisateurs SET bloque = 0 WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    flash('Utilisateur débloqué avec succès !', 'success')
    return redirect('/admin')

# Route pour la déconnexion
@app.route('/deconnexion')
def deconnexion():
    session.pop('nom_utilisateur', None)
    session.pop('role', None)
    session.pop('utilisateur_id', None)
    return redirect('/connexion')

# Lancer l'application
if __name__ == '__main__':
    init_db()
    ajouter_admin()
    app.run(debug=True)