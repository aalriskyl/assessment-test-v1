import {
  Building2,
  ClipboardList,
  Clock3,
  Grid2X2,
  LoaderCircle,
  LogOut,
  Package,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { SecurityFields } from "@/components/forms"
import type { ScreenState } from "@/types"

export function WorkspaceShell({
  state,
  title,
  busy,
}: {
  state: ScreenState
  title: string
  busy: boolean
}) {
  const nav = [
    {
      label: "Overview",
      href: "/",
      icon: Grid2X2,
      active: state.page === "dashboard",
    },
    {
      label: "Purchase requests",
      href: "/requests",
      icon: ClipboardList,
      active:
        (state.page === "requests" &&
          !["submitted", "incoming"].includes(state.data.selected_status)) ||
        ["detail", "request_form", "quotation_form", "upload", "order", "revision"].includes(
          state.page,
        ),
    },
    {
      label: "Approval queue",
      href: "/requests?status=submitted",
      icon: Clock3,
      active: state.page === "requests" && state.data.selected_status === "submitted",
    },
    {
      label: "Incoming orders",
      href: "/requests?status=incoming",
      icon: Package,
      active: state.page === "requests" && state.data.selected_status === "incoming",
    },
    ...(state.user?.role === "purchasing"
      ? [
          {
            label: "Suppliers",
            href: "/suppliers",
            icon: Building2,
            active: state.page === "suppliers",
          },
        ]
      : []),
  ]
  const signOut = (label: string) => (
    <form method="post" action="/logout">
      <SecurityFields state={state} />
      <Button
        variant="ghost"
        size="icon"
        type="submit"
        aria-label={label}
        title="Sign out"
        disabled={busy}
      >
        <LogOut size={17} />
      </Button>
    </form>
  )
  return (
    <>
      {state.user && (
        <>
          <aside className="sidebar">
            <a className="brand" href="/">
              <span className="brand-mark">p</span>procure<span className="brand-dot">.</span>
            </a>
            <div className="workspace">
              <span>N</span>
              <div>
                Nusantara HQ<small>Procurement</small>
              </div>
            </div>
            <nav aria-label="Main navigation">
              {nav.map(({ label, href, icon: Icon, active }) => (
                <a
                  href={href}
                  key={label}
                  className={`nav-link ${active ? "active" : ""}`}
                  aria-current={active ? "page" : undefined}
                >
                  <Icon size={18} />
                  {label}
                </a>
              ))}
            </nav>
            <div className="profile">
              <span className="avatar">{state.user.name[0]}</span>
              <div>
                {state.user.name}
                <small>{state.user.role}</small>
              </div>
              {signOut("Sign out")}
            </div>
          </aside>
          <header className="topbar">
            <div className="breadcrumb">
              Procurement<span>/</span>
              <strong>{title}</strong>
            </div>
            <div className="topbar-profile">
              {busy && <LoaderCircle size={15} className="animate-spin" aria-label="Loading" />}
              <span className="role-tag">{state.user.role}</span>
              {signOut("Sign out of workspace")}
            </div>
          </header>
        </>
      )}
    </>
  )
}
