# Application Architecture Design

## Overview
This application is built using React Native with Expo Router for navigation, Supabase for database and authentication, and React Query for data fetching and state management. The stack is TypeScript-based for type safety.

## Directory Structure
- `app/`: Contains all screens and layout files using Expo Router
  - `_layout.tsx`: Root layout with Stack navigator
  - `index.tsx`: Main screen displaying content
- `components/`: Reusable UI components
- `lib/`: Shared logic, hooks, and utilities
- `types/`: TypeScript interfaces and types

## Navigation
Expo Router is used with file-based routing. The `_layout.tsx` file defines the root stack navigator, and screens are automatically registered based on file names.

## Data Flow
1. Data is stored in Supabase PostgreSQL database
2. React Query hooks in `lib/` fetch and manage data
3. Screens consume data through these hooks
4. UI updates automatically via React Query's caching and refetching

## State Management
- Local state: React useState/useReducer
- Server state: React Query
- Authentication state: Supabase Auth + React Query

## Styling
- React Native StyleSheet for component styling
- Flexible layout using Flexbox
- Responsive design principles

## Environment Configuration
- Environment variables defined in `.env.example`
- Docker Compose for local development with Supabase

## Testing
- Unit tests for components and hooks
- Integration tests for data flow
- E2E tests for critical user journeys