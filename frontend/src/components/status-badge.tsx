import { Badge } from "@/components/ui/badge"
import type { Status } from "@/types"

export function StatusBadge({
  status,
  labels,
}: {
  status: Status
  labels: Record<Status, string>
}) {
  return (
    <Badge variant="outline" className={`status-badge ${status}`}>
      <span className="status-dot" />
      {labels[status]}
    </Badge>
  )
}
