#!/bin/zsh
cd "$(dirname "$0")"

echo "=== Key Club — démarrage local (Mac) ==="

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 n'est pas installé. Installe Python 3 puis relance ce fichier."
  echo "https://www.python.org/downloads/macos/"
  read -k 1 "?Appuie sur une touche pour fermer..."
  echo
  exit 1
fi

if [ ! -d ".venv" ]; then
  echo "Création de l'environnement Python..."
  python3 -m venv .venv || exit 1
fi

.venv/bin/python -m pip install -q -r requirements.txt || exit 1

open "http://127.0.0.1:5000"
echo ""
echo "Le site est disponible sur : http://127.0.0.1:5000"
echo "Pour arrêter le serveur : Ctrl+C"
.venv/bin/python app.py
