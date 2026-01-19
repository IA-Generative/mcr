# MCR Génération

## 1. Description

Cette application est une API codé en FastAPI qui permet de générer un compte rendu de réunion à partir de la transcription de cette réunion. Elle est l'une des briques d'une architecture microservice du projet **Mon Compte Rendu**.

## 2. Fonctionnalités

- **Réception d'une transcription diarisée** : L'application reçoit une transcription diarisée (i.e. chaque segment de la transcription est rattaché à un locuteur) par segment.

- **Génération d'un compte rendu** : Selon le type de réunion un compte rendu est généré par une chaîne d'appels succéssifs à un LLM.

- **Classification des décisions par thème** : Lorsque le type de compte-rendu est un relevé de décisions une classification est opérée pour associer chaque décision à un thème abordé dans l'ordre du jour. (Cette option est désactivée par défaut)

## 3. Prérequis

Avant de démarrer, assurez-vous d'avoir installé les éléments suivants sur votre machine:

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

Il faut également avoir capté la transcription d'une réunion avec le module [mcr-core](git@github.com:IA-Generative/mcr-core.git).
