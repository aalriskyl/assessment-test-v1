import { Printer } from "lucide-react"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Back, Heading } from "@/components/forms"
import { ItemTable } from "@/components/item-table"
import { money, poNumber, prNumber, wib } from "@/lib/format"
import type { PageState } from "@/types"

export function OrderDocument({ state }: { state: PageState<"order"> }) {
  const { record, order, lines } = state.data
  return (
    <>
      <Back href={`/requests/${record.id}`} />
      <Card className="detail-panel printable-order">
        <Heading
          title="Purchase order"
          eyebrow="Nusantara HQ · Procurement"
          subtitle={`${poNumber(order.id)} · ${wib(order.created_at)}`}
        >
          <Button variant="outline" type="button" id="print-order" onClick={() => window.print()}>
            <Printer />
            Print / Save PDF
          </Button>
        </Heading>
        <div className="detail-facts">
          <div>
            <small>Supplier</small>
            <strong>{order.supplier_name}</strong>
            <p>{order.supplier_contact}</p>
          </div>
          <div>
            <small>Quotation</small>
            <strong>{order.quotation_reference}</strong>
          </div>
          <div>
            <small>Request</small>
            <strong>
              {prNumber(record.id)} / Revision {order.request_revision}
            </strong>
          </div>
        </div>
        <ItemTable items={lines} agreed />
        <div className="order-total">
          Total (IDR)<strong>{money(order.total)}</strong>
        </div>
        <div className="purpose">
          <small>Supplier selection</small>
          <p>{order.selection_reason}</p>
        </div>
      </Card>
    </>
  )
}
