# ADR 002: Frontend Architecture with Expo and React Query

## Status
Accepted

## Context
We need a mobile-first frontend architecture that supports:
- Offline usage
- Fast iteration
- Type safety
- Code sharing
- Navigation
- State management

Evaluating:
- React Native with custom setup
- Expo with managed workflow
- Next.js with NativeScript

## Decision
Use Expo with React Query for frontend architecture.

## Rationale
Expo provides:
- Unified development experience for iOS, Android, web
- Managed workflow with pre-configured build pipeline
- Expo Router for file-based routing (`app/` directory)
- Over-the-air updates
- Access to native device features

React Query provides:
- Server state management
- Automatic caching
- Background refetching
- Pagination helpers
- Mutation support with optimistic updates
- Built-in error handling

Combining Expo Router with React Query gives us a powerful, type-safe architecture for data fetching and navigation.

## Consequences
Positive:
- Rapid development
- Excellent developer experience
- Built-in best practices
- Strong TypeScript integration
- Easy testing

Negative:
- Bundle size overhead
- Some limitations in managed workflow
- Learning curve for React Query concepts (staleTime, cacheTime, etc)