import { Card } from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Back, Heading } from "@/components/forms"
import { ItemTable } from "@/components/item-table"
import { StatusBadge } from "@/components/status-badge"
import { QuotationComparison } from "@/features/purchasing/quotation-comparison"
import { RequestActions } from "./request-actions"
import { RequestHistory } from "./request-history"
import { money, prNumber, wib } from "@/lib/format"
import type { PageState } from "@/types"

export function Detail({ state }: { state: PageState<"detail"> }) {
  const d = state.data,
    r = d.record
  const changes = d.events.find((event) => event.action === "Revision requested")
  return (
    <>
      <Back href="/requests">Purchase requests</Back>
      <Heading
        title={r.title}
        eyebrow={`${prNumber(r.id)} · Revision ${r.revision} · ${r.category}`}
        subtitle={`Requested by ${d.requester.name} · Created ${wib(r.created_at, true)}`}
      >
        <StatusBadge status={r.status} labels={state.statusLabels} />
      </Heading>
      {r.status === "rejected" && changes && (
        <div className="notice">
          <strong>Changes requested by {changes.name}</strong>
          <p>{changes.note}</p>
        </div>
      )}
      <div className="detail-layout">
        <div className="detail-main">
          <Card className="detail-panel">
            <h2>Request summary</h2>
            <div className="detail-facts">
              <div>
                <small>Estimated budget</small>
                <strong>{money(d.total)}</strong>
              </div>
              <div>
                <small>Required by</small>
                <strong>{r.needed_by}</strong>
              </div>
              <div>
                <small>Priority</small>
                <strong className={`priority ${r.priority}`}>{r.priority}</strong>
              </div>
            </div>
            <div className="purpose">
              <small>Business purpose</small>
              <p>{r.purpose}</p>
            </div>
          </Card>
          <Card className="table-panel">
            <div className="panel-heading">
              <h2>
                Requested items <span className="count">{d.items.length}</span>
              </h2>
            </div>
            <ItemTable items={d.items} />
          </Card>
          <QuotationComparison quotes={d.quotes} budget={d.total} revision={r.revision} />
          {d.order && (
            <>
              <Card className="detail-panel">
                <div className="inline-heading">
                  <h2>Purchase order</h2>
                  <a className="text-link" href={`/requests/${r.id}/order`}>
                    View purchase order
                  </a>
                </div>
                <div className="detail-facts">
                  <div>
                    <small>Supplier</small>
                    <strong>{d.order.supplier_name}</strong>
                  </div>
                  <div>
                    <small>Quotation reference</small>
                    <strong>{d.order.quotation_reference}</strong>
                  </div>
                  <div>
                    <small>Agreed order total</small>
                    <strong>{money(d.order.total)}</strong>
                  </div>
                </div>
                <div className="purpose">
                  <small>Supplier selection</small>
                  <p>{d.order.selection_reason}</p>
                </div>
              </Card>
              <Card className="table-panel">
                <div className="panel-heading">
                  <h2>Ordered items and acceptance</h2>
                </div>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Item</TableHead>
                      <TableHead>Quantity</TableHead>
                      <TableHead className="numeric">Unit price</TableHead>
                      <TableHead className="numeric">Accepted</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {d.order_lines.map((line) => (
                      <TableRow key={line.id}>
                        <TableCell>{line.name}</TableCell>
                        <TableCell>
                          {line.quantity} {line.unit}
                        </TableCell>
                        <TableCell className="numeric">{money(line.unit_price)}</TableCell>
                        <TableCell className="numeric">
                          {line.received_quantity} / {line.quantity}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </Card>
            </>
          )}
          {!!d.receipts.length && (
            <Card className="detail-panel">
              <h2>Delivery records</h2>
              {d.receipts.map((receipt) => (
                <div className="receipt" key={receipt.id}>
                  <strong>{receipt.delivery_reference}</strong>
                  <small>
                    {receipt.name} · {wib(receipt.created_at)}
                  </small>
                  {receipt.note && <p>{receipt.note}</p>}
                  <ul>
                    {receipt.lines.map((line, i) => (
                      <li key={i}>
                        {line.name}: {line.quantity} {line.unit} accepted
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </Card>
          )}
          <RequestHistory events={d.events} revisions={d.revisions} requestId={r.id} />
        </div>
        <aside className="detail-side">
          <Card className="detail-panel">
            <RequestActions state={state} />
          </Card>
        </aside>
      </div>
    </>
  )
}
