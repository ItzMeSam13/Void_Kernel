"use client";

/**
 * Skeleton.tsx — Loading shimmer skeleton (design 4.11).
 * Matches card and pill shapes with a 1.4s shimmer loop.
 */

export function SkeletonCard() {
  return (
    <div
      className="rounded-[28px] overflow-hidden"
      style={{
        background: "var(--card)",
        border: "1px solid var(--ink-200)",
        padding: 8,
      }}
    >
      {/* Inner pastel panel skeleton */}
      <div
        className="skeleton rounded-[24px]"
        style={{ height: 200, background: "var(--pastel-grey)" }}
      />
      {/* Footer skeleton */}
      <div className="flex items-center justify-between p-4">
        <div className="flex items-center gap-3">
          <div className="skeleton w-24 h-6 rounded-full" />
          <div className="skeleton w-16 h-4 rounded" />
        </div>
        <div className="skeleton w-24 h-[52px] rounded-full" />
      </div>
    </div>
  );
}

export function SkeletonLine({
  width = "100%",
  height = 16,
}: {
  width?: string | number;
  height?: number;
}) {
  return (
    <div
      className="skeleton rounded"
      style={{ width, height }}
    />
  );
}

export function SkeletonAxisCard() {
  return (
    <div
      className="rounded-[28px] overflow-hidden"
      style={{
        background: "var(--card)",
        border: "1px solid var(--ink-200)",
        padding: 8,
      }}
    >
      <div
        className="skeleton rounded-[24px] p-5"
        style={{ height: 180, background: "var(--pastel-grey)" }}
      />
      <div className="flex items-center justify-between p-4">
        <div className="flex items-center gap-3">
          <div className="skeleton w-28 h-6 rounded-full" />
          <div className="skeleton w-14 h-4 rounded" />
        </div>
        <div className="skeleton w-20 h-[44px] rounded-full" />
      </div>
    </div>
  );
}
