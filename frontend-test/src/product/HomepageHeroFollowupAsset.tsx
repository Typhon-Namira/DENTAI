import { useEffect } from "react";

import followupImageData from "./followup-image-data";

export function HomepageHeroFollowupAsset() {
  useEffect(() => {
    const hero = document.querySelector<HTMLElement>(".product-home-hero");
    if (!hero) return;

    const imageUrl = `url("data:image/avif;base64,${followupImageData}")`;
    hero.style.setProperty("--teta2-followup-image", imageUrl);

    return () => {
      hero.style.removeProperty("--teta2-followup-image");
    };
  }, []);

  return null;
}
