# ADR 001: Utilisation de Supabase, React Query et Expo Router

## Contexte
Nous devons construire une application mobile avec un backend robuste, une synchronisation temps réel des données, et une navigation fluide. L’application comporte des profils utilisateurs, un catalogue de produits, et un système de commande.

## Décision
Nous choisissons d’utiliser :

- **Supabase** comme backend 
  - Authentification via JWT
  - Base de données PostgreSQL auto-hébergée
  - RLS (Row Level Security) pour la sécurité
- **React Query** pour la gestion des états côté client
  - Synchronisation optimiste
  - Caching intelligent
  - Gestion des erreurs et retries
- **Expo Router** pour la navigation
  - Structure basée sur le système de fichiers (`app/`)
  - Support des deep links
  - Nested layouts

## Justification
- Supabase offre une alternative open-source à Firebase avec une intégration aisée à PostgreSQL.
- React Query s’impose comme standard pour la gestion coté client, surtout avec Supabase.
- Expo Router suit les bonnes pratiques de Next.js et simplifie grandement le routage.

## Conséquences
- Réduction du code boilerplate
- Meilleure maintenabilité
- Stack moderne et bien documentée
- Nécessite une bonne compréhension de RLS et des patterns de React Query
