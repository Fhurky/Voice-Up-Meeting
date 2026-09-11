import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { IntlProvider, useIntl } from "@/contexts/IntlContext";

afterEach(cleanup);
function Example() { const { t } = useIntl(); return <p>{t("meeting.speakerLabel", { number: "$& {number} <b>" })}</p>; }
it("interpolates values once as plain text, without replacement or markup expansion", async () => {
  render(<IntlProvider><Example /></IntlProvider>);
  expect(await screen.findByText("Konuşmacı $& {number} <b>")).toBeInTheDocument();
  expect(document.querySelector("b")).toBeNull();
});
