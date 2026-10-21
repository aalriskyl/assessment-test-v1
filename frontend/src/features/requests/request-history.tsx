import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { wib } from "@/lib/format"
import type { Activity, Revision } from "@/types"

export function RequestHistory({
  events,
  revisions,
  requestId,
}: {
  events: Activity[]
  revisions: Revision[]
  requestId: number
}) {
  return (
    <Card className="history-panel">
      <details>
        <summary>
          Activity &amp; revisions{" "}
          <span>
            {events.length} {events.length === 1 ? "event" : "events"}
          </span>
        </summary>
        <div className="history-content">
          {!!revisions.length && (
            <>
              <h2>Submitted revisions</h2>
              <div className="revision-links">
                {revisions.map((revision) => (
                  <Button asChild variant="outline" size="sm" key={revision.revision}>
                    <a href={`/requests/${requestId}/revisions/${revision.revision}`}>
                      Revision {revision.revision}
                    </a>
                  </Button>
                ))}
              </div>
            </>
          )}
          <h2>Activity history</h2>
          <ol className="timeline">
            {events.map((event) => (
              <li key={event.id}>
                <span className="timeline-dot" />
                <div>
                  <strong>{event.action}</strong>
                  <small>
                    {event.name} · {wib(event.created_at)}
                  </small>
                  {event.note && <p>{event.note}</p>}
                </div>
              </li>
            ))}
          </ol>
        </div>
      </details>
    </Card>
  )
}
