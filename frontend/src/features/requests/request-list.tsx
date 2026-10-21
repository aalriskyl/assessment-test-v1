import { ArrowUpRight, Box, CheckCheck, Clock3, FileText, Plus, Search } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { NativeSelect } from "@/components/ui/native-select"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Heading } from "@/components/forms"
import { StatusBadge } from "@/components/status-badge"
import { money, prNumber } from "@/lib/format"
import type { PageState } from "@/types"

export function RequestList({ state }: { state: PageState<"dashboard" | "requests"> }) {
  const d = state.data
  const overview = state.page === "dashboard"
  const title = overview
    ? "Overview"
    : d.selected_status === "submitted"
      ? "Approval queue"
      : d.selected_status === "incoming"
        ? "Incoming orders"
        : "Purchase requests"
  const showRequester = state.user?.role !== "requester"
  const metricLinks = [
    { label: "Total requests", value: d.metrics.total, href: "/requests", icon: FileText },
    {
      label: "Awaiting approval",
      value: d.metrics.pending,
      href: "/requests?status=submitted",
      icon: Clock3,
    },
    {
      label: "In progress",
      value: d.metrics.active,
      href: "/requests?status=in_progress",
      icon: Box,
    },
    {
      label: "Fully received",
      value: d.metrics.received,
      href: "/requests?status=received",
      icon: CheckCheck,
    },
  ]
  const pageLink = (page: number) =>
    `/requests?${new URLSearchParams({ page: String(page), q: d.search, status: d.selected_status })}`
  return (
    <>
      <Heading title={title}>
        {state.user?.role === "requester" && (
          <Button asChild>
            <a href="/requests/new">
              <Plus />
              New request
            </a>
          </Button>
        )}
      </Heading>
      {overview && (
        <section className="metrics" aria-label="Request summary">
          {metricLinks.map(({ label, value, href, icon: Icon }) => (
            <a href={href} key={label} className="metric">
              <div>
                {label}
                <Icon size={17} />
              </div>
              <strong>{value}</strong>
            </a>
          ))}
        </section>
      )}
      <Card className="requests-panel" id="requests">
        <div className="panel-heading">
          <h2>
            Purchase requests <span className="count">{d.total}</span>
          </h2>
        </div>
        <form className="filters" method="get" action="/requests">
          <div className="search-input">
            <Search size={16} />
            <Input
              type="search"
              name="q"
              defaultValue={d.search}
              aria-label="Search requests"
              placeholder="Search requests or PR number"
            />
          </div>
          <NativeSelect
            name="status"
            defaultValue={d.selected_status}
            aria-label="Filter by status"
          >
            <option value="">All statuses</option>
            <option value="in_progress">In progress</option>
            <option value="incoming">Incoming deliveries</option>
            {(
              [
                "draft",
                "submitted",
                "rejected",
                "approved",
                "ordered",
                "partial",
                "received",
                "cancelled",
              ] as const
            ).map((key) => (
              <option key={key} value={key}>
                {state.statusLabels[key]}
              </option>
            ))}
          </NativeSelect>
          <Button variant="outline" type="submit">
            Apply filters
          </Button>
          <a className="text-link" href="/requests">
            Reset
          </a>
        </form>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Request</TableHead>
              {showRequester && <TableHead>Requested by</TableHead>}
              <TableHead>Status</TableHead>
              <TableHead>Priority</TableHead>
              <TableHead className="numeric">Estimated value</TableHead>
              <TableHead>Required by</TableHead>
              <TableHead>
                <span className="sr-only">Open</span>
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {d.rows.map((row) => (
              <TableRow key={row.id}>
                <TableCell>
                  <a className="request-title" href={`/requests/${row.id}`}>
                    {row.title}
                  </a>
                  <small className="cell-detail">
                    {prNumber(row.id)} · {row.category} · {row.item_count}{" "}
                    {row.item_count === 1 ? "item" : "items"}
                  </small>
                </TableCell>
                {showRequester && <TableCell>{row.requester_name}</TableCell>}
                <TableCell>
                  <StatusBadge status={row.status} labels={state.statusLabels} />
                </TableCell>
                <TableCell>
                  <span className={`priority ${row.priority}`}>{row.priority}</span>
                </TableCell>
                <TableCell className="numeric amount">{money(row.total)}</TableCell>
                <TableCell className="date">{row.needed_by}</TableCell>
                <TableCell>
                  <a
                    href={`/requests/${row.id}`}
                    aria-label={`Open ${row.title}`}
                    className="row-arrow"
                  >
                    <ArrowUpRight size={17} />
                  </a>
                </TableCell>
              </TableRow>
            ))}
            {!d.rows.length && (
              <TableRow>
                <TableCell colSpan={showRequester ? 7 : 6}>
                  <div className="empty-state">
                    <FileText size={25} />
                    <h3>No requests here yet</h3>
                    <p>
                      {d.search || d.selected_status
                        ? "Try another search or clear your filters."
                        : "Your purchase requests will appear here."}
                    </p>
                    {state.user?.role === "requester" && (
                      <a className="text-link" href="/requests/new">
                        Create a request
                      </a>
                    )}
                  </div>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
        <div className="table-footer">
          <span>
            Showing {d.rows.length} {d.rows.length === 1 ? "request" : "requests"}
          </span>
          <span>
            Page {d.page} of {d.pages} · {d.total} matching requests
          </span>
        </div>
        {d.pages > 1 && (
          <div className="pagination">
            {d.page > 1 && (
              <Button variant="outline" asChild>
                <a href={pageLink(d.page - 1)}>Previous</a>
              </Button>
            )}
            {d.page < d.pages && (
              <Button variant="outline" asChild>
                <a href={pageLink(d.page + 1)}>Next</a>
              </Button>
            )}
          </div>
        )}
      </Card>
    </>
  )
}
