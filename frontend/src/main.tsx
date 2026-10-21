import "vite/modulepreload-polyfill"
import { createRoot } from "react-dom/client"
import { App } from "./app/App"
import { parseState } from "./lib/api"
import "./index.css"

const root = document.getElementById("root")
const initial = document.getElementById("initial-state")
if (!root || !initial?.textContent) throw new Error("Application state missing")
createRoot(root).render(<App initial={parseState(JSON.parse(initial.textContent))} />)
