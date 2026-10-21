import { useId, type ComponentProps, type ReactNode } from "react"
import { ArrowLeft } from "lucide-react"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { NativeSelect } from "@/components/ui/native-select"
import type { FormValues, SharedState } from "@/types"

export function valueOf(values: FormValues, name: string, fallback = "") {
  return values[name]?.[0] ?? fallback
}
export function SecurityFields({
  state,
  token,
  version,
}: {
  state: SharedState
  token?: string
  version?: number | string
}) {
  return (
    <>
      <input type="hidden" name="csrf_token" value={state.csrfToken} />
      {token && <input type="hidden" name="operation_token" value={token} />}{" "}
      {version !== undefined && <input type="hidden" name="version" value={version} />}
    </>
  )
}
export function Field({ label, ...props }: ComponentProps<typeof Input> & { label: string }) {
  const id = useId()
  return (
    <div className="field">
      <Label htmlFor={id}>{label}</Label>
      <Input {...props} id={id} />
    </div>
  )
}
export function TextField({
  label,
  ...props
}: ComponentProps<typeof Textarea> & { label: string }) {
  const id = useId()
  return (
    <div className="field">
      <Label htmlFor={id}>{label}</Label>
      <Textarea {...props} id={id} />
    </div>
  )
}
export function SelectField({
  label,
  children,
  ...props
}: ComponentProps<typeof NativeSelect> & { label: string; children: ReactNode }) {
  const id = useId()
  return (
    <div className="field">
      <Label htmlFor={id}>{label}</Label>
      <NativeSelect {...props} id={id}>
        {children}
      </NativeSelect>
    </div>
  )
}
export function Back({
  href,
  children = "Back to request",
}: {
  href: string
  children?: ReactNode
}) {
  return (
    <a className="back-link" href={href}>
      <ArrowLeft size={15} />
      {children}
    </a>
  )
}
export function Heading({
  title,
  subtitle,
  eyebrow,
  children,
}: {
  title: string
  subtitle?: string
  eyebrow?: string
  children?: ReactNode
}) {
  return (
    <div className="page-heading">
      <div>
        {eyebrow && <div className="eyebrow">{eyebrow}</div>}
        <h1>{title}</h1>
        {subtitle && <p>{subtitle}</p>}
      </div>
      {children}
    </div>
  )
}
