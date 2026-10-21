import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Field, Heading, SecurityFields, valueOf } from "@/components/forms"
import type { PageState } from "@/types"

export function Suppliers({ state }: { state: PageState<"suppliers"> }) {
  return (
    <>
      <Heading title="Suppliers" />
      <div className="supplier-layout">
        <Card className="table-panel">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Supplier</TableHead>
                <TableHead>Contact</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {state.data.suppliers.map((supplier) => (
                <TableRow key={supplier.id}>
                  <TableCell className="amount">{supplier.name}</TableCell>
                  <TableCell>{supplier.contact}</TableCell>
                </TableRow>
              ))}
              {!state.data.suppliers.length && (
                <TableRow>
                  <TableCell colSpan={2}>
                    <div className="empty-state">No suppliers yet</div>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </Card>
        <Card className="detail-panel">
          <h2>Add supplier</h2>
          <form method="post" action="/suppliers">
            <SecurityFields state={state} />
            <Field
              label="Supplier name"
              name="name"
              required
              maxLength={120}
              defaultValue={valueOf(state.data.values, "name")}
            />
            <Field
              label="Supplier contact"
              name="contact"
              required
              maxLength={254}
              defaultValue={valueOf(state.data.values, "contact")}
            />
            <Button type="submit" className="full form-submit">
              Add supplier
            </Button>
          </form>
        </Card>
      </div>
    </>
  )
}
