# Frontend

React + TypeScript, Vite, Tailwind and shadcn/ui. Flask serves the built application at its existing URLs.

```powershell
npm.cmd ci
npm.cmd run build
npm.cmd test
npm.cmd run format:check
```

Use Node 24. Build checks strict TypeScript and writes hashed assets plus a manifest into `../procurement/static/app`. The bundle is included for the Python-only reviewer quick start. Rebuild after changing source, then reload the page. The Flask server remains the application entrypoint; Vite's standalone dev server does not supply authenticated view data.

## Responsibilities

| Folder | Responsibility |
| --- | --- |
| `src/app` | Page composition, workspace shell, navigation and pending-request lifecycle |
| `src/features/requests` | List/filter, request form, detail, actions, revision and activity views |
| `src/features/purchasing` | Suppliers, document input, quotation review/comparison and purchase order |
| `src/features/receiving` | Accepted delivery form |
| `src/features/auth` | Sign-in screen |
| `src/components/ui` | Local shadcn visual primitives |
| `src/components` | Shared forms, status badge and item table |
| `src/lib` | Same-origin HTTP transport, formatting and class-name helpers |
| `src/types.ts` | Discriminated page DTOs, role and status contracts |

Feature components keep their form state locally. Persisted state, permissions, totals, transitions, versions and retry protection belong to Python operations. Shared UI must not import a feature. Split a feature further when its responsibilities grow; do not add layers merely to make the folder tree larger.

## Data and navigation

`procurement/presentation.py` serializes public view data. Normal navigation returns the HTML shell with escaped JSON; subsequent navigation requests the same URL with `Accept: application/json`. Authentication remains a same-origin HttpOnly session. Forms include a CSRF token and any required version/operation token. Downloads keep native browser behavior.

Overview uses `/`; the request list and queues use `/requests` with URL query filters. Sidebar selection and titles derive from the returned page/status. Filters, Reset and pagination stay in the request list. Older root query links redirect to the canonical list route.

The shared request hook cancels superseded reads, ignores late responses and errors, prevents duplicate in-flight form submissions and retains input after network failures. Rejected actions show an inline error while preserving the current form and its original version; conflicts offer an explicit reload. Server read errors render an error screen. Server validation returns form values without passwords. Navigation does not add duplicate history entries for the same URL, and back/forward canonical redirects replace the current history URL. If a history read fails offline, the current entry's URL is restored to the visible form instead of displaying it under the unloaded destination. Deep links resolve through Flask.

To add a screen, first add its Python read view and explicit public fields, extend the page union in `types.ts`, implement its feature component, then wire composition in `app/App.tsx`. Keep provider credentials exclusively in server environment variables. Never expose an API key through bootstrap JSON or a `VITE_` variable.

## Time and verification

`lib/format.ts` converts UTC event timestamps to WIB using `Asia/Jakarta`. Calendar delivery dates remain unchanged. Node tests cover timezone boundaries. Python regression covers authorization, data serialization and business operations. The [browser regression suite](../tests/test_browser.py) runs only against a disposable seeded database; setup is in the root README. Check commands are in the [root README](../README.md); application boundaries are in [scope](../docs/scope.md).
