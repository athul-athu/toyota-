"use client";

import Image from "next/image";
import { useState } from "react";

/** Local copy of Toyota logo (sourced from pluspng.com) */
const LOGO_PNG = "/toyota-logo.png";
const LOGO_SVG = "/toyota-logo.svg";

type ToyotaLogoProps = {
  className?: string;
  variant?: "color" | "white";
  width?: number;
  height?: number;
};

export function ToyotaLogo({
  className = "",
  variant = "color",
  width = 200,
  height = 80,
}: ToyotaLogoProps) {
  const [src, setSrc] = useState(LOGO_PNG);
  // Only invert simple SVG fallback on dark backgrounds; keep full-color PNG as-is
  const variantClass =
    variant === "white" && src.endsWith(".svg") ? "brightness-0 invert" : "";

  return (
    <Image
      src={src}
      alt="Toyota"
      width={width}
      height={height}
      priority
      unoptimized
      className={`object-contain object-left ${variantClass} ${className}`}
      onError={() => {
        if (src !== LOGO_SVG) setSrc(LOGO_SVG);
      }}
    />
  );
}
