import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router";
import { IntlProvider } from "@/contexts/IntlContext";
import { SpeakerResultCard } from "@/components/SpeakerResultCard";
import { resultFixture } from "@/test/speakerFixtures";
import type { SpeakerResult } from "@/services/speakers";

vi.mock("@/contexts/AuthContext", () => ({ useAuth: () => ({ hasPermission: () => true }) }));
afterEach(cleanup);
function result(value: SpeakerResult) { render(<IntlProvider><MemoryRouter><SpeakerResultCard result={value} /></MemoryRouter></IntlProvider>); }

describe("identity result presentation", () => {
  it("shows raw cosine instead of confidence percent", async () => {
    result(resultFixture);
    await screen.findByRole("heading", { name: "Konuşmacı tanındı" });
    expect(screen.getByText("0,84")).toBeInTheDocument();
    expect(screen.queryByText("84%")).not.toBeInTheDocument();
    expect(screen.getByText(/yüzde güven veya doğruluk olasılığı değildir/)).toBeInTheDocument();
  });
  it.each(["unknown", "ambiguous"] as const)("does not reveal candidate identity for %s", async (decision) => {
    result({ ...resultFixture, decision, reason: "below_match_threshold" });
    await screen.findByRole("heading");
    expect(screen.queryByText("Ada")).not.toBeInTheDocument();
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });
  it("does not present a deleted historical identity as active", async () => {
    result({ ...resultFixture, profile_deleted: true });
    await screen.findByRole("heading", { name: "İlişkili profil silinmiş" });
    expect(screen.queryByText("Ada")).not.toBeInTheDocument();
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });
});
