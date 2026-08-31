export interface SessionRequest {
  timezone: string;
}

export interface SessionProfile {
  id: string;
  timezone: string;
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
}
