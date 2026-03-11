# Frontend Summary (Current Implementation)

This document summarizes how the `frontend/` app in BookWise 2 currently works, based on the code in this repository.

## 1) What the frontend is

The frontend is a React + TypeScript single-page app built with Vite. It has two routes:

- `/`: search and discovery page
- `/book/:workId`: detailed book page with generated sections and external enrichment

Entry point and routing:

- `src/main.tsx` mounts `<App />` inside `BrowserRouter`
- `src/App.tsx` defines route mapping via `react-router-dom`

## 2) Tech stack and why it appears to be used

## Runtime and build

- React 18 (`react`, `react-dom`): component/state model for UI
- TypeScript (`strict: true`): typed API contracts and safer refactors
- Vite: fast local dev server and production bundling
- React Router v6: client-side route transitions between search and detail pages

## Styling and UI composition

- Primary styling is custom CSS in `src/index.css`
- There is a lightweight internal UI layer (`Button`, `Input`, `Card`, `ScrollArea`) under `src/components/ui`
- `cn()` utility in `src/lib/utils.ts` is a minimal class joiner

Tailwind-related packages/config are present (`tailwindcss`, `tailwind.config.ts`, `components.json`), but current UI classes are mostly handcrafted CSS classes (`bw-*`, layout classes, section classes). In practice, this frontend currently behaves as a custom-CSS app with typed React components.

## API communication

- Centralized API client in `src/api.ts`
- Uses `fetch` against `VITE_API_BASE` (fallback: `http://localhost:8000/api`)
- Strongly typed request/response interfaces for search, book metadata, generated sections, videos, and links
- Error normalization via custom `ApiError` and `formatError`
- Captures `X-Request-ID` metadata for endpoints called via `fetchJsonWithMeta`

Apparent rationale:

- Keep component code simple by moving HTTP/error details into one module
- Preserve backend observability IDs for troubleshooting

## 3) Route-level behavior

## A. Search page (`/`)

Implemented inside `SearchPage` in `src/App.tsx`.

### State managed

- `queryInput`: immediate textbox value
- `query`: debounced value used for API calls
- `loading`, `error`, `results`
- `prefetchingId`: indicates which selected book is being prefetched

### Search flow

1. User types into `SearchBar`
2. `queryInput` is debounced by 1000ms (`useEffect` + `setTimeout`)
3. On debounced `query` change:
   - empty query clears state
   - non-empty query calls `api.search(query)`
   - results are capped to 25 items
4. UI states in `SearchResultsPanel`:
   - no query: render nothing
   - loading: "Searching..."
   - error: `<pre className="error-box">...`
   - empty: "No books found."
   - success: scrollable card list

### Open-book flow

When user clicks `Open Book` on a result card:

1. Frontend sets `prefetchingId`
2. Calls `api.getBook(work_id)` to warm metadata (best-effort)
3. Navigates to `/book/:workId` even if prefetch fails

Apparent rationale: perceived speed and earlier error surfacing without blocking navigation.

### Surprise flow

- `Surprise Me` triggers `api.surprise()`
- On success navigates directly to `/book/:workId`

## B. Book detail page (`/book/:workId`)

Implemented in `src/components/book/BookDetailsPage.tsx`.

This page orchestrates six content sections:

1. Summary
2. Key Ideas
3. Critique
4. Related Videos
5. Other Books by Same Author
6. Explore More

### State shape

Each section uses `SectionState<T>`:

- `data: T | null`
- `loading: boolean`
- `error: string | null`

Also tracks:

- `book` metadata + `bookError`
- `activeSection` for sticky nav highlighting and mobile select
- `selectedVideo` for modal player

### Loading/generation orchestration

#### 1) Metadata fetch

On `workId` change, page resets all state and fetches `api.getBook(workId)`.

#### 2) Sequential generated sections

`runSections()` executes in strict sequence:

1. Poll summary endpoint until terminal state
2. Only if summary completes, poll key ideas
3. Only if key ideas complete, poll critique
4. Only if critique completes, prefetch external sections

Polling logic (`pollSection`):

- interval: 5 seconds
- max polls: 18
- pending statuses: `pending` or `generating`
- timeout message after max polls: "Generation is taking longer than expected. Please refresh the page."

