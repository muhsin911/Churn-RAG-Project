export default function LoadingSpinner({ label = "Loading", compact = false }) {
  return (
    <span
      className={`inline-flex items-center gap-2 ${compact ? "text-sm" : ""}`}
      role="status"
      aria-live="polite"
    >
      <span className="size-4 animate-spin rounded-full border-2 border-current border-r-transparent" />
      <span>{label}</span>
    </span>
  );
}