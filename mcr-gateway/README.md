# Gateway

## Accès au Swagger

La route pour accéder au Swagger de la gateway a été modifiée de manière à être accessible depuis tous les environnements et en local.

Il est disponible à l'url **{domaine}/api/docs**.

Son utilisation nécessite de s'authentifier en cliquant sur le bouton **Authorize**.
Il faut renseigner :

- L'identifiant MCR pour cet environnement dans le champ _username_.
- Le mot de passe MCR pour cet environnement dans le champ _password_.
- Laisser _Authorization Header_ pour le champ _Client credentials location_.
- Renseigner _mcr_ dans le champ _client_id_.
- Laisser le champ _client_secret_ vide.
