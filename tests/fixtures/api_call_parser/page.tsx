import { apiFetch } from "@/lib/api-client";

export default function RulesetsPage() {
  const loadRulesets = async () => {
    const data = await apiFetch("/api/v1/rulesets");
    return data;
  };

  const createRuleset = async (name: string) => {
    await apiFetch("/api/v1/rulesets", {
      method: "POST",
      body: JSON.stringify({ name }),
    });
  };

  return <div />;
}
