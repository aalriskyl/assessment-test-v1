import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { money } from "@/lib/format"

interface Line {
  name: string
  unit?: string
  quantity: number
  unit_price: number | null
}
export function ItemTable({ items, agreed = false }: { items: Line[]; agreed?: boolean }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Description</TableHead>
          <TableHead>Unit</TableHead>
          <TableHead className="numeric">Qty</TableHead>
          <TableHead className="numeric">{agreed ? "Unit price" : "Unit estimate"}</TableHead>
          <TableHead className="numeric">Total</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {items.map((line, index) => (
          <TableRow key={index}>
            <TableCell>{line.name}</TableCell>
            <TableCell>{line.unit ?? "unit"}</TableCell>
            <TableCell className="numeric">{line.quantity}</TableCell>
            <TableCell className="numeric">{money(line.unit_price)}</TableCell>
            <TableCell className="numeric amount">
              {money(line.unit_price === null ? null : line.quantity * line.unit_price)}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
