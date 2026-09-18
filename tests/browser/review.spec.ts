import { test, expect } from "@playwright/test";

test("default review identifies broad financial questions and original evidence", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "투자 전에, 무엇을 확인해야 할까요?" }),
  ).toBeVisible();
  await expect(page.locator(".review-card")).toHaveCount(10);
  await page.getByRole("button", { name: /매출채권이 매출보다/ }).click();
  await expect(page.locator(".review-explanation")).toContainText(
    "매출채권 연령",
  );
  await expect(page.locator(".pdf-cell-highlight")).toHaveCount(2);
  await expect(page.locator(".pdf-cell-highlight.after")).toHaveAttribute(
    "aria-label",
    "이후 원문 셀 51,127,642 백만원",
  );
  await page
    .locator(".review-fact-table")
    .getByRole("button", { name: /매출액/ })
    .click();
  await expect(page.locator(".source-table-viewer")).toContainText(
    "연결 손익계산서",
  );
  await expect(page.locator(".pdf-cell-highlight.after")).toHaveAttribute(
    "aria-label",
    "이후 원문 셀 333,605,938 백만원",
  );
  await page.reload();
  await expect(page.locator(".pdf-cell-highlight.after")).toHaveAttribute(
    "aria-label",
    "이후 원문 셀 333,605,938 백만원",
  );
  await expect(page.locator(".review-coverage")).toContainText("우발채무");
});

test("screening categories distinguish nontriggered and unavailable company", async ({
  page,
}) => {
  await page.goto("/?view=review");
  await page
    .getByRole("button", { name: "설정 기준 미해당", exact: false })
    .filter({ has: page.locator("strong") })
    .click();
  await expect(page.locator(".review-card")).toHaveCount(4);
  await expect(page.locator(".review-explanation")).toContainText(
    "안전하다는 판단은 아닙니다",
  );
  await page.getByLabel("투자 검토 기업").selectOption("lge");
  await expect(
    page.getByRole("heading", {
      name: "이 기업의 재무 검토 결과는 준비 중입니다.",
    }),
  ).toBeVisible();
  await expect(page.locator(".pdf-cell-highlight")).toHaveCount(0);
});

test("mobile review source remains accessible with no page overflow", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/?view=review&company=samsung&finding=payout&fact=buybacks");
  await expect(page.locator(".pdf-cell-highlight.after")).toHaveAttribute(
    "aria-label",
    "이후 원문 셀 (8,189,263) 백만원",
  );
  await page.locator(".source-table-viewer").scrollIntoViewIfNeeded();
  await page.getByLabel("이전 금액 위치로 이동").click();
  await expect(page.locator(".pdf-cell-highlight.before")).toBeInViewport();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  await page.screenshot({
    path: "test-results/review-mobile.png",
    fullPage: true,
  });
});

test("invalid cell amount stops the result from rendering", async ({
  page,
}) => {
  await page.route("**/review/samsung-2025-review-v1.json", async (route) => {
    const r = await route.fetch();
    const d = await r.json();
    d.facts[0].after = "1";
    await route.fulfill({ json: d });
  });
  await page.goto("/?view=review");
  await expect(page.getByRole("alert")).toContainText("불일치");
  await expect(page.locator(".review-card")).toHaveCount(0);
});
