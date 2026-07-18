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
  /** 0–100; when set, UI colors value with ScoreBar tiers */
  tone_score?: number;
}

export interface SubScore {
  id: string;
  label: string;
  score: number;
  available?: boolean;
}

export interface ScoreDimension {
  score: number;
  label: string;
  summary: string;
  factors: Factor[];
  sub_scores?: SubScore[];
}

export interface DimensionSource {
  source_id: string;
  reason?: string | null;
  detail?: Record<string, unknown>;
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
  /** Provenance map for future source showcase UI; optional on older payloads. */
  sources?: Record<string, DimensionSource>;
}

export interface LookupResponse {
  address_id: string;
  status: "cached" | "computing" | "ready";
  address_normalized: string;
  geoid?: string | null;
}

export type CoverageGrain = "county" | "state";

export interface SourceCoverage {
  job_name: string;
  grain: CoverageGrain;
  done_count: number;
  total_count: number;
  pct_complete: number;
}

export interface StateCoverage {
  state_fips: string;
  state_abbr: string;
  county_total: number;
  sources: SourceCoverage[];
}

export interface CoverageResponse {
  captured_at: string;
  overall_pct: number;
  county_universe_count: number;
  state_universe_count: number;
  empty_universe: boolean;
  sources: SourceCoverage[];
  states: StateCoverage[];
}
