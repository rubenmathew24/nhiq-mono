import { Lock } from "lucide-react";
import { ButtonWithArrow } from "@/components/ui/Button";
import { cn } from "@/lib/utils";

const tierLabels: Record<string, string> = {
  buyer: "Buyer ($19/mo)",
  buyer_pro: "Buyer Pro ($49/mo)",
};

interface UpgradePromptProps {
  feature: string;
  tier?: "buyer" | "buyer_pro";
  className?: string;
}

export default function UpgradePrompt({
  feature,
  tier = "buyer",
  className,
}: UpgradePromptProps) {
  return (
    <div
      className={cn(
        "rounded-2xl border border-border bg-card p-8 text-center space-y-5",
        className,
      )}
    >
      <div className="w-12 h-12 rounded-xl bg-muted grid place-items-center mx-auto">
        <Lock className="w-5 h-5 text-muted-foreground" />
      </div>
      <div className="space-y-2">
        <h3 className="font-display text-lg font-bold text-foreground">
          {feature} requires {tierLabels[tier]}
        </h3>
        <p className="text-sm text-muted-foreground max-w-xs mx-auto">
          Upgrade your plan to unlock this feature and get unlimited AI-powered neighborhood
          insights.
        </p>
      </div>
      <ButtonWithArrow href="/pricing" variant="primary">
        View pricing
      </ButtonWithArrow>
    </div>
  );
}