Retry support:

- Summary/Key Ideas/Critique components expose `Retry`
- Retry calls `runSections({ summary: true })`, etc.
- This sets `?retry=true` on the corresponding endpoint call

Important current behavior:

- The frontend now includes **summary-first** orchestration before key ideas and critique.
- This differs from older MVP descriptions that mention key ideas first.

#### 3) External sections fetch

After critique completion, `prefetchExternalSections()` runs:

- In parallel via `Promise.allSettled`:
  - `/books/{id}/other-books`
  - `/books/{id}/youtube-videos`
- Then fetches `/books/{id}/explore-more`

Errors are isolated per section, so one failing section does not block others.

### Navigation behavior

Desktop:

- Left sticky rail with cover + section buttons (`StickyBookRail`, `SectionNav`)
- Active section is computed from viewport position (`getBoundingClientRect` with 120px activation offset)

Mobile:

- Top card header with cover/title/author + `<select>` jump menu
- Desktop rail hidden via media query

## 4) Component responsibilities

## Search components

- `SearchBar`: input + Surprise button
- `SearchResultsPanel`: conditional rendering for loading/error/empty/success
- `SearchResultCard`: book card with cover fallback and Open button

## Book content components

- `SummarySection`: skeleton, error+retry, failed state, rendered summary + source
- `KeyIdeasSection`: skeleton, error+retry, text rendered in `<pre>`
- `CritiqueSection`: skeleton, error+retry, strengths/weaknesses/who should read
- `AuthorBooksSection` + `AuthorGroup` + `BookMiniCard`: grouped related books with internal navigation links
- `YouTubeVideosSection` + `VideoGrid` + `VideoCard`: related videos list
- `VideoModalPlayer`: overlay modal with embedded YouTube iframe, close on Escape/backdrop/button
- `ExploreMoreSection`: external cards for Amazon, Goodreads, and author website fallback card

## Landing quote panel

`LandingQuotePanel`:

- Reads `src/content/landing_quotes.yml` as raw text (`?raw` import)
- Parses YAML-like structure with a custom line parser (`parseQuotesYaml`)
- Rotates quotes every 15s with fade transition timing (`FADE_MS = 260`)

Note: attribution is parsed but not rendered in current UI.

## 5) API contract coverage used by frontend

The frontend calls these backend endpoints:

- `GET /api/search?q=...`
- `GET /api/books/{workId}`
- `GET /api/books/{workId}/summary[?retry=true]`
- `GET /api/books/{workId}/key-ideas[?retry=true]`
- `GET /api/books/{workId}/critique[?retry=true]`
- `GET /api/books/{workId}/other-books`
- `GET /api/books/{workId}/youtube-videos`
- `GET /api/books/{workId}/explore-more`
- `GET /api/surprise`

Typed response models in `api.ts` include generation metadata fields (`model`, token counts, duration, status, timestamps), though most section components currently display only user-facing text/error/source.

## 6) Styling and responsiveness

Styling is centralized in `src/index.css`.

Key characteristics:

- CSS variable palette (`--bg`, `--ink`, `--muted`, etc.)
- Typographic mix using Google Fonts for headings/subheadings
- Reusable class patterns for buttons/cards/placeholders/errors/skeletons
- Layout breakpoints primarily at `max-width: 700px`

Responsive adjustments include:

- Search controls collapse to one column
- Book detail layout collapses from two-column to single column
- Card grids reduce columns (author books, videos, explore links)
- Mobile-only header/select replaces desktop sticky rail

## 7) Operational notes for frontend development

- Dev server script: `npm run dev` (port `5173`)
- Backend base URL can be overridden via `VITE_API_BASE`
- Default API base assumes local backend at `http://localhost:8000/api`
- The app expects backend CORS to allow `http://localhost:5173` (configured in backend settings)

## 8) Current architecture summary

The frontend is a route-driven React SPA with:

- one central typed API client,
- route-level orchestration in `App.tsx` and `BookDetailsPage.tsx`,
- presentational section components for each content block,
- custom CSS-driven design system,
- sequential generation polling followed by external enrichment fetches.

This structure keeps async workflow control concentrated in one page component while leaving rendering concerns in focused subcomponents.
