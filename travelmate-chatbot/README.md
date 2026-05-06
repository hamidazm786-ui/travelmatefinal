# Travelmate Chatbot — Drop-in Files

These are the exact files that power the `/chat` page you see in the preview.
If your VS Code project doesn't look the same, it's almost always because
**one of the supporting pieces is missing** (design tokens, fonts, tailwind
plugin, or a dependency). Copy ALL of the files below — not just `Chat.tsx`.

## File map → where to put them

| From this zip            | Copy to (in your project)            |
|--------------------------|--------------------------------------|
| `src/pages/Chat.tsx`     | `src/pages/Chat.tsx`                 |
| `src/lib/chatApi.ts`     | `src/lib/chatApi.ts`                 |
| `src/lib/chatStore.ts`   | `src/lib/chatStore.ts`               |
| `src/lib/utils.ts`       | `src/lib/utils.ts` (if missing)      |
| `src/components/AppNavbar.tsx` | `src/components/AppNavbar.tsx` (adds the Chat link) |
| `src/index.css`          | merge the `:root` tokens + `@layer` blocks into your own `src/index.css` |
| `tailwind.config.ts`     | merge `colors.gold`, `colors.ink`, fonts, and the `@tailwindcss/typography` plugin |

## 1. Install dependencies

```bash
npm i react-markdown zustand sonner lucide-react react-router-dom clsx tailwind-merge
npm i -D @tailwindcss/typography
```

(You also need: `react`, `react-dom`, `tailwindcss`, `vite` — standard
Vite + React + TS + Tailwind setup.)

## 2. Add the route

In your router (e.g. `src/App.tsx`):

```tsx
import Chat from "@/pages/Chat";
// ...
<Route path="/chat" element={<Chat />} />
```

The page also expects a layout with a top navbar (it uses
`h-[calc(100vh-6.5rem)]`). If you don't have one, just wrap `<Chat />` in
your own layout or remove that height calculation.

## 3. Fonts (critical for the look)

In `index.html` `<head>` OR at the top of `src/index.css`:

```css
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400;1,500;1,600&family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@300;400;500&display=swap');
```

Without these fonts the chat will look like plain Arial — that's the #1
reason "it doesn't look the same".

## 4. Design tokens (also critical)

Open the `src/index.css` in this zip and copy the entire `@layer base`
`:root { ... }` block into your own `src/index.css`. These are the gold/ink
HSL variables every chat class depends on (`bg-ink`, `text-gold`, `gold/15`,
etc.).

## 5. Tailwind config

Make sure your `tailwind.config.ts` has:

- `colors.gold` (DEFAULT, bright, deep)
- `colors.ink` (DEFAULT, soft)
- The fonts (`display`, `sans`, `mono`)
- `plugins: [require("@tailwindcss/typography"), require("tailwindcss-animate")]`

Just copy the `tailwind.config.ts` from this zip if you don't have heavy
custom config of your own.

## 6. Backend

The chatbot calls `http://localhost:8000/api/v1` by default and falls back
to **demo mode** if it can't reach the backend. To point at a different URL
create `.env` in your project root:

```
VITE_CHAT_API_BASE=http://localhost:8000/api/v1
```

Then restart the dev server.

## 7. Run

```bash
npm run dev
```

Open `http://localhost:5173/chat`.

---

### Common reasons it looks different in VS Code

1. ❌ Forgot to copy `index.css` tokens → no gold colour, no dark bg
2. ❌ Forgot the Google Fonts `@import` → wrong typography
3. ❌ Forgot `@tailwindcss/typography` plugin → markdown bubbles look plain
4. ❌ Forgot to install `react-markdown`, `zustand`, `sonner`, `lucide-react`
5. ❌ No `<Toaster />` in your `App.tsx` → toasts won't show (add `import { Toaster } from "sonner"; <Toaster />`)
6. ❌ Your project doesn't have the `cn()` util — copy `src/lib/utils.ts`

If after all that it still doesn't match, tell me which step failed and I'll
fix it.
