import { describe, expect, it } from "vitest";

import type { CurrentUser } from "../api/types";
import { isPaymentReview } from "./SubscriptionExperience";

function user(state: string): CurrentUser {
  return { subscription_state: state } as CurrentUser;
}

describe("payment review experience", () => {
  it("recognizes payment review as a dedicated locked state", () => {
    expect(isPaymentReview(user("PAYMENT_REVIEW"))).toBe(true);
  });

  it("does not isolate active or expired subscriptions as payment review", () => {
    expect(isPaymentReview(user("ACTIVE"))).toBe(false);
    expect(isPaymentReview(user("EXPIRED"))).toBe(false);
    expect(isPaymentReview(null)).toBe(false);
  });
});
