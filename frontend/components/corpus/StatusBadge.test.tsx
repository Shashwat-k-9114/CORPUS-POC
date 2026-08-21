import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import StatusBadge, { STATUS_MEANINGS } from "./StatusBadge";
import type { ProcessingState } from "@/lib/types";

describe("StatusBadge", () => {
  it.each(Object.entries(STATUS_MEANINGS) as [ProcessingState, string][]) (
    "explains the durable %s state",
    (state, meaning) => {
      render(<StatusBadge state={state} />);
      expect(screen.getByText(state)).toHaveAttribute("title", meaning);
    },
  );
});
