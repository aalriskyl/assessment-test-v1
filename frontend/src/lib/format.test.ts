import assert from "node:assert/strict"
import test from "node:test"
import { wib } from "./format.ts"

test("UTC evening becomes the next calendar day in WIB", () => {
  assert.equal(wib("2026-10-21 18:30:00"), "22 Oct 2026, 01:30 WIB")
  assert.equal(wib("2026-10-21 18:30:00", true), "22 Oct 2026")
})
test("UTC midnight and noon use a 24-hour clock", () => {
  assert.equal(wib("2026-10-21 00:00:00"), "21 Oct 2026, 07:00 WIB")
  assert.equal(wib("2026-10-21 12:00:00"), "21 Oct 2026, 19:00 WIB")
})
