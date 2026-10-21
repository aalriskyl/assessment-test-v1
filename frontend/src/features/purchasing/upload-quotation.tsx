import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Back, Heading, SecurityFields, SelectField } from "@/components/forms"
import type { PageState } from "@/types"

export function Upload({ state }: { state: PageState<"upload"> }) {
  const { record, configured } = state.data
  const [mode, setMode] = useState("local")
  return (
    <>
      <Back href={`/requests/${record.id}`} />
      <Heading title="Upload quotation" subtitle="Review the extracted details before saving." />
      <Card className="detail-panel upload-panel">
        <form
          method="post"
          encType="multipart/form-data"
          action={`/requests/${record.id}/documents`}
        >
          <SecurityFields state={state} />
          <h2>Quotation document</h2>
          <p>Up to 5 MB. PDFs: 5 pages maximum.</p>
          <div className="field">
            <Label htmlFor="quotation-file">Choose file</Label>
            <Input
              id="quotation-file"
              type="file"
              name="document"
              required
              accept={mode === "ai" ? ".pdf,.png,.jpg,.jpeg" : ".pdf"}
            />
          </div>
          {configured ? (
            <SelectField
              label="Extraction method"
              name="mode"
              value={mode}
              onChange={(e) => setMode(e.target.value)}
            >
              <option value="local">PDF text</option>
              <option value="ai">Gemini AI · PDF or image</option>
            </SelectField>
          ) : (
            <input type="hidden" name="mode" value="local" />
          )}
          {mode === "ai" ? (
            <>
              <label className="checkbox-label">
                <input type="checkbox" name="allow_external" value="yes" required />I agree to send
                this document to Google Gemini for extraction.
              </label>
              <p className="field-help">Images: JPG or PNG, up to 12 megapixels.</p>
            </>
          ) : (
            <p className="field-help">
              Use a text-based PDF with labeled quotation fields. For scans or other layouts, enter
              the details manually.
            </p>
          )}
          <div className="upload-actions">
            <Button type="submit">Extract and review</Button>
            <a className="text-link" href={`/requests/${record.id}/quotations/new`}>
              Enter manually instead
            </a>
          </div>
        </form>
      </Card>
    </>
  )
}
