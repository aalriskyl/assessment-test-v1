import { useState } from "react"
import { Plus, X } from "lucide-react"
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
import { money } from "@/lib/format"
import type { PageState } from "@/types"

interface DraftLine {
  key: string
  name: string
  unit: string
  quantity: string
  price: string
}
export function RequestForm({ state }: { state: PageState<"request_form"> }) {
  const { values, record, token, categories } = state.data
  const [lines, setLines] = useState<DraftLine[]>(() =>
    (values.item_name ?? [""]).map((name, i) => ({
      key: crypto.randomUUID(),
      name,
      unit: values.unit?.[i] ?? "unit",
      quantity: values.quantity?.[i] ?? "1",
      price: values.unit_price?.[i] ?? "",
    })),
  )
  const [focusKey, setFocusKey] = useState("")
  const change = (key: string, field: keyof Omit<DraftLine, "key">, value: string) =>
    setLines((current) =>
      current.map((line) => (line.key === key ? { ...line, [field]: value } : line)),
    )
  const total = lines.reduce((sum, line) => {
    const value = Number(line.quantity) * Number(line.price)
    return sum + (Number.isFinite(value) ? value : 0)
  }, 0)
  const add = () => {
    if (lines.length >= 20) return
    const key = crypto.randomUUID()
    setFocusKey(key)
    setLines((current) => [...current, { key, name: "", unit: "unit", quantity: "1", price: "" }])
  }
  const action = record ? `/requests/${record.id}/edit` : "/requests/new"
  return (
    <>
      <Back href="/requests">Purchase requests</Back>
      <Heading
        title={record ? "Edit purchase request" : "New purchase request"}
        subtitle={
          record?.status === "approved"
            ? "Saving changes returns this request to draft for approval."
            : undefined
        }
      />
      <form method="post" action={action} className="request-form">
        <SecurityFields
          state={state}
          token={token}
          version={record ? valueOf(values, "version", String(record.version)) : undefined}
        />
        <Card className="form-panel">
          <h2>Request details</h2>
          <Field
            label="Request title"
            name="title"
            required
            maxLength={120}
            placeholder="e.g. Laptops for the design team"
            defaultValue={valueOf(values, "title")}
          />
          <div className="form-grid">
            <SelectField
              label="Category"
              name="category"
              required
              defaultValue={valueOf(values, "category", categories[0])}
            >
              {categories.map((category) => (
                <option key={category}>{category}</option>
              ))}
            </SelectField>
            <SelectField
              label="Priority"
              name="priority"
              defaultValue={valueOf(values, "priority", "normal")}
            >
              {["normal", "high", "low"].map((priority) => (
                <option key={priority} value={priority}>
                  {priority[0].toUpperCase() + priority.slice(1)}
                </option>
              ))}
            </SelectField>
            <Field
              label="Required by"
              name="needed_by"
              type="date"
              required
              defaultValue={valueOf(values, "needed_by")}
            />
          </div>
          <TextField
            label="Business purpose"
            name="purpose"
            required
            maxLength={2000}
            rows={3}
            placeholder="Reason for this purchase"
            defaultValue={valueOf(values, "purpose")}
          />
          {record && (
            <TextField
              label="Revision summary"
              name="note"
              required
              maxLength={2000}
              rows={2}
              placeholder="What changed and why?"
              defaultValue={valueOf(values, "note")}
            />
          )}
        </Card>
        <Card className="form-panel">
          <div>
            <h2>Line items</h2>
            <p>Up to 20 items. Use whole quantities and IDR amounts.</p>
          </div>
          <div id="line-items">
            {lines.map((line) => (
              <div className="line-item" key={line.key}>
                <Field
                  label="Item description"
                  name="item_name"
                  required
                  maxLength={160}
                  placeholder="Item name and specifications"
                  autoFocus={line.key === focusKey}
                  value={line.name}
                  onChange={(e) => change(line.key, "name", e.target.value)}
                />
                <Field
                  label="Unit"
                  name="unit"
                  required
                  maxLength={30}
                  value={line.unit}
                  onChange={(e) => change(line.key, "unit", e.target.value)}
                />
                <Field
                  label="Quantity"
                  name="quantity"
                  type="number"
                  min={1}
                  max={10000}
                  required
                  value={line.quantity}
                  onChange={(e) => change(line.key, "quantity", e.target.value)}
                />
                <Field
                  label="Unit price (IDR)"
                  name="unit_price"
                  type="number"
                  min={1}
                  max={100000000000}
                  required
                  value={line.price}
                  onChange={(e) => change(line.key, "price", e.target.value)}
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  aria-label="Remove item"
                  disabled={lines.length === 1}
                  onClick={() =>
                    setLines((current) => current.filter((item) => item.key !== line.key))
                  }
                >
                  <X />
                </Button>
              </div>
            ))}
          </div>
          <div className="line-item-footer">
            <Button
              type="button"
              variant="outline"
              id="add-item"
              disabled={lines.length >= 20}
              onClick={add}
            >
              <Plus />
              Add line item
            </Button>
            <div className="estimate">
              Estimated total<strong id="estimated-total">{money(total)}</strong>
            </div>
          </div>
        </Card>
        <div className="form-actions">
          <Button asChild variant="outline">
            <a href={record ? `/requests/${record.id}` : "/requests"}>Cancel</a>
          </Button>
          <Button type="submit">{record ? "Save revision" : "Save draft"}</Button>
        </div>
      </form>
    </>
  )
}
