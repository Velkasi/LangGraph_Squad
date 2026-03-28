# ADR 001: Choose Supabase as Backend BaaS

## Status
Accepted

## Context
We need a backend solution that provides:
- Authentication
- Database (PostgreSQL)
- Realtime capabilities
- File storage
- type-safe APIs
- Minimal DevOps overhead

Evaluating:
- Build custom backend (Node.js + PostgreSQL)
- Use Firebase
- Use Supabase

Custom backend would require significant time to implement auth, RLS, realtime, etc.
Firebase lacks full PostgreSQL capabilities and uses NoSQL (Firestore).

## Decision
Use Supabase as our Backend-as-a-Service.

## Rationale
Supabase provides:
- Full PostgreSQL database
- Row Level Security for fine-grained access control
- Built-in auth with JWT integration
- Realtime subscriptions via WebSockets
- REST and GraphQL APIs
- TypeScript support
- Local development with Docker
- Self-hostable

It accelerates development while maintaining flexibility.

## Consequences
Positive:
- Rapid development
- Real-time features out of the box
- Strong type safety with generated types
- Easy local setup with Docker

Negative:
- Vendor-like dependency (though self-hostable)
- Learning curve for RLS policies