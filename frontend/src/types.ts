export type Role = "requester" | "approver" | "purchasing" | "receiver"
export type Status =
  "draft" | "submitted" | "rejected" | "approved" | "ordered" | "partial" | "received" | "cancelled"
export type FormValues = Record<string, string[]>
export interface User {
  id: number
  name: string
  role: Role
}
export interface RequestRecord {
  id: number
  requester_id: number
  title: string
  category: string
  priority: string
  needed_by: string
  purpose: string
  status: Status
  revision: number
  approved_revision: number | null
  version: number
  created_at: string
  updated_at: string
}
export interface Item {
  id: number
  name: string
  unit: string
  quantity: number
  unit_price: number
  received_quantity: number
}
export interface OrderLine extends Omit<Item, "unit_price"> {
  unit_price: number | null
}
export interface Supplier {
  id: number
  name: string
  contact: string
}
export interface Quote {
  id: number
  supplier_name: string
  reference: string
  lead_days: number
  total: number
  note: string
  document_id: number | null
  lines: Item[]
}
export interface Order {
  id: number
  supplier_name: string
  supplier_contact: string
  quotation_reference: string
  total: number
  request_revision: number
  selection_reason: string
  created_at: string
}
export interface Activity {
  id: number
  action: string
  note: string
  name: string
  created_at: string
}
export interface Receipt {
  id: number
  delivery_reference: string
  name: string
  note: string
  created_at: string
  lines: { name: string; unit: string; quantity: number }[]
}
export interface Revision {
  revision: number
  created_at: string
}
export interface Document {
  id: number
  request_id: number
  original_name: string
  media_type: string
  extraction_mode: string
}
export interface ExtractedLine {
  name: string | null
  quantity: number | null
  unit: string | null
  unit_price: number | null
  evidence: string | null
}
export interface Extraction {
  supplier: string | null
  reference: string | null
  lead_days: number | null
  lines: ExtractedLine[]
  warnings: string[]
}
export interface RevisionContent {
  title?: string
  category?: string
  priority?: string
  needed_by?: string
  purpose?: string
  request?: Omit<RevisionContent, "request" | "items">
  legacy_reconstructed?: boolean
  items: { name: string; quantity: number; unit?: string; unit_price: number }[]
}
interface Values {
  values: FormValues
}
export interface DashboardData extends Values {
  rows: (RequestRecord & { requester_name: string; item_count: number; total: number })[]
  total: number
  page: number
  pages: number
  search: string
  selected_status: string
  metrics: { total: number; pending: number; active: number; received: number }
}
export interface DetailData extends Values {
  record: RequestRecord
  requester: User
  total: number
  items: Item[]
  events: Activity[]
  quotes: Quote[]
  receipts: Receipt[]
  order: Order | null
  order_lines: OrderLine[]
  revisions: Revision[]
  token: string
}
export interface RequestFormData extends Values {
  record: RequestRecord | null
  token: string
  categories: string[]
}
export interface QuotationData extends Values {
  record: RequestRecord
  items: Item[]
  suppliers: Supplier[]
  token: string
  document: Document | null
  extraction: Extraction | null
}
interface PageData {
  login: Values
  dashboard: DashboardData
  requests: DashboardData
  detail: DetailData
  request_form: RequestFormData
  quotation_form: QuotationData
  upload: { record: RequestRecord; configured: boolean } & Values
  suppliers: { suppliers: Supplier[] } & Values
  order: { record: RequestRecord; order: Order; lines: OrderLine[] } & Values
  revision: { record: RequestRecord; snapshot: Revision; content: RevisionContent } & Values
  error: { code: number; message: string } & Values
}
export interface SharedState {
  user: User | null
  csrfToken: string
  statusLabels: Record<Status, string>
  flashes: [string, string][]
}
export type ScreenState = {
  [K in keyof PageData]: SharedState & { page: K; data: PageData[K] }
}[keyof PageData]
export type PageState<K extends keyof PageData> = Extract<ScreenState, { page: K }>
