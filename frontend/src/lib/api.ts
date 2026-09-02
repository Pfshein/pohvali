export interface SessionRequest {
  timezone: string;
}

export type UserRole = "user" | "admin";

export interface SessionProfile {
  id: string;
  timezone: string;
  role: UserRole;
}

export interface PraiseCreateRequest {
  body_ciphertext: string;
  iv: string;
}

export interface PraiseCreated {
  id: string;
  local_date: string;
  star_awarded: boolean;
  balance: number;
  newly_unlocked: string[];
}
