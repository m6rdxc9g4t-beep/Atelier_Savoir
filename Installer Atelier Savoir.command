#!/bin/bash
# Double-cliquez sur ce fichier dans le Finder pour installer « Atelier Savoir.app ».
cd "$(dirname "$0")" || exit 1

if ./macos/build_app.sh; then
  open -R "$HOME/Applications/Atelier Savoir.app"
  open "$HOME/Applications/Atelier Savoir.app"
  echo
  echo "Vous pouvez fermer cette fenêtre."
else
  echo
  echo "L'installation a échoué : lisez le message ci-dessus."
  read -r -p "Appuyez sur Entrée pour fermer…"
fi
