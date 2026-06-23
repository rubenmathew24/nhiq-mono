import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export type ScoreTier = "good" | "mid" | "poor";

export function scoreTier(score: number): ScoreTier {
  if (score >= 75) return "good";
  if (score >= 50) return "mid";
  return "poor";
}

export function scoreBarClass(score: number): string {
  if (score >= 75) return "bg-score-good";
  if (score >= 50) return "bg-score-mid";
  return "bg-score-poor";
}

export function scoreTextClass(score: number): string {
  if (score >= 75) return "text-score-good";
  if (score >= 50) return "text-score-mid";
  return "text-score-poor";
}

export function scoreColor(score: number): string {
  return scoreTextClass(score);
}

export function scoreGrade(score: number): string {
  if (score >= 90) return "A+";
  if (score >= 80) return "A";
  if (score >= 70) return "B";
  if (score >= 60) return "C";
  if (score >= 50) return "D";
  return "F";
}
