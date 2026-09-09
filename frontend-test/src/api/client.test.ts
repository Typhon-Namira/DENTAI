import { beforeEach, describe, expect, it, vi } from "vitest";

import { api, resolveApiBaseUrl } from "./client";

describe("API origin configuration", () => {
  it("uses the same-origin proxy for empty, malformed, and placeholder values", () => {
    expect(resolveApiBaseUrl(undefined)).toBe("");
    expect(resolveApiBaseUrl("api-domain")).toBe("");
    expect(resolveApiBaseUrl("https://api-domain")).toBe("");
    expect(resolveApiBaseUrl("https://your-dentai-production-domain.example")).toBe("");
    expect(resolveApiBaseUrl("not a URL")).toBe("");
  });

  it("accepts explicit valid origins and same-host path prefixes", () => {
    expect(resolveApiBaseUrl("https://api.teta2.com/")).toBe("https://api.teta2.com");
    expect(resolveApiBaseUrl("/backend/")).toBe("/backend");
  });
});

describe("login transport resilience", () => {
  beforeEach(() => {
    const values = new Map<string, string>();
    vi.stubGlobal("sessionStorage", {
      getItem: (key: string) => values.get(key) ?? null,
      setItem: (key: string, value: string) => values.set(key, value),
      removeItem: (key: string) => values.delete(key)
    });
  });

  it("retries transient network failures without retrying HTTP authentication errors", async () => {
    const fetchMock = vi.fn()
      .mockRejectedValueOnce(new TypeError("Failed to fetch"))
      .mockRejectedValueOnce(new TypeError("Failed to fetch"))
      .mockResolvedValueOnce(new Response(JSON.stringify({ access_token: "access", refresh_token: "refresh" }), {
        status: 200,
        headers: { "content-type": "application/json" }
      }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(api.login({ clinic_slug: "clinic", identifier: "doctor", password: "password" }))
      .resolves.toMatchObject({ access_token: "access" });
    expect(fetchMock).toHaveBeenCalledTimes(3);

    fetchMock.mockReset().mockResolvedValueOnce(new Response(JSON.stringify({ detail: "Invalid credentials" }), {
      status: 401,
      headers: { "content-type": "application/json" }
    }));
    await expect(api.login({ clinic_slug: "clinic", identifier: "doctor", password: "wrongpass" }))
      .rejects.toMatchObject({ status: 401 });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
