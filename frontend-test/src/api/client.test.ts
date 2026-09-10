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

describe("authenticated transport resilience", () => {
  let values: Map<string, string>;

  beforeEach(() => {
    values = new Map<string, string>();
    vi.stubGlobal("sessionStorage", {
      getItem: (key: string) => values.get(key) ?? null,
      setItem: (key: string, value: string) => values.set(key, value),
      removeItem: (key: string) => values.delete(key)
    });
  });

  it("retries transient login network failures without retrying HTTP authentication errors", async () => {
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

  it("rotates an expired access token once and retries the original request", async () => {
    values.set("dentai-test-auth", JSON.stringify({ accessToken: "expired", refreshToken: "refresh-1" }));
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ detail: "expired" }), {
        status: 401,
        headers: { "content-type": "application/json" }
      }))
      .mockResolvedValueOnce(new Response(JSON.stringify({
        access_token: "access-2",
        refresh_token: "refresh-2",
        expires_in: 900
      }), {
        status: 200,
        headers: { "content-type": "application/json" }
      }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ id: "user-1", clinic_id: "clinic-1" }), {
        status: 200,
        headers: { "content-type": "application/json" }
      }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(api.me()).resolves.toMatchObject({ id: "user-1" });
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(fetchMock.mock.calls[1]?.[0]).toContain("/api/v1/auth/refresh");
    const retryHeaders = fetchMock.mock.calls[2]?.[1]?.headers as Headers;
    expect(retryHeaders.get("Authorization")).toBe("Bearer access-2");
    expect(JSON.parse(values.get("dentai-test-auth") ?? "{}")).toEqual({
      accessToken: "access-2",
      refreshToken: "refresh-2"
    });
  });

  it("migrates the legacy product session key into the canonical session key", async () => {
    values.set("teta2-auth", JSON.stringify({ accessToken: "access", refreshToken: "refresh" }));
    const fetchMock = vi.fn().mockResolvedValueOnce(new Response(JSON.stringify({
      id: "user-1",
      clinic_id: "clinic-1"
    }), {
      status: 200,
      headers: { "content-type": "application/json" }
    }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(api.me()).resolves.toMatchObject({ id: "user-1" });
    expect(values.has("teta2-auth")).toBe(false);
    expect(values.has("dentai-test-auth")).toBe(true);
  });
});
