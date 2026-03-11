# 📚 BookWise 2 — MVP Implementation Plan

## 1. MVP Goal

Build a **local web application** that allows users to:

1. **Search books via Open Library**
2. **Open a book page**
3. Automatically **generate insights**:

   * Key Ideas
   * Critique
4. Persist results in a **SQLite database**
5. Reuse previously generated insights
6. Provide **Surprise Me** discovery from a curated YAML list.

Primary user journeys:

```
Search → Book Page → Key Ideas → Critique
Surprise Me → Book Page → Key Ideas → Critique
```

---

# 🧱 System Architecture

```
React (Vite)
     │
     │ REST API
     ▼
FastAPI Backend
     │
     ├── Open Library Client
     ├── LLM Provider (OpenAI initially)
     └── SQLite Database
```

Generation flow:

```
Book Page Opened
        │
        ▼
Check DB for insights
        │
   ┌────┴────┐
   │         │
Exists     Missing
   │         │
Return     Generate
              │
        Key Ideas first
              │
       Critique async
```

---

# 📂 Backend Project Structure

Chosen architecture: **clean modular architecture**

```
backend/
│
├── app/
│   ├── main.py
│   ├── config.py
│
│   ├── api/
│   │   ├── search.py
│   │   ├── books.py
│   │   ├── generation.py
│   │   └── surprise.py
│
│   ├── services/
│   │   ├── search_service.py
│   │   ├── book_service.py
│   │   └── generation_service.py
│
│   ├── repositories/
│   │   ├── book_repo.py
│   │   └── generation_repo.py
│
│   ├── clients/
│   │   ├── openlibrary_client.py
│   │   └── llm_client.py
│
│   ├── providers/
│   │   ├── base_provider.py
│   │   └── openai_provider.py
│
│   ├── models/
│   │   ├── book.py
│   │   └── generation.py
│
│   ├── schemas/
│   │   ├── books.py
│   │   └── generations.py
│
│   ├── prompts/
│   │   ├── key_ideas.txt
│   │   └── critique.txt
│
│   └── utils/
│       ├── logging.py
│       └── concurrency.py
│
├── curated_books.yml
└── bookwise.db
```

---

# 🗄️ Database Schema (SQLite)

### Books Table

```
books
------
id
work_id (unique)
title
authors
description
cover_url
subjects
created_at
```

---

### Generations Table

```
generations
------------
id
work_id
section (key_ideas | critique)

content TEXT

status
pending
generating
completed
failed

error_message
model
tokens_prompt
tokens_completion
generation_time
created_at
updated_at
```

Unique constraint:

```
(work_id, section)
```

Prevents duplicate generation.

---

# 🤖 LLM Provider System

Design: **pluggable provider architecture**

```
providers/
   base_provider.py
   openai_provider.py
```

Default model:

```
GPT-5-mini
```

Future providers:

```
Ollama
Anthropic
Local models
```

---

# 🧠 Generation Pipeline

### Step 1 — Book page opened

Frontend calls:

```
GET /api/books/{work_id}/key-ideas
```

Backend:

```
check DB
if exists → return
if missing → generate
```

---

### Step 2 — Key Ideas generation

Prompt context:

```
Book Title
Author
```

Output schema:

```
key_ideas: str
```

Output format:

```
• bullet point ideas
• detailed explanations
• thoughtful insights
```

Token cap:

```
5000 tokens
```

---

### Step 3 — Critique generation

Triggered **after Key Ideas finishes**.

Schema:

```
strengths: str
weaknesses: str
who_should_read: str
```

Token cap:

```
2000 tokens
```

---

# ⚡ Concurrency Control

If multiple users open same book:

```
First request → generation
Other requests → wait/poll
```

DB status:

```
pending
generating
completed
failed
```

Prevents duplicate LLM calls.

---

# 🔎 Search System

Endpoint:

```
GET /api/search?q={query}
```

Backend calls:

