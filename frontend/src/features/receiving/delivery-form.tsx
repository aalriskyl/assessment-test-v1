import { Button } from "@/components/ui/button"
import { Field, SecurityFields, TextField } from "@/components/forms"
import type { PageState } from "@/types"

export function DeliveryForm({ state }: { state: PageState<"detail"> }) {
  const d = state.data,
    r = d.record
  const fields = <SecurityFields state={state} token={d.token} version={r.version} />
  const action = (name: string) => `/requests/${r.id}/${name}`
  return (
    <>
      <h2>Record a delivery</h2>
      <p>Enter the accepted quantities for this delivery.</p>
      <form method="post" action={action("receive")}>
        {fields}
        <Field
          label="Delivery note reference"
          name="reference"
          required
          maxLength={100}
          placeholder="DO-001"
        />
        {d.order_lines.map((line) => (
          <Field
            key={line.id}
            label={`${line.name} · ${line.quantity - line.received_quantity} ${line.unit} outstanding`}
            type="number"
            name={`received_${line.id}`}
            min={0}
            max={line.quantity - line.received_quantity}
            defaultValue="0"
            required
            disabled={line.quantity === line.received_quantity}
          />
        ))}
        <TextField label="Inspection note (optional)" name="note" maxLength={2000} rows={2} />
        <Button type="submit" className="full">
          Confirm accepted goods
        </Button>
      </form>
    </>
  )
}
