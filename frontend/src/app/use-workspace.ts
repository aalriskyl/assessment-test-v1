import { useCallback, useEffect, useRef, useState, type FormEvent, type MouseEvent } from "react"
import { fetchPage } from "@/lib/api"
import type { ScreenState } from "@/types"

export function useWorkspace(initial: ScreenState) {
  const [state, setState] = useState(initial)
  const [busy, setBusy] = useState(false)
  const [version, setVersion] = useState(0)
  const [networkError, setNetworkError] = useState("")
  const [actionFailure, setActionFailure] = useState<{ code: number; message: string } | null>(null)
  const errorRef = useRef<HTMLDivElement>(null)
  const requestId = useRef(0)
  const mutating = useRef(false)
  const navigation = useRef<AbortController | null>(null)
  const visibleUrl = useRef(location.pathname + location.search + location.hash)
  const mainRef = useRef<HTMLElement>(null)

  const load = useCallback(async (url: string, options: RequestInit = {}, push = true) => {
    const mutation = options.method === "POST"
    if (mutating.current) return
    mutating.current = mutation
    navigation.current?.abort()
    const controller = new AbortController()
    navigation.current = controller
    const id = ++requestId.current
    setBusy(true)
    setNetworkError("")
    setActionFailure(null)
    setState((current) => (current.flashes.length ? { ...current, flashes: [] } : current))
    try {
      const response = await fetchPage(url, { ...options, signal: controller.signal })
      const next = response.state
      if (id !== requestId.current) return
      // A rejected action must not discard the form or silently adopt a newer version.
      if (mutation && !response.ok && next.page === "error") {
        history.replaceState(null, "", visibleUrl.current)
        setActionFailure({ code: next.data.code, message: next.data.message })
        requestAnimationFrame(() => errorRef.current?.focus())
        return
      }
      const destination = new URL(response.url)
      const path = destination.pathname + destination.search
      if (
        (response.ok || !mutation) &&
        path !== location.pathname + location.search + location.hash
      ) {
        if (push) history.pushState(null, "", path)
        else history.replaceState(null, "", path)
      }
      visibleUrl.current = path
      setState(next)
      setVersion((current) => current + 1)
      window.scrollTo({ top: 0, behavior: "instant" })
      requestAnimationFrame(() => mainRef.current?.focus({ preventScroll: true }))
    } catch (error) {
      if (id !== requestId.current) return
      if (error instanceof DOMException && error.name === "AbortError") return
      // popstate changes the address before its read succeeds; keep the visible form and URL together.
      history.replaceState(null, "", visibleUrl.current)
      setNetworkError("Could not reach the server. Your entries are still here. Try again.")
    } finally {
      if (id === requestId.current) {
        setBusy(false)
        mutating.current = false
      }
    }
  }, [])
  useEffect(() => {
    const onPop = () => {
      if (mutating.current) {
        history.replaceState(null, "", visibleUrl.current)
        return
      }
      void load(location.href, {}, false)
    }
    window.addEventListener("popstate", onPop)
    return () => {
      window.removeEventListener("popstate", onPop)
      navigation.current?.abort()
    }
  }, [load])

  function onClick(event: MouseEvent<HTMLElement>) {
    if (
      event.defaultPrevented ||
      event.button !== 0 ||
      event.metaKey ||
      event.ctrlKey ||
      event.shiftKey ||
      event.altKey
    )
      return
    const target =
      event.target instanceof Element ? event.target.closest<HTMLAnchorElement>("a[href]") : null
    if (
      !target ||
      target.target ||
      target.hasAttribute("download") ||
      target.hasAttribute("data-native")
    )
      return
    const url = new URL(target.href)
    if (url.origin !== location.origin || url.pathname.endsWith("/file")) return
    event.preventDefault()
    if (mutating.current) return
    if (url.pathname === location.pathname && url.search === location.search && url.hash) {
      document.getElementById(url.hash.slice(1))?.scrollIntoView()
      return
    }
    void load(url.href)
  }
  function onSubmit(event: FormEvent<HTMLElement>) {
    const form = event.target
    if (!(form instanceof HTMLFormElement)) return
    event.preventDefault()
    if (mutating.current) return
    const body = new FormData(form)
    if (form.method.toLowerCase() === "get") {
      const url = new URL(form.action)
      url.search = ""
      body.forEach((value, key) => {
        if (typeof value === "string") url.searchParams.append(key, value)
      })
      void load(url.href)
    } else void load(form.action, { method: "POST", body })
  }
  const actionError = actionFailure ? { ...actionFailure, ref: errorRef } : null
  return { state, setState, busy, version, networkError, actionError, mainRef, onClick, onSubmit }
}