```
https://openlibrary.org/search.json?q={query}&limit=25
```

Fields extracted:

```
work_id
title
author_name
cover_i
```

Cover URL:

```
https://covers.openlibrary.org/b/id/{cover_i}-M.jpg
```

---

# 🎲 Surprise Me Feature

Source:

```
curated_books.yml
```

Example:

```
- work_id: OL123W
  title: Superintelligence
  author: Nick Bostrom

- work_id: OL456W
  title: Deep Work
  author: Cal Newport
```

Endpoint:

```
GET /api/surprise
```

Backend:

```
choose random book
return work_id
```

Opening it triggers generation if needed.

---

# 🖥️ Frontend Architecture

Stack:

```
React + Vite
```

Structure:

```
frontend/
│
├── src/
│   ├── pages/
│   │   ├── SearchPage.tsx
│   │   └── BookPage.tsx
│
│   ├── components/
│   │   ├── SearchBar.tsx
│   │   ├── BookCard.tsx
│   │   ├── SkeletonLoader.tsx
│   │   └── InsightTabs.tsx
│
│   ├── api/
│   │   └── bookApi.ts
│
│   └── App.tsx
```

---

# 📖 Book Page UI

Layout:

```
--------------------------------
Cover | Title | Author
--------------------------------

[ Key Ideas ] [ Critique ]
--------------------------------
Content
--------------------------------
```

---

# ⏳ Generation UI Behavior

While generating:

```
Skeleton placeholders
```

Polling strategy:

```
every 5 seconds
max 5 attempts
25 seconds total
```

If still generating:

```
Timeout message
```

---

# ❗ Error Handling

Errors returned by API:

```
{
  status: "failed",
  section: "critique",
  error: "OpenAI timeout"
}
```

UI displays **detailed error message**.

---

# 📊 Observability

Structured logging:

```
generation_started
generation_completed
generation_failed
openlibrary_fetch
book_cached
```

Metrics captured:

```
token usage
generation time
model used
section generated
```

---

# 🧩 Prompt Design

Stored in:

```
app/prompts/
```

### key_ideas.txt

Prompt instructs model to produce:

```
• detailed
• thoughtful
• well organized
• bullet format
```

---

### critique.txt

Sections required:

```
Strengths
Weaknesses
Who Should Read
```

---

# 🚀 MVP Implementation Order

Recommended development sequence.

### Phase 1 — Backend Foundations

1️⃣ FastAPI project setup
2️⃣ SQLite + SQLAlchemy models
3️⃣ Open Library client
4️⃣ Book caching system

---

### Phase 2 — Generation System

5️⃣ LLM provider abstraction
6️⃣ GPT-5-mini integration
7️⃣ Key Ideas generation
8️⃣ Critique async pipeline

---

### Phase 3 — API Layer

9️⃣ Search endpoint
10️⃣ Book endpoint
11️⃣ Generation endpoints
12️⃣ Surprise endpoint

---

### Phase 4 — Frontend

13️⃣ React + Vite setup
14️⃣ Search page
15️⃣ Book page
16️⃣ Tab interface
17️⃣ Skeleton loaders
18️⃣ Polling logic

---

### Phase 5 — Polish

19️⃣ Logging + observability
20️⃣ Error handling
21️⃣ Prompt tuning

---

# 📅 Estimated Build Time (Vibe Coding)

If working efficiently:

```
Backend foundation: 3–4 hours
Generation system: 3–5 hours
Frontend: 3–4 hours
Debugging + polish: 2–3 hours
```

**Total: ~10–16 hours**

Which is very realistic for a **weekend vibe-coding project**.

---

# ⭐ Optional Post-MVP Improvements

These would make **BookWise feel like a real product**.

### UI

* Better book cards
* Animations
* Responsive layout
* Shadcn UI

---

### Features

Add later:

```
Overview generation
Chapter summaries
Quotes extraction
Book comparisons
User accounts
Reading lists
```
