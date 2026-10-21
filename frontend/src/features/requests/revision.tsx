import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Back, Heading } from "@/components/forms"
import { ItemTable } from "@/components/item-table"
import { prNumber, wib } from "@/lib/format"
import type { PageState } from "@/types"

export function RevisionDocument({ state }: { state: PageState<"revision"> }) {
  const { record, snapshot, content } = state.data
  const fields = content.request ?? content
  return (
    <>
      <Back href={`/requests/${record.id}`} />
      <Heading
        title={fields.title ?? prNumber(record.id)}
        eyebrow={`${prNumber(record.id)} · Revision ${snapshot.revision}`}
        subtitle={`${content.legacy_reconstructed ? "Recorded" : "Submitted"} ${wib(snapshot.created_at)}`}
      >
        <Badge variant="outline">
          {content.legacy_reconstructed ? "Imported record" : "Submitted revision"}
        </Badge>
      </Heading>
      <div className="revision-content">
        <Card className="detail-panel">
          <h2>Request details</h2>
          {(fields.category || fields.priority || fields.needed_by) && (
            <div className="detail-facts">
              {fields.category && (
                <div>
                  <small>Category</small>
                  <strong>{fields.category}</strong>
                </div>
              )}
              {fields.priority && (
                <div>
                  <small>Priority</small>
                  <strong className="capitalize">{fields.priority}</strong>
                </div>
              )}
              {fields.needed_by && (
                <div>
                  <small>Required by</small>
                  <strong>{fields.needed_by}</strong>
                </div>
              )}
            </div>
          )}
          <div className="purpose">
            <small>Business purpose</small>
            <p>{fields.purpose}</p>
          </div>
        </Card>
        <Card className="table-panel">
          <div className="panel-heading">
            <h2>
              Requested items <span className="count">{content.items.length}</span>
            </h2>
          </div>
          <ItemTable items={content.items} />
        </Card>
      </div>
    </>
  )
}
