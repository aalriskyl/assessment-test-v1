import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Field, SecurityFields, valueOf } from "@/components/forms"
import type { PageState } from "@/types"

export function Login({ state }: { state: PageState<"login"> }) {
  return (
    <Card className="login-card">
      <a className="brand" href="/login">
        <span className="brand-mark">p</span>procure<span className="brand-dot">.</span>
      </a>
      <div>
        <h1>Sign in</h1>
        <p>Nusantara HQ · Procurement</p>
      </div>
      <form method="post" action="/login">
        <SecurityFields state={state} />
        <Field
          label="Email address"
          type="email"
          name="email"
          required
          maxLength={254}
          autoComplete="username"
          placeholder="you@company.com"
          defaultValue={valueOf(state.data.values, "email")}
        />
        <Field
          label="Password"
          type="password"
          name="password"
          required
          maxLength={256}
          autoComplete="current-password"
        />
        <Button className="full" type="submit">
          Sign in
        </Button>
      </form>
    </Card>
  )
}
