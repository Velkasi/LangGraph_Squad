# Application Architecture Design

## Overview
This application is a React Native mobile app built with Expo Router for navigation, Supabase for backend services, and React Query for data management. The app follows a modular structure with clear separation of concerns between UI components, data hooks, and business logic.

## Stack
- **Frontend**: React Native + Expo
- **Navigation**: Expo Router (app/ directory structure)
- **State/Data**: React Query for API data, React local state for UI
- **Backend**: Supabase (PostgreSQL, Auth, Storage)
- **Styling**: React Native StyleSheet
- **Language**: TypeScript

## Project Structure
```
app/
├─ _layout.tsx        # Root layout with providers
├─ index.tsx          # Main screen / entry point
components/           # Reusable UI components
hooks/                # Custom React hooks
lib/                  # Utilities, config, Supabase client
types/                # TypeScript interfaces
```

## Data Flow
1. Supabase provides database, authentication, and storage
2. Custom hooks (using React Query) fetch and mutate data from Supabase
3. Screens consume hooks to display data and handle user actions
4. Components are reusable UI elements used across screens

## Key Decisions
- **Expo Router**: Modern file-based routing, easy navigation
- **React Query**: Powerful caching, synchronization, and data fetching
- **Supabase**: Open-source Firebase alternative with PostgreSQL
- **TypeScript**: Type safety across frontend and backend interfaces
