#### **1. Description**

Ce repository regroupe les différents services de l’application **MCR**, dont l’objectif est d’aider les métiers dans leurs tâches de génération de comptes rendus.

Les services sont les suivants :

1. **mcr-frontend**
   Application **Vue**. Il s’agit de l’interface utilisateur de MCR.

2. **mcr-gateway**
   Application **FastAPI** exposée comme point d’entrée du cluster.
   Elle est en charge de l’**autorisation** des requêtes.

3. **mcr-core**
   Application **FastAPI**. Module principal du backend.
   Il orchestre la gestion des ressources (CRUD) ainsi que le **scheduling** des tâches de transcription.

4. **mcr-capture-worker**
   Worker **Playwright** chargé de la capture audio des réunions en ligne.
   Il utilise un bot simulant un utilisateur dans une réunion de visioconférence, capture l’audio à intervalles réguliers et l’envoie dans un bucket S3.

5. **mcr-transcription-worker**
   Worker **Celery / Redis** en charge de la transcription et de la **diarisation** des fichiers audio.

6. **mcr-generation**
   Worker **Celery / Redis** permettant de générer le compte-rendu à partir de la transcription diarisation en entrée.

---

Il existe **trois manières** de fournir l’audio d’une réunion à MCR :

1. Via une plateforme de visioconférence (COMU, webinaire, webconf)
2. Via un fichier audio ou vidéo (MP3, WAV, MP4, etc.)
3. Via un microphone connecté à la machine

Une fois l’audio fourni, MCR effectue les étapes suivantes :

1. Transcription et diarisation de l’audio
2. Génération du compte-rendu (optionnel)

---

### **2. Architecture de MCR**

![Architecture globale de MCR](./image/schema-archi-fonctionnel.jpg)

---

### **3. Prérequis**

Un fichier `docker-compose` est disponible à la racine de ce repository.
Il permet de faire fonctionner l’ensemble des briques applicatives en local.

Avant de démarrer, assurez-vous d’avoir installé les éléments suivants :

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

- Les librairies ffmpeg, pnpm et uv
```bash
brew install ffmpeg node pnpm uv
```

De manière optionnelle, vous pouvez utiliser un outil de gestion de bases de données tel que :

- [pgAdmin](https://www.pgadmin.org/download/)
- [DBeaver](https://dbeaver.io/download/)

Ces outils permettent de visualiser et d’explorer le contenu de la base de données.

---

### **4. Configuration Claude Code (MCP)**

Un fichier `.mcp.json` à la racine déclare les serveurs **MCP** partagés par l’équipe (actuellement : **Sentry**). Au premier lancement de Claude Code dans ce repository, un prompt de confiance s’affiche pour approuver les serveurs MCP du projet.

Le MCP Sentry permet à Claude Code d’interroger directement l’instance Sentry du projet : lister les issues, consulter les events et stack traces, rechercher dans les erreurs remontées par les services MCR. Concrètement, cela permet de demander à Claude d’investiguer une erreur de production sans copier-coller les stack traces à la main.

#### Authentification via 1Password

Les secrets du MCP Sentry ne sont pas stockés dans des variables d’environnement : le serveur est lancé via `op run`, qui résout les références `op://` du `.mcp.json` au démarrage. Ce setup est identique quel que soit l’OS, et évite que le token traîne dans un `.bashrc`.

Pour le configurer :

1. Dans votre vault personnel 1Password (« Employee » ou « Private » selon le compte), créez un item de type **API Credentials** (dans *Show more*) nommé exactement `Sentry MCP Access Token`, avec les champs :
   - **credential** : votre Personal Access Token Sentry (scopes `org:read`, `project:read`, `event:read`, `issue:read`) ;
   - **hostname** : le hostname de l’instance Sentry du projet (à demander à l’équipe).

2. Installez la CLI 1Password :

```bash
brew install 1password-cli
```

3. Activez l’intégration CLI dans l’app 1Password : **Settings > Developer > Integrate with 1Password CLI**.

Au lancement du MCP, 1Password demandera une autorisation (Touch ID ou mot de passe) pour laisser `op` lire l’item.

Ces credentials ne sont **pas** des variables de runtime des services MCR : ils ne doivent pas figurer dans les fichiers `.env.local.*`.

---

### **5. Lancement de MCR en local**

1) Clonez le repository :

```bash
git clone git@github.com:IA-Generative/mcr.git
cd mcr
```
2) Demander un .env à l'équipe

3) Lancer le projet à l’aide de la commande `make`
```bash
make start
```

---

### **6. Licence**

Ce projet est distribué sous licence Apache 2.0.

### **7. Avis de sécurité**

Tous les identifiants, noms d’utilisateurs, adresses e-mail, mots de passe et clés présents dans ce dépôt sont **des valeurs fictives**, utilisées **uniquement à des fins de développement local**.

Ils **ne correspondent à aucun environnement de production** et **ne permettent l’accès à aucun système réel**.
