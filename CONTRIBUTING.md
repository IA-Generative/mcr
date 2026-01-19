# Contribuer à FCR

Merci de votre intérêt pour contribuer au projet **FCR** 🎉

Ce document décrit le processus de contribution et les règles à respecter afin de garantir la qualité, la cohérence et la maintenabilité du projet.

---

## 🧭 Processus de contribution

1. Forkez le repository GitHub
2. Créez une branche depuis `dev` :
   - `feat/<description-courte>` pour une nouvelle fonctionnalité
   - `fix/<description-courte>` pour une correction
3. Effectuez des commits clairs, atomiques et explicites. Nous utilisons [gitmoji](https://gitmoji.dev/) pour les commits.  
   Exemple : `git commit -m "✨ ({number-issue}): add feature X "`
4. Ouvrez une **Pull Request vers la branche** **dev**

> ⚠️ Les Pull Requests vers `main` sont réservées aux maintainers du projet.

---

## 🧪 Tests et qualité

Avant d’ouvrir une Pull Request, assurez-vous que l’ensemble des tests et outils de qualité passent correctement.

### Backend (FastAPI)

```bash
cd mcr-core
make pre-commit
```

### Frontend (Vue)

```bash
cd mcr-frontend
pnpm lint
pnpm build
```

Toute Pull Request qui échoue à la CI sera automatiquement bloquée.

---

## 🧹 Standards de code

- Respectez les conventions et l’architecture existantes
- Une Pull Request doit traiter **un seul sujet**
- Évitez les changements non liés au périmètre de la PR
- Tout changement significatif doit être documenté (README ou commentaires)

---

## 🔐 Sécurité

- ❌ Ne committez jamais de secrets (`.env`, clés API, tokens, credentials…)
- ❌ Ne committez pas de données sensibles ou personnelles
- Utilisez et maintenez à jour le fichier `.env.local.docker`

Toute PR contenant des secrets sera refusée.

---

## 🗣️ Communication

- Utilisez les **Issues GitHub** pour signaler un bug ou proposer une amélioration

---

## 📜 Licence

En contribuant à ce projet, vous acceptez que vos contributions soient distribuées sous licence **Apache License 2.0**.

---

Merci pour votre contribution 🙏

