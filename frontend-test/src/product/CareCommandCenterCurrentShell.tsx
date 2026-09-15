import { useLayoutEffect } from "react";

import { CareCommandCenter as LegacyCareCommandCenter } from "./CareCommandCenter";

/**
 * Adapts the legacy Teta2 AI command center to the current clinical dashboard
 * without changing its backend/API behavior. The command center still expects
 * the former `.clinic-*` shell class names, while the current dashboard uses
 * `.care-*`. We add those legacy class aliases to the real shell nodes for as
 * long as the command center is mounted.
 */
export function CareCommandCenter() {
  useLayoutEffect(() => {
    const sidebar = document.querySelector(".care-sidebar");
    const main = document.querySelector(".care-main");
    const shell = document.querySelector(".care-shell");
    const patientSelect = document.querySelector(".care-quick-patient");

    sidebar?.classList.add("clinic-sidebar");
    main?.classList.add("clinic-main");
    shell?.classList.add("clinic-shell");
    patientSelect?.classList.add("clinic-patient-select");

    return () => {
      sidebar?.classList.remove("clinic-sidebar");
      main?.classList.remove("clinic-main");
      shell?.classList.remove("clinic-shell");
      patientSelect?.classList.remove("clinic-patient-select");
    };
  }, []);

  return <LegacyCareCommandCenter />;
}
