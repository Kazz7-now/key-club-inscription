# Key Club — Vient battre ton gameur

Prototype du site d'inscription à l'événement Key Club.

## Architecture

- **Mode utilisateur public** : `/` — aucun compte ni mot de passe nécessaire.
- **Administration** : `/admin` — séparée du parcours utilisateur et protégée par mot de passe.
- **Frontend** : HTML, CSS, Jinja2 et JavaScript.
- **Backend** : Python + Flask.
- **Base de données** : SQLite pour le développement ; PostgreSQL pourra remplacer SQLite pour le serveur final.

## Accès utilisateur

Les participants n'ont rien à installer : une fois le site déployé sur le VPS, ils ouvrent simplement l'adresse du site avec Safari, Chrome, Firefox, Edge, sur téléphone, Windows ou Mac.

Le parcours public est :

1. Accueil → choix d'un jeu.
2. Clic sur un jeu → formulaire prénom / nom / classe.
3. Choix d'un jour disponible pour ce jeu.
4. Confirmation de l'inscription.
5. Une seule inscription active par personne.
6. Possibilité d'annuler depuis le même navigateur, puis de se réinscrire.

## Lancer sur Windows

Double-cliquer sur `start.bat`.

Ou :

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
python app.py
```

Puis ouvrir `http://127.0.0.1:5000`.

## Lancer sur Mac

Double-cliquer sur `Lancer Key Club sur Mac.command`.

Si macOS affiche un avertissement : clic droit sur le fichier → **Ouvrir** → confirmer.

Si le fichier reste bloqué car il a été téléchargé depuis Internet, ouvre Terminal dans le dossier et exécute une seule fois :

```bash
xattr -d com.apple.quarantine "Lancer Key Club sur Mac.command"
```

Le script crée automatiquement l'environnement Python, installe Flask et ouvre le site dans le navigateur. Les instructions sont aussi dans `LIRE_MOI_MAC.txt`.

## Important pour la version en ligne

Les participants ne lanceront **pas** `start.command` ou `start.bat`. Ces fichiers servent uniquement au développement local.

En production, le participant fera simplement :

```text
Safari / Chrome
      ↓
https://adresse-du-site.fr
      ↓
Mode utilisateur
```

## Administration

L'administration reste accessible séparément par `/admin`. Ne pas utiliser le mot de passe de démonstration en production : définir `ADMIN_PASSWORD` et `SECRET_KEY` dans les variables d'environnement.


## Voir le code

Le code est directement dans le dossier : `app.py`, `templates/`, `static/`, `schema.sql`, etc. Il peut être ouvert dans VS Code, Cursor ou un autre éditeur sur Mac.
