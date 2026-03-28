# ADR 001: Technical Architecture Overview

## Status
Accepted

## Context
We are building a mobile e-commerce application using Expo, Supabase, and React Query. The app needs to handle user authentication, product browsing, cart management, and order processing.

Key constraints:
- Must be mobile-first and offline-capable
- Data synchronization must be reliable
- Team has strong TypeScript proficiency
- Prefer open-source and self-hostable solutions

## Decision
We will use the following architecture:

1. **Frontend**: Expo with React Native, Expo Router for navigation
2. **State Management**: React Query for server state, React Context for limited local state
3. **Backend**: Supabase (PostgreSQL + Auth + Realtime) hosted locally for development
4. **Data Fetching**: RESTful API patterns with TypeScript interfaces
5. **Authentication**: Supabase Auth with JWT
6. **Realtime**: Supabase Realtime for live updates where needed

The application will follow a clean architecture pattern with:
- `src/types/` for shared TypeScript types
- `src/lib/` for business logic and service classes
- `src/hooks/` for React Query hooks
- `src/components/` for UI components
- `src/app/` for Expo Router page components

## Consequences
**Pros:**
- TypeScript types ensure type safety across layers
- React Query simplifies data fetching and caching
- Supabase provides a complete backend solution
- Expo enables cross-platform mobile development

**Cons:**
- Learning curve for team members new to Supabase
- Vendor lock-in risk with Supabase-specific features
- Additional complexity from multiple libraries

## Alternatives Considered
- Firebase + Firestore: Rejected due to preference for SQL and self-hosting
- Custom Node.js API: Rejected due to increased development time
- Apollo Client + GraphQL: Rejected as overkill for current needs