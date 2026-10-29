"use client";

import React from "react";

interface SkeletonProps {
  className?: string;
  rounded?: "sm" | "md" | "lg" | "xl" | "full";
}

export function Skeleton({ className = "", rounded = "md" }: SkeletonProps) {
  const roundedClass =
    rounded === "sm"
      ? "rounded-[12px]"
      : rounded === "lg"
      ? "rounded-[28px]"
      : rounded === "xl"
      ? "rounded-[40px]"
      : rounded === "full"
      ? "rounded-full"
      : "rounded-[20px]";

  return (
    <div
      className={`animate-pulse bg-[var(--ink-200)]/60 ${roundedClass} ${className}`}
      aria-hidden="true"
    />
  );
}

export function CardSkeleton() {
  return (
    <div className="bg-white rounded-[28px] border border-[var(--ink-200)] p-2">
      <div className="bg-[var(--pastel-grey)] rounded-[24px] p-5 h-64 flex flex-col justify-between">
        <div className="flex justify-between items-center">
          <Skeleton className="w-28 h-7" rounded="full" />
          <Skeleton className="w-10 h-10" rounded="full" />
        </div>
        <div className="space-y-3">
          <Skeleton className="w-24 h-4" />
          <Skeleton className="w-full h-8" />
          <Skeleton className="w-4/5 h-8" />
        </div>
        <div className="flex gap-2">
          <Skeleton className="w-20 h-6" rounded="full" />
          <Skeleton className="w-28 h-6" rounded="full" />
        </div>
      </div>
      <div className="flex items-center justify-between p-3">
        <Skeleton className="w-32 h-8" rounded="full" />
        <Skeleton className="w-28 h-12" rounded="full" />
      </div>
    </div>
  );
}

