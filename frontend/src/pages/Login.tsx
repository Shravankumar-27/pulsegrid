import { FormEvent, useState } from "react";
import { login } from "../api";

interface LoginProps {
  onSuccess: () => void;
}

export function Login({ onSuccess }: LoginProps) {
  const [telegramId, setTelegramId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);

    const id = Number(telegramId.trim());
    if (!Number.isFinite(id) || id <= 0) {
      setError("Enter a valid numeric Telegram user id.");
      return;
    }

    setBusy(true);
    try {
      await login(id);
      onSuccess();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="login-shell">
      <section className="login-panel">
        <p className="eyebrow">PulseGrid Ops</p>
        <h1>Sign in</h1>
        <p className="lede">
          Use your authorized Telegram user id. Jobs are created via the bot;
          this console manages them.
        </p>

        <form className="login-form" onSubmit={handleSubmit}>
          <label htmlFor="telegram-id">Telegram user id</label>
          <input
            id="telegram-id"
            name="telegramId"
            inputMode="numeric"
            autoComplete="username"
            placeholder="e.g. 777799369"
            value={telegramId}
            onChange={(e) => setTelegramId(e.target.value)}
            disabled={busy}
            required
          />
          {error ? <p className="error">{error}</p> : null}
          <button type="submit" disabled={busy}>
            {busy ? "Signing in…" : "Continue"}
          </button>
        </form>
      </section>
    </main>
  );
}
