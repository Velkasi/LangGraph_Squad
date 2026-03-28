# ADR 004: Backend Data Layer with Supabase

## Status
Accepted

## Context
We need a backend data layer that provides:
- PostgreSQL database
- Authentication
- Realtime subscriptions
- File storage
- RESTful API
- Type-safe client
- Easy local development

Evaluating:
- Custom Node.js + PostgreSQL
- Firebase
- Supabase
- Appwrite
- AWS Amplify

## Decision
Use Supabase as the backend data layer.

## Rationale
Supabase provides:
- Open-source Firebase alternative
- Full PostgreSQL database
- Row Level Security (RLS) for fine-grained access control
- Built-in authentication with JWT
- Realtime capabilities via PostgreSQL LISTEN/NOTIFY
- Storage for files and media
- Auto-generated RESTful API
- TypeScript client with type inference
- Excellent local development experience with Docker
- Self-hostable

Compared to Firebase, Supabase uses standard SQL and doesn't require learning NoSQL concepts.
Compared to a custom backend, it saves significant development time.
Compared to Appwrite, it has better PostgreSQL integration and more mature ecosystem.

## Consequences
Positive:
- Rapid backend setup
- Familiar SQL interface
- Strong security model with RLS
- Realtime capabilities out of the box
- Type safety with generated types

Negative:
- Vendor lock-in to Supabase ecosystem
- Requires understanding of PostgreSQL and RLS policies
- Limited to PostgreSQL (but this is acceptable for our needs)