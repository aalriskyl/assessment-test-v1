const currency = new Intl.NumberFormat("id-ID", {
  style: "currency",
  currency: "IDR",
  maximumFractionDigits: 0,
})
const localDate = new Intl.DateTimeFormat("en-GB", {
  timeZone: "Asia/Jakarta",
  day: "2-digit",
  month: "short",
  year: "numeric",
})
const localTime = new Intl.DateTimeFormat("en-GB", {
  timeZone: "Asia/Jakarta",
  day: "2-digit",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
})

export function money(value: number | null) {
  return value === null ? "Not recorded" : currency.format(value)
}
export function prNumber(id: number) {
  return `PR-${String(id).padStart(4, "0")}`
}
export function poNumber(id: number) {
  return `PO-${String(id).padStart(4, "0")}`
}

// Database timestamps are UTC. Calendar fields such as needed_by are never shifted.
export function wib(value: string, dateOnly = false) {
  const timestamp = new Date(`${value.replace(" ", "T")}Z`)
  return dateOnly ? localDate.format(timestamp) : `${localTime.format(timestamp)} WIB`
}
