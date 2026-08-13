import { authClient } from "@/lib/auth/client";
import { apiFetch } from "@/lib/api/client";

import type { AuthUser, SignInInput, SignUpInput } from "./types";

export async function signIn(input: SignInInput) {
  return authClient.signIn.email(input);
}

export async function signUp(input: SignUpInput) {
  return authClient.signUp.email({
    email: input.email,
    password: input.password,
    name: input.display_name || input.email.split("@")[0] || "User",
  });
}

export function signOut() {
  return authClient.signOut();
}

export function getCurrentUser() {
  return apiFetch<AuthUser>("/api/v1/auth/me", { cache: "no-store" });
}
