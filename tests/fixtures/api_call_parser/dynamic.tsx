import { apiFetch } from "@/lib/api-client";

export function RulesetDetail({ name }: { name: string }) {
  const loadDetail = async () => {
    const data = await apiFetch(`/api/v1/rulesets/${name}`);
    return data;
  };

  return <div />;
}
