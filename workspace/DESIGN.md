## Architecture Decision
**Stack:** React Native + Expo Router + Supabase + React Query + TypeScript
**Structure:** DB + Auth + Hooks + Screens
**Key decisions:**
- Chaque fichier est immédiatement exécutable (pas de TODO bloquant)
- Chaque hook : { data, isLoading, error } — jamais d’états partiels
- Aucun écran n’appelle Supabase directement (tout passe par les hooks)

## Tools
write_file