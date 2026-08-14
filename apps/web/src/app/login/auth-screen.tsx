"use client";

import {
  ArrowRight,
  Check,
  Eye,
  EyeSlash,
  PresentationChart,
  Sparkle,
} from "@phosphor-icons/react";
import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { ApiError, apiFetch, type CurrentUser } from "../../lib/api";

type Mode = "login" | "register";

export function AuthScreen() {
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    apiFetch<CurrentUser>("/v1/auth/me")
      .then(() => window.location.replace("/"))
      .catch(() => undefined);
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const credentials = JSON.stringify({ email, password });
      if (mode === "register") {
        await apiFetch<CurrentUser>("/v1/auth/register", {
          method: "POST",
          body: credentials,
        });
      }
      await apiFetch<CurrentUser>("/v1/auth/login", {
        method: "POST",
        body: credentials,
      });
      window.location.replace("/");
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Unable to connect to the API.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-intro" aria-label="Product introduction">
        <div className="brand-mark"><PresentationChart size={23} weight="fill" /></div>
        <p className="eyebrow">Gapo SlideGen</p>
        <h1>Bring your knowledge to the world.</h1>
        <p className="auth-intro__copy">
          Start with a prompt, a finished manuscript, or an existing office document. Keep every
          slide editable through review and export.
        </p>
        <ul className="auth-benefits">
          <li><Check size={17} weight="bold" /> Native PowerPoint objects</li>
          <li><Check size={17} weight="bold" /> Private, account-owned sources</li>
          <li><Check size={17} weight="bold" /> English and Vietnamese content</li>
        </ul>
      </section>

      <section className="auth-panel">
        <div className="auth-card">
          <div className="auth-card__icon"><Sparkle size={20} weight="fill" /></div>
          <p className="eyebrow">Internal workspace</p>
          <h2>{mode === "login" ? "Welcome back" : "Create your account"}</h2>
          <p className="auth-card__subtitle">
            {mode === "login"
              ? "Sign in with your work email to continue."
              : "Email verification is not required for this MVP."}
          </p>

          <form className="auth-form" onSubmit={submit}>
            <label htmlFor="email">Email</label>
            <input
              id="email"
              name="email"
              type="email"
              autoComplete="email"
              placeholder="you@company.com"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
            <label htmlFor="password">Password</label>
            <div className="password-field">
              <input
                id="password"
                name="password"
                type={showPassword ? "text" : "password"}
                autoComplete={mode === "login" ? "current-password" : "new-password"}
                minLength={mode === "register" ? 10 : 1}
                placeholder={mode === "register" ? "At least 10 characters" : "Your password"}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
              />
              <button
                type="button"
                aria-label={showPassword ? "Hide password" : "Show password"}
                aria-pressed={showPassword}
                onClick={() => setShowPassword((visible) => !visible)}
              >
                {showPassword ? <EyeSlash size={18} /> : <Eye size={18} />}
              </button>
            </div>
            {error ? <p className="form-error" role="alert">{error}</p> : null}
            <button className="auth-submit" type="submit" disabled={submitting}>
              {submitting ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}
              {!submitting ? <ArrowRight size={17} weight="bold" /> : null}
            </button>
          </form>

          <button
            className="auth-switch"
            type="button"
            onClick={() => {
              setMode(mode === "login" ? "register" : "login");
              setError(null);
            }}
          >
            {mode === "login" ? "Need an account? Create one" : "Already have an account? Sign in"}
          </button>
        </div>
      </section>
    </main>
  );
}
