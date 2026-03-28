# Superbase and Expo App Design

## Overview
This project integrates Supabase with Expo using React Query for state management. The architecture follows a modular structure with clear separation of concerns between components, hooks, authentication, and data access.

## Data Model

### Books Table
- id: uuid (primary key)
- title: text
- author: text
- created_at: timestamp
- user_id: uuid (foreign key to auth.users)

### RLS Policies
- Users can view all books
- Users can create books (authenticated)
- Users can update/delete only their own books

## Auth Roles
- **Anonymous**: View books only
- **Authenticated**: Full CRUD (ownership-based)

## Hooks API

### `useAuth()`
- `signIn(email, password)`
- `signUp(email, password)`
- `signOut()`
- `user`
- `session`
- `isLoading`

### `useBooks()`
- `books`: Book[] | undefined
- `isLoading`: boolean
- `error`: Error | null
- `addBook(title, author)`
- `updateBook(id, updates)`
- `deleteBook(id)`

## Repository Structure
```
app/
  _layout.tsx
  index.tsx
lib/
  supabase/
    client.ts
    auth.ts
    books.ts
hooks/
  useAuth.ts
  useBooks.ts
types/
  index.ts
```