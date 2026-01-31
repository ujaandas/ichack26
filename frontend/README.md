# Hackathon Starterkit Frontend

This directory contains the React frontend for the project. It is intentionally minimal, using plain React with Vite, TanStack Router (file‑based routing), TailwindCSS, and a HeyAPI‑generated SDK for typed communication with the backend.

The goal is to keep the stack simple, explicit, and easy to extend without introducing framework‑level abstractions.

---

# Overview

The frontend is organized into a small number of predictable directories:

- `src/routes/` — File‑based routing (TanStack Router)
- `src/components/` — Reusable UI components
- `src/client/` — Generated HeyAPI client (SDK + types)
- `src/lib/` — Helpers, utilities, configuration
- `src/styles.css` — TailwindCSS setup

Routing is handled by TanStack Router’s file‑based routing plugin.  
API calls are made through the generated HeyAPI SDK.

---

# Running the Frontend

Install dependencies:

```sh
pnpm install
```

Start the dev server:

```sh
pnpm dev
```

The app will be available at:

```sh
http://localhost:3000
```

---

# Routing

Routes live in `src/routes/` and are automatically picked up by TanStack Router’s file‑based routing plugin.

A basic route looks like:

```ts
// src/routes/index.tsx
import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/')({
  component: () => <div>Hello, world</div>,
})
```

Naturally, nested routes follow folder structure:

```sh
src/routes/
  index.tsx
  dashboard/
    index.tsx
    settings.tsx
```

Dynamic routes use `$param`:

```sh
src/routes/users/$userId.tsx
```

---

# Calling the Backend

The frontend uses a HeyAPI‑generated SDK for typed API calls.
The client is generated into:

```sh
src/client/
```

To regenerate the client after backend changes:

```sh
pnpm run openapi
```

A typical API call inside a route:

```ts
import { createFileRoute } from '@tanstack/react-router'
import { healthHealthGet } from '@/client'

export const Route = createFileRoute('/')({
  loader: () => healthHealthGet(),
  component: Home,
})

function Home() {
  const data = Route.useLoaderData()
  return <pre>{JSON.stringify(data)}</pre>
}
```

Loaders run on the server (RSC‑compatible) and provide data to the component.

---

# Adding a New Page

To add a new page (e.g., `/about`):

1. Create a file:

```sh
src/routes/about.tsx
```

2. Add a route definition:

```sh
import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/about')({
  component: () => <div>About page</div>,
})
```

3. Visit:

```sh
http://localhost:5173/about
```
