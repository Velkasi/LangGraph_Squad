# ADR 003: Server State Management with React Query

## Status
Accepted

## Context
We need to manage server state including:
- Data fetching from Supabase
- Caching of API responses
- Background synchronization
- Pagination
- Optimistic updates
- Error handling and retry logic

Evaluating:
- Redux Toolkit + RTK Query
- Apollo Client (for GraphQL)
- React Query
- Custom Context + useReducer

## Decision
Use React Query (`@tanstack/react-query`) for server state management.

## Rationale
React Query is specifically designed for server state and provides:
- Minimal boilerplate
- Automatic caching and deduplication
- Background refetching
- Pagination helpers
- Mutation support with optimistic updates
- Built-in error handling and retry mechanisms
- Devtools for debugging
- Excellent TypeScript support

Unlike Redux, it doesn't require defining actions, reducers, or thunks for data fetching.
Unlike Apollo, it works with REST APIs (our Supabase backend) without needing GraphQL.
The custom Context approach would require building all these features ourselves.

## Consequences
Positive:
- Significantly less boilerplate than Redux
- Automatic caching improves UX
- Optimistic updates provide instant feedback
- Built-in devtools
- Strong TypeScript integration

Negative:
- Additional dependency
- Learning curve around cache invalidation strategies
- Requires proper query key design