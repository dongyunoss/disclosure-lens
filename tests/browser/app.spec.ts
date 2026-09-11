import { test, expect } from "@playwright/test";
test("actual filings stay unpublished until review", async ({ page }) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", {
      name: "삼성전자의 비교 결과를 준비하고 있습니다",
    }),
  ).toBeVisible();
  await expect(page.locator(".financial")).toHaveCount(0);
  await page.getByRole("button", { name: "가상 예시로 기능 둘러보기" }).click();
  await expect(page.locator(".financial")).toBeVisible();
  await expect(page.locator(".notice")).toContainText("가상 예시");
});
test("filters, wording, additions, deletions and company selection", async ({
  page,
}) => {
  await page.goto("/?demo=1");
  await expect(page.locator(".change-card")).toHaveCount(4);
  await page.getByLabel("표현만 바뀐 항목 포함").check();
  await expect(page.locator(".change-card")).toHaveCount(5);
  await page.getByRole("button", { name: "추가", exact: true }).click();
  await expect(page.locator(".change-card")).toHaveCount(1);
  await page.locator(".change-card").click();
  await expect(page.locator(".viewer-heading")).toContainText(
    "서비스 설명 문단 추가",
  );
  await page.getByRole("button", { name: "삭제", exact: true }).click();
  await page.locator(".change-card").click();
  await expect(page.locator(".viewer-heading")).toContainText(
    "유통 경로 설명 삭제",
  );
  await page.getByLabel("분석 기업").selectOption("skhynix");
  await expect(page.locator(".financial-table")).toContainText("흑자 전환");
});
test("shared link restores evidence and mobile side changes", async ({
  page,
}, testInfo) => {
  await page.goto(
    "/?demo=1#company=samsung&pair=samsung-2024-2025-demo&change=change-1",
  );
  await expect(page.locator(".viewer-heading")).toContainText(
    "제품 설명의 범위 확대",
  );
  await expect(page.locator("mark").first()).toBeAttached();
  if (testInfo.project.name === "mobile") {
    await page.getByRole("tab", { name: "2024 이전" }).click();
    await expect(page.locator(".source-column.mobile-active")).toContainText(
      "소비자용 전자 제품을 공급",
    );
    await page.getByRole("tab", { name: "2025 이후" }).click();
    await expect(page.locator(".source-column.mobile-active")).toContainText(
      "기업용 솔루션",
    );
  }
  await page.reload();
  await expect(page.locator(".viewer-heading")).toContainText(
    "제품 설명의 범위 확대",
  );
  await page.getByRole("button", { name: "매출 원문 근거 보기" }).click();
  await expect(page.locator(".source-table").first()).toBeAttached();
  await expect(page).toHaveURL(/financial-0/);
});
test("no overflow or browser errors and capture working surface", async ({
  page,
}, info) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto(
    "/?demo=1#company=samsung&pair=samsung-2024-2025-demo&change=change-1",
  );
  await expect(page.locator(".source-text").first()).toBeAttached();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  expect(errors).toEqual([]);
  await page.screenshot({
    path: `test-results/${info.project.name}-comparison.png`,
    fullPage: true,
  });
});
test("failed data request is explained", async ({ page }) => {
  await page.route("**/demo/samsung-2024-2025-demo.json", (route) =>
    route.fulfill({ status: 503, body: "unavailable" }),
  );
  await page.goto("/?demo=1");
  await expect(page.getByRole("alert")).toContainText("데이터");
});
