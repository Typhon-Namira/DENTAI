interface StatusBadgeProps {
  value: string;
}

export function StatusBadge({ value }: StatusBadgeProps) {
  const tone = value.toLowerCase().replace(/[^a-z]+/g, "-");
  return <span className={"status-badge status-" + tone}>{value.replaceAll("_", " ")}</span>;
}
