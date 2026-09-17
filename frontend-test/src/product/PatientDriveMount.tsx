import { useEffect, useState } from "react";

import { PatientDriveExplorer } from "./PatientDriveExplorer";

export function PatientDriveMount() {
  const [generation, setGeneration] = useState(0);

  useEffect(() => {
    let hadMain = Boolean(document.querySelector(".care-main"));
    const observer = new MutationObserver(() => {
      const hasMain = Boolean(document.querySelector(".care-main"));
      if (hasMain !== hadMain) {
        hadMain = hasMain;
        setGeneration((value) => value + 1);
      }
    });
    observer.observe(document.body, { childList: true, subtree: true });
    return () => observer.disconnect();
  }, []);

  return <PatientDriveExplorer key={generation} />;
}
