import { useState } from "react"
import { Paperclip } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import {
  Back,
  Field,
  Heading,
  SecurityFields,
  SelectField,
  TextField,
  valueOf,
} from "@/components/forms"
import { money, prNumber } from "@/lib/format"
import type { PageState } from "@/types"

export function QuotationForm({ state }: { state: PageState<"quotation_form"> }) {
  const { record, items, suppliers, values, token, document, extraction } = state.data
  const [prices, setPrices] = useState<Record<number, string>>(() =>
    Object.fromEntries(items.map((item) => [item.id, valueOf(values, `price_${item.id}`)])),
  )
  return (
    <>
      <Back href={`/requests/${record.id}`}>{prNumber(record.id)}</Back>
      <Heading
        title="New quotation"
        subtitle={`${prNumber(record.id)} · Revision ${record.revision}`}
      />
      {document && (
        <Card className="detail-panel extraction-review">
          <div className="inline-heading">
            <h2>Source document</h2>
            <a className="text-link" data-native href={`/documents/${document.id}/file`}>
              <Paperclip size={14} />
              Open source document
            </a>
          </div>
          <p>
            {document.original_name} ·{" "}
            {{
              local_pdf: "PDF text extraction",
              ai: "AI extraction",
              failed: "Manual entry required",
              pending: "Processing",
            }[document.extraction_mode] ?? document.extraction_mode}
          </p>
          {document.media_type !== "application/pdf" && (
            <img
              className="source-image"
              src={`/documents/${document.id}/file`}
              alt="Uploaded supplier quotation"
            />
          )}
          {extraction ? (
            <details className="extraction-details">
              <summary>View extracted data</summary>
              <p>
                {extraction.supplier ?? "Supplier not identified"} ·{" "}
                {extraction.reference ?? "Reference not identified"}
              </p>
              {extraction.warnings.map((warning, i) => (
                <p className="field-help" key={i}>
                  {warning}
                </p>
              ))}
              {extraction.lines.map((line, i) => (
                <div className="extracted-source-line" key={i}>
                  <strong>
                    {line.name ?? "Unknown item"} · {money(line.unit_price)}
                  </strong>
                  <p>
                    {line.quantity ?? "Unknown"} {line.unit ?? ""} ·{" "}
                    {line.evidence ?? "No source text available"}
                  </p>
                </div>
              ))}
            </details>
          ) : (
            <p>Extraction was unsuccessful. Enter the quotation details below.</p>
          )}
        </Card>
      )}
      <form method="post" action={`/requests/${record.id}/quotations/new`} className="request-form">
        <SecurityFields
          state={state}
          token={token}
          version={valueOf(values, "version", String(record.version))}
        />
        {valueOf(values, "document_id") && (
          <input type="hidden" name="document_id" value={valueOf(values, "document_id")} />
        )}
        <Card className="form-panel">
          <h2>Supplier and terms</h2>
          <div className="form-grid">
            <SelectField
              label="Supplier"
              name="supplier_id"
              required
              defaultValue={valueOf(values, "supplier_id")}
            >
              <option value="">Select supplier</option>
              {suppliers.map((supplier) => (
                <option key={supplier.id} value={supplier.id}>
                  {supplier.name}
                </option>
              ))}
            </SelectField>
            <Field
              label="Quotation reference"
              name="reference"
              required
              maxLength={100}
              defaultValue={valueOf(values, "reference")}
            />
            <Field
              label="Delivery lead time (days)"
              name="lead_days"
              type="number"
              min={0}
              max={365}
              required
              defaultValue={valueOf(values, "lead_days")}
            />
          </div>
          <TextField
            label="Quotation note (optional)"
            name="note"
            maxLength={2000}
            rows={2}
            defaultValue={valueOf(values, "note")}
          />
        </Card>
        <Card className="form-panel">
          <div>
            <h2>Agreed unit prices</h2>
            <p>
              Quantities follow the approved request. Prices in IDR, excluding tax and discounts.
            </p>
          </div>
          {items.map((item) => (
            <div className="quote-price-row" key={item.id}>
              <div>
                <strong>{item.name}</strong>
                <small>
                  {item.quantity} {item.unit} · estimated {money(item.unit_price)} each
                </small>
              </div>
              {extraction && (
                <SelectField
                  label="Use extracted line"
                  className="extracted-line-select"
                  defaultValue=""
                  onChange={(e) => {
                    if (e.target.value)
                      setPrices((current) => ({ ...current, [item.id]: e.target.value }))
                  }}
                >
                  <option value="">Choose and verify</option>
                  {extraction.lines
                    .filter((line) => line.unit_price !== null)
                    .map((line, i) => (
                      <option key={i} value={String(line.unit_price)}>
                        {line.name ?? "Unknown item"} · {money(line.unit_price)}
                      </option>
                    ))}
                </SelectField>
              )}
              <Field
                label={`Unit price for ${item.name}`}
                name={`price_${item.id}`}
                type="number"
                min={1}
                max={100000000000}
                required
                value={prices[item.id]}
                onChange={(e) =>
                  setPrices((current) => ({ ...current, [item.id]: e.target.value }))
                }
              />
            </div>
          ))}
          <label className="checkbox-label">
            <input type="checkbox" name="reviewed" value="yes" required />I checked the supplier,
            currency, prices, quantities and lead time against the quotation.
          </label>
        </Card>
        <div className="form-actions">
          <Button asChild variant="outline">
            <a href={`/requests/${record.id}`}>Cancel</a>
          </Button>
          <Button type="submit">Save reviewed quotation</Button>
        </div>
      </form>
    </>
  )
}
