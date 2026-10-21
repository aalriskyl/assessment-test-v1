import { useEffect } from "react"
import { X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { useWorkspace } from "./use-workspace"
import { WorkspaceShell } from "./workspace-shell"
import { RequestList } from "@/features/requests/request-list"
import { Detail } from "@/features/requests/request-detail"
import { RequestForm } from "@/features/requests/request-form"
import { RevisionDocument } from "@/features/requests/revision"
import { Login } from "@/features/auth/login"
import { QuotationForm } from "@/features/purchasing/quotation-form"
import { Upload } from "@/features/purchasing/upload-quotation"
import { Suppliers } from "@/features/purchasing/suppliers"
import { OrderDocument } from "@/features/purchasing/purchase-order"
import { prNumber } from "@/lib/format"
import type { ScreenState } from "@/types"

function Page({ state }: { state: ScreenState }) {
  switch (state.page) {
    case "login":
      return <Login state={state} />
    case "dashboard":
    case "requests":
      return <RequestList state={state} />
    case "detail":
      return <Detail state={state} />
    case "request_form":
      return <RequestForm state={state} />
    case "quotation_form":
      return <QuotationForm state={state} />
    case "upload":
      return <Upload state={state} />
    case "suppliers":
      return <Suppliers state={state} />
    case "order":
      return <OrderDocument state={state} />
    case "revision":
      return <RevisionDocument state={state} />
    case "error":
      return (
        <Card className="error-page">
          <span className="eyebrow">{state.data.code}</span>
          <h1>Unable to complete this action</h1>
          <p>{state.data.message}</p>
          <Button asChild>
            <a href={state.user ? "/" : "/login"}>Back to workspace</a>
          </Button>
        </Card>
      )
  }
}
function pageTitle(state: ScreenState) {
  switch (state.page) {
    case "requests":
      return state.data.selected_status === "submitted"
        ? "Approval queue"
        : state.data.selected_status === "incoming"
          ? "Incoming orders"
          : "Purchase requests"
    case "detail":
      return prNumber(state.data.record.id)
    case "request_form":
      return state.data.record ? "Edit request" : "New request"
    case "quotation_form":
      return "New quotation"
    case "upload":
      return "Upload quotation"
    case "order":
      return "Purchase order"
    case "revision":
      return `${prNumber(state.data.record.id)} / Revision ${state.data.snapshot.revision}`
    case "suppliers":
      return "Suppliers"
    case "login":
      return "Sign in"
    case "error":
      return String(state.data.code)
    default:
      return "Overview"
  }
}

export function App({ initial }: { initial: ScreenState }) {
  const { state, setState, busy, version, networkError, actionError, mainRef, onClick, onSubmit } =
    useWorkspace(initial)
  const title = pageTitle(state)
  useEffect(() => {
    document.title = `${title} · Procure`
  }, [title])
  return (
    <div
      className={state.user ? "application" : "auth-application"}
      onClick={onClick}
      onSubmitCapture={onSubmit}
    >
      <WorkspaceShell state={state} title={title} busy={busy} />
      <main
        className={state.user ? "main-content" : "auth-content"}
        id="main-content"
        tabIndex={-1}
        ref={mainRef}
        aria-busy={busy}
      >
        {state.flashes.map(([kind, message], i) => (
          <div className={`notice ${kind}`} role="status" key={`${version}-${i}`}>
            <span>{message}</span>
            <Button
              variant="ghost"
              size="icon-sm"
              type="button"
              aria-label="Dismiss notification"
              onClick={() =>
                setState((current) => ({
                  ...current,
                  flashes: current.flashes.filter((_, index) => index !== i),
                }))
              }
            >
              <X size={14} />
            </Button>
          </div>
        ))}
        {networkError && (
          <div className="notice error" role="alert">
            {networkError}
          </div>
        )}
        {actionError && (
          <div className="notice error" role="alert" tabIndex={-1} ref={actionError.ref}>
            <span>{actionError.message}</span>
            {actionError.code === 409 && (
              <a className="text-link" href={location.pathname + location.search}>
                Reload current page
              </a>
            )}
          </div>
        )}
        <fieldset disabled={busy} className="page-fieldset">
          <Page key={version} state={state} />
        </fieldset>
      </main>
    </div>
  )
}
