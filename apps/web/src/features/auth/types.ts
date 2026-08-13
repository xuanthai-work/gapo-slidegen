export interface AuthUser {
  id: string;
  email: string;
  display_name: string | null;
  roles: string[];
}

export interface SignInInput {
  email: string;
  password: string;
}

export interface SignUpInput extends SignInInput {
  display_name?: string;
}
