export type UserTier = "free" | "buyer" | "buyer_pro" | "agent" | "brokerage";

export interface User {
  id: string;
  email: string;
  full_name: string;
  tier: UserTier;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface SavedLookup {
  user_id: string;
  address_id: string;
  address_normalized: string;
  looked_up_at: string;
}

export interface LookupListResponse {
  items: SavedLookup[];
}

export interface Factor {
  name: string;
  value: string;
  impact: "positive" | "negative" | "neutral";
}

export interface ScoreDimension {
  score: number;
  label: string;
  summary: string;
  factors: Factor[];
}

export interface NeighborhoodReport {
  address: string;
  address_normalized: string;
  geoid: string;
  latitude: number;
  longitude: number;
  overall_score: number;
  healthcare: ScoreDimension;
  safety: ScoreDimension;
  environment: ScoreDimension;
  education: ScoreDimension;
  economic: ScoreDimension;
  narrative: string;
  data_vintage: string;
  computed_at: string;
}

export interface LookupResponse {
  address_id: string;
  status: "cached" | "computing" | "ready";
  address_normalized: string;
  geoid?: string | null;
}
