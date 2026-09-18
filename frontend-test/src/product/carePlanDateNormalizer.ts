import { productApi, type CarePlan } from "../api/product";

let installed = false;

function normalize(plans: CarePlan[]): CarePlan[] {
  return plans.map((plan) => ({
    ...plan,
    items: plan.items.map((item) => ({
      ...item,
      // The clinician-edited target is authoritative. conversation_start_at is
      // only a fallback for legacy rows that do not have a usable target value.
      target_followup_at: item.target_followup_at || item.conversation_start_at || "",
    })),
  }));
}

export function installCarePlanDateNormalizer() {
  if (installed) return;
  installed = true;
  const baseCarePlans = productApi.carePlans.bind(productApi);
  productApi.carePlans = async (patientId?: string) => normalize(await baseCarePlans(patientId));
}
