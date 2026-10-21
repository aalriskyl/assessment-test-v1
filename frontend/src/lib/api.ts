import type { ScreenState } from "@/types"

const pages = [
  "login",
  "dashboard",
  "requests",
  "detail",
  "request_form",
  "quotation_form",
  "upload",
  "suppliers",
  "order",
  "revision",
  "error",
]
export function parseState(value: unknown): ScreenState {
  if (
    !value ||
    typeof value !== "object" ||
    !("page" in value) ||
    !pages.includes(String(value.page)) ||
    !("csrfToken" in value) ||
    typeof value.csrfToken !== "string" ||
    !("data" in value) ||
    !value.data ||
    typeof value.data !== "object"
  )
    throw new Error("Invalid application response")
  return value as ScreenState
}

export async function fetchPage(url: string, options: RequestInit) {
  const response = await fetch(url, {
    ...options,
    headers: { Accept: "application/json" },
    credentials: "same-origin",
  })
  if (!response.headers.get("content-type")?.includes("application/json"))
    throw new Error("Unexpected response")
  return { state: parseState(await response.json()), url: response.url, ok: response.ok }
}
