# Rehab App — Workspace

Application mobile de rééducation médicale construite avec **Expo / React Native**, **Supabase** et **TanStack Query**.

## Stack technique

| Couche | Technologie |
|---|---|
| Mobile | Expo (React Native) |
| Backend / DB | Supabase (PostgreSQL + Auth + Storage) |
| State / Data fetching | TanStack React Query v5 |
| Routing | Expo Router (file-based) |
| Langage | TypeScript |

## Architecture

### Rôles utilisateurs

Trois rôles distincts avec routing automatique à l'ouverture :

- **admin** → `/admin`
- **practitioner** → `/practitioner`
- **patient** → `/patient`
- Non authentifié → `/auth`

### Multi-tenant

Chaque entité (patient, praticien, programme, vidéo, pathologie) est rattachée à une `organization_id`. La sécurité est assurée via **Row-Level Security (RLS)** sur toutes les tables Supabase : un utilisateur ne peut accéder qu'aux données de son organisation.

### Modèle de données

```
organizations
  └── users (role: admin | practitioner | patient)
        ├── practitioners (specialty)
        └── patients (practitioner_id)

pathologies
  └── programs (title, description)
        └── program_videos (order_index)
              └── videos (source_type: supabase | youtube | vimeo)

patient_programs (assigned_by, mode: manual | auto)
video_progress (last_position_seconds, completed)
```

## Structure du projet

```
workspace/
├── app/
│   └── _layout.tsx          # Entry point Expo Router, routing par rôle
├── db/
│   ├── supabase.sql          # Schéma PostgreSQL complet avec RLS
│   └── models.ts             # ⚠️ Ancien fichier — à supprimer
├── src/
│   ├── components/
│   │   ├── Button.tsx        # Bouton réutilisable (primary / secondary)
│   │   ├── PatientCard.tsx   # Carte patient
│   │   ├── ProgramCard.tsx   # Carte programme
│   │   └── VideoPlayer.tsx   # Lecteur vidéo multi-source
│   ├── hooks/
│   │   ├── auth/
│   │   │   └── useCurrentUser.ts
│   │   ├── organizations/
│   │   │   └── useOrganization.ts
│   │   ├── pathologies/
│   │   │   └── usePathologies.ts
│   │   ├── patients/
│   │   │   └── usePatientPrograms.ts
│   │   ├── programs/
│   │   │   ├── useAssignProgram.ts
│   │   │   └── useProgramVideos.ts
│   │   └── videos/
│   │       ├── useVideoProgress.ts
│   │       └── useUpdateVideoProgress.ts
│   ├── lib/
│   │   └── supabase.ts       # Client Supabase
│   └── types/
│       └── db.ts             # Types TypeScript alignés sur le schéma SQL
```

## Configuration

### Variables d'environnement

Créer un fichier `.env` à la racine :

```env
EXPO_PUBLIC_SUPABASE_URL=https://<votre-projet>.supabase.co
EXPO_PUBLIC_SUPABASE_ANON_KEY=<votre-clé-anon>
```

### Path alias

Ajouter dans `tsconfig.json` :

```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    }
  }
}
```

### Base de données

Exécuter le fichier [db/supabase.sql](db/supabase.sql) dans l'éditeur SQL Supabase pour créer toutes les tables avec RLS activé.

Pour générer les types Supabase automatiquement :

```bash
npx supabase gen types typescript --project-id <project-id> > src/types/supabase.ts
```

## Installation

```bash
npm install
npx expo start
```

## Composants

### `Button`
```tsx
<Button title="Valider" onPress={handlePress} variant="primary" />
<Button title="Annuler" onPress={handleBack} variant="secondary" disabled={isLoading} />
```

### `VideoPlayer`
Supporte trois sources vidéo :
- `supabase` — fichier stocké dans Supabase Storage (lecture via `expo-av`)
- `youtube` — ID de la vidéo YouTube (embed via WebView)
- `vimeo` — ID de la vidéo Vimeo (embed via WebView)

```tsx
<VideoPlayer video={video} onPlaybackStatusUpdate={handleProgress} />
```

## Hooks principaux

| Hook | Description |
|---|---|
| `useCurrentUser` | Utilisateur connecté (auth + profil DB) |
| `useOrganization(id)` | Données de l'organisation |
| `usePathologies()` | Liste des pathologies |
| `usePatientPrograms(patientId)` | Programmes assignés à un patient |
| `useProgramVideos(programId)` | Vidéos d'un programme (ordonnées) |
| `useVideoProgress(patientId, videoId)` | Progression d'une vidéo |
| `useUpdateVideoProgress()` | Mutation upsert de la progression |
| `useAssignProgram()` | Mutation d'assignation d'un programme |

## Points d'attention connus

- `db/models.ts` est un fichier legacy à supprimer — utiliser `src/types/db.ts`
- Les hooks dupliqués à la racine de `src/hooks/` sont à consolider dans leurs sous-dossiers respectifs
- Le type `Database` pour `useAssignProgram` doit être généré via la CLI Supabase
