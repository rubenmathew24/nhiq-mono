import type { LucideIcon } from "lucide-react";
import {
  Brain,
  Building2,
  GraduationCap,
  Heart,
  Shield,
  Sparkles,
  TrendingUp,
} from "lucide-react";

export const navLinks = [
  { href: "/#scores", label: "Scores" },
  { href: "/#ai", label: "AI Insights" },
  { href: "/#pricing", label: "Pricing" },
  { href: "/coverage", label: "Coverage" },
] as const;

export const heroContent = {
  badge: "Now scoring the top 50 U.S. metros",
  headline: "Know your neighborhood",
  headlineAccent: "before you buy.",
  subcopy:
    "Zillow tells you what a home costs. NeighborhoodIQ tells you what living there actually feels like — healthcare, safety, environment, schools, and economic health, scored for any U.S. address.",
  freeTierNote: "Free tier: 3 address lookups/month · No credit card required",
};

export const scorePreview = {
  label: "Sample neighborhood score",
  address: "Walnut Grove, Austin",
  overall: 82,
  rating: "Above avg",
  dimensions: [
    { name: "Healthcare", score: 87 },
    { name: "Safety & Environment", score: 74 },
    { name: "Schools", score: 91 },
    { name: "Economy", score: 68 },
  ],
  aiSummary:
    "Strong hospital access and top-rated schools, with moderate flood risk to watch in spring.",
};

export const problemContent = {
  eyebrow: "The Problem",
  headline: "Buyers spend more time researching a new\u00a0TV",
  headlineAccent: "than the neighborhood they move into.",
  subcopy:
    "A home is the largest financial decision most people will ever make. Yet the information that defines daily life there isn't on any listing page.",
  questions: [
    "How far is the nearest ER — and how long is the wait at 2am?",
    "Is the air quality safe for your child's asthma?",
    "Is the neighborhood getting safer or more dangerous?",
    "How do the schools actually stack up?",
  ],
  closing: "Buyers find out after closing.",
  closingAccent: "NeighborhoodIQ changes that.",
};

export interface ScoreDimension {
  icon: LucideIcon;
  title: string;
  description: string;
  sources: string;
  iconStyle: "mint" | "primary" | "accent";
}

export const scoreDimensions: ScoreDimension[] = [
  {
    icon: Heart,
    title: "Healthcare Access",
    description: "ER wait times, hospital quality, trauma center proximity.",
    sources: "CMS · CDC",
    iconStyle: "mint",
  },
  {
    icon: Shield,
    title: "Safety & Environment",
    description: "Crime trends, air quality, flood, wildfire, and disaster risk.",
    sources: "FBI · EPA · FEMA",
    iconStyle: "primary",
  },
  {
    icon: GraduationCap,
    title: "Education & Amenities",
    description: "School ratings, walkability, food access, parks and green space.",
    sources: "NCES · USDA · EPA",
    iconStyle: "accent",
  },
  {
    icon: TrendingUp,
    title: "Economic Health",
    description: "Property value trends, unemployment, business formation activity.",
    sources: "Zillow · BLS · Census",
    iconStyle: "mint",
  },
];

export const aiContent = {
  eyebrow: "The differentiator",
  headline: "Numbers are noise.",
  headlineAccent: "Narratives are insight.",
  subcopy: "Anyone can stack data. We translate it.",
  sampleQuote:
    "This neighborhood has strong hospital access but elevated flood risk. Comparable homes 2 miles north score higher on both.",
  features: [
    {
      icon: Brain,
      title: "Plain-English narratives",
      description:
        "Real sentences, not dashboards. We tell you what the numbers mean for your life.",
    },
    {
      icon: Sparkles,
      title: "Personalized weighting",
      description:
        "Family with kids, retiree, remote pro — scores adapt to what matters to you.",
    },
    {
      icon: Building2,
      title: "Side-by-side comparison",
      description:
        "Compare two addresses with AI commentary on the real differences.",
    },
    {
      icon: TrendingUp,
      title: "3–5 year trend forecasts",
      description:
        "Is this neighborhood on the rise, or quietly slipping? See the trajectory.",
    },
  ],
};

export interface PricingTier {
  name: string;
  description: string;
  price: string;
  period: string;
  features: string[];
  cta: string;
  highlighted?: boolean;
}

export const pricingTiers: PricingTier[] = [
  {
    name: "Free",
    description: "Kick the tires on any address.",
    price: "$0",
    period: "forever",
    features: [
      "3 address lookups / month",
      "Basic neighborhood scores",
      "Top 50 U.S. metros",
    ],
    cta: "Start free",
  },
  {
    name: "Buyer",
    description: "Everything you need before making an offer.",
    price: "$19",
    period: "/month",
    features: [
      "Unlimited address lookups",
      "Full AI narratives",
      "Side-by-side comparison",
      "All U.S. metros",
    ],
    cta: "Start as Buyer",
    highlighted: true,
  },
  {
    name: "Buyer Pro",
    description: "For serious due diligence.",
    price: "$49",
    period: "/month",
    features: [
      "Everything in Buyer",
      "3–5 year trend forecasts",
      "Branded PDF reports",
      "Priority support",
    ],
    cta: "Go Pro",
  },
];

export const pricingFootnote =
  "Agents: $99/mo white-labeled reports · Brokerages: $499/mo with API access · Developer API from $0.50/lookup";

export const whyNowContent = {
  eyebrow: "Why now",
  headline: "The infrastructure finally exists.",
  reasons: [
    {
      title: "Public data has never been richer",
      description:
        "CMS, EPA, FEMA, and Census APIs are free, comprehensive, and finally machine-readable.",
    },
    {
      title: "LLMs make narratives tractable",
      description:
        "What used to require a full analytics team can now ship as plain-English insight.",
    },
    {
      title: "Buyers are more location-conscious",
      description:
        "Remote work decoupled buyers from employer cities — neighborhood choice carries more weight than ever.",
    },
    {
      title: "Proptech is a proven category",
      description:
        "Zillow, Opendoor, and Redfin proved buyers will pay for information that lowers risk.",
    },
  ],
  quote:
    "The long-term vision: the definitive intelligence layer for any location-based decision in the United States.",
};

export const finalCtaContent = {
  headline: "The biggest decision of your life",
  headlineAccent: "deserves better data.",
  subcopy:
    "Score your first three addresses free. No credit card. No spam. Just signal.",
  cta: "Get my Neighborhood Score",
};

export const footerContent = {
  tagline:
    "Built with public data. Powered by AI. Designed for the most important decision of your life.",
  dataSources:
    "CMS, FBI, EPA, FEMA, NCES, USDA, BLS, Census Bureau, Zillow",
};
