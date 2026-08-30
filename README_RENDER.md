# Déployer Key Club sur Render + PostgreSQL

Cette V8 est préparée pour fonctionner avec **Render Web Service + Render PostgreSQL**.

## 1. Mettre le projet sur GitHub

Crée un dépôt GitHub et envoie **le contenu de ce dossier** (pas le fichier ZIP lui-même).

Ne mets jamais dans GitHub :
- un mot de passe administrateur ;
- une clé secrète ;
- un fichier `key_club.db` contenant des inscriptions.

Le fichier `.gitignore` fourni protège déjà ces éléments locaux.

## 2. Créer les services Render

Le fichier `render.yaml` est déjà configuré pour créer :

- un Web Service Python nommé `key-club` ;
- une base PostgreSQL nommée `key-club-db` ;
- `DATABASE_URL` automatiquement reliée à PostgreSQL ;
- une `SECRET_KEY` générée automatiquement.

Dans Render :

1. Connecte ton compte GitHub.
2. Crée un nouveau **Blueprint** depuis le dépôt.
3. Render détectera `render.yaml`.
4. Utilise le plan **Free** pour le Web Service et PostgreSQL.
5. Dans les variables d'environnement du service, définis `ADMIN_PASSWORD` avec un mot de passe que tu choisis.
6. Lance le déploiement.

Render fournit alors une URL publique en `onrender.com`.

## 3. Important : PostgreSQL gratuit

Le PostgreSQL Free de Render est destiné aux tests/projets temporaires et expire après 30 jours. C'est adapté à un événement d'environ une semaine, mais pense à sauvegarder/exporter les inscriptions avant l'expiration si tu veux les conserver.

Le Web Service Free peut aussi s'arrêter après une période d'inactivité ; il redémarre lorsqu'une nouvelle requête arrive.

## 4. Configuration automatique

Render utilisera :

Build command:
```text
pip install -r requirements.txt
```

Start command:
```text
gunicorn app:app
```

## 5. Développement local

Sans `DATABASE_URL`, l'application continue d'utiliser SQLite localement. Tu peux donc continuer à développer sans PostgreSQL sur ton PC.

Pour tester exactement PostgreSQL en local, définis `DATABASE_URL` vers une base PostgreSQL de développement.
