import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { money } from "@/lib/format"
import type { Quote } from "@/types"

export function QuotationComparison({
  quotes,
  budget,
  revision,
}: {
  quotes: Quote[]
  budget: number
  revision: number
}) {
  return (
    <>
      {!!quotes.length && (
        <Card className="table-panel">
          <div className="panel-heading">
            <div>
              <h2>Quotation comparison</h2>
              <p>
                Revision {revision} · Budget {money(budget)}
              </p>
            </div>
          </div>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Supplier / quotation</TableHead>
                <TableHead>Lead time</TableHead>
                <TableHead className="numeric">Quoted total</TableHead>
                <TableHead>Budget</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {quotes.map((quote) => (
                <TableRow key={quote.id}>
                  <TableCell>
                    <strong>{quote.supplier_name}</strong>
                    <small className="cell-detail">{quote.reference}</small>
                  </TableCell>
                  <TableCell>
                    {quote.lead_days} {quote.lead_days === 1 ? "day" : "days"}
                  </TableCell>
                  <TableCell className="numeric amount">{money(quote.total)}</TableCell>
                  <TableCell>
                    <Badge
                      variant="outline"
                      className={quote.total <= budget ? "within-budget" : "over-budget"}
                    >
                      {quote.total <= budget ? "Within budget" : "Over budget"}
                    </Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <div className="quote-details">
            {quotes.map((quote) => (
              <details key={quote.id}>
                <summary>{quote.reference} — line prices and notes</summary>
                <ul>
                  {quote.lines.map((line) => (
                    <li key={line.id}>
                      {line.name}: {line.quantity} {line.unit} × {money(line.unit_price)}
                    </li>
                  ))}
                </ul>
                {quote.note && <p>{quote.note}</p>}
                {quote.document_id && (
                  <a
                    data-native
                    className="text-link"
                    href={`/documents/${quote.document_id}/file`}
                  >
                    Source document
                  </a>
                )}
              </details>
            ))}
          </div>
        </Card>
      )}
    </>
  )
}
