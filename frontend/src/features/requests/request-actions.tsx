import { Button } from "@/components/ui/button"
import { SecurityFields, SelectField, TextField } from "@/components/forms"
import { DeliveryForm } from "@/features/receiving/delivery-form"
import { money } from "@/lib/format"
import type { PageState } from "@/types"

export function RequestActions({ state }: { state: PageState<"detail"> }) {
  const d = state.data,
    r = d.record,
    role = state.user?.role
  const fields = <SecurityFields state={state} token={d.token} version={r.version} />
  const action = (name: string) => `/requests/${r.id}/${name}`
  const editable = role === "requester" && ["draft", "rejected", "approved"].includes(r.status)
  const waitingTitles = {
    draft: "Draft request",
    submitted: "Approval pending",
    rejected: "Changes requested",
    approved: "Awaiting purchase order",
    ordered: "Awaiting delivery",
    partial: "Delivery in progress",
    received: "All goods received.",
    cancelled: "Request closed.",
  }
  return (
    <>
      {editable ? (
        <>
          <h2>{r.status === "draft" ? "Submit request" : "Update request"}</h2>
          {r.status === "approved" && <p>Changes will require approval again.</p>}
          {r.status === "rejected" && <p>Update the request and resubmit for approval.</p>}
          <Button variant="outline" asChild className="full">
            <a href={`/requests/${r.id}/edit`}>Edit request</a>
          </Button>
          {r.status === "draft" && (
            <form method="post" action={action("submit")}>
              {fields}
              <Button type="submit" className="full">
                Submit for approval
              </Button>
            </form>
          )}
        </>
      ) : role === "approver" && r.status === "submitted" ? (
        <>
          <h2>Approval</h2>
          <form method="post" action={action("approve")}>
            {fields}
            <TextField label="Approval note (optional)" name="note" maxLength={2000} rows={2} />
            <Button type="submit" className="full">
              Approve request
            </Button>
          </form>
          <details className="reject-section">
            <summary>Request a revision</summary>
            <form method="post" action={action("reject")}>
              {fields}
              <TextField
                label="What needs to change?"
                name="note"
                required
                maxLength={2000}
                rows={3}
              />
              <Button type="submit" variant="destructive" className="full">
                Return for revision
              </Button>
            </form>
          </details>
        </>
      ) : role === "purchasing" && r.status === "approved" ? (
        <>
          <h2>Purchasing</h2>
          <Button asChild className="full">
            <a href={`/requests/${r.id}/quotations/new`}>Add quotation manually</a>
          </Button>
          <Button asChild variant="outline" className="full">
            <a href={`/requests/${r.id}/documents`}>Upload quotation</a>
          </Button>
          {!!d.quotes.length && (
            <form method="post" action={action("order")}>
              {fields}
              <SelectField label="Selected quotation" name="quotation_id" required defaultValue="">
                <option value="">Select a quotation</option>
                {d.quotes.map((quote) => (
                  <option key={quote.id} value={quote.id} disabled={quote.total > d.total}>
                    {quote.supplier_name} · {money(quote.total)} · {quote.lead_days}{" "}
                    {quote.lead_days === 1 ? "day" : "days"}
                    {quote.total > d.total ? " · Over budget" : ""}
                  </option>
                ))}
              </SelectField>
              <TextField
                label="Why this supplier?"
                name="note"
                required
                maxLength={2000}
                rows={3}
                placeholder="Price, delivery timing and suitability"
              />
              <Button type="submit" className="full">
                Issue purchase order
              </Button>
            </form>
          )}
        </>
      ) : role === "receiver" && ["ordered", "partial"].includes(r.status) ? (
        <DeliveryForm state={state} />
      ) : (
        <>
          <h2>{waitingTitles[r.status]}</h2>
          {r.status === "submitted" && <p>Waiting for an approver to review this request.</p>}
          {r.status === "approved" && <p>Purchasing will select a supplier and issue the PO.</p>}
          {["ordered", "partial"].includes(r.status) && (
            <p>The receiving team will record accepted goods.</p>
          )}
        </>
      )}
      {role === "requester" &&
        ["draft", "submitted", "rejected", "approved"].includes(r.status) && (
          <details className="reject-section">
            <summary>Cancel this request</summary>
            <form method="post" action={action("cancel")}>
              {fields}
              <p>This request will be closed and cannot be reopened.</p>
              <Button type="submit" variant="destructive" className="full">
                Confirm cancellation
              </Button>
            </form>
          </details>
        )}
    </>
  )
}
