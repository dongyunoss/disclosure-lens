import { test, expect } from "@playwright/test";
test("actual FCF attribution, source evidence and revenue regions", async ({
  page,
}) => {
  await page.goto("/?view=drivers");
  await expect(
    page.getByRole("heading", { name: "숫자 뒤의 이유를 확인하세요" }),
  ).toBeVisible();
  await expect(
    page.getByText("실시간 감지 연결 전", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", {
      name: "영업현금흐름 변화가 증가에 가장 크게 기여했습니다.",
    }),
  ).toBeVisible();
  await page.locator(".driver-evidence summary").first().click();
  await expect(
    page.getByRole("link", { name: "이 근거의 원문 열기" }).first(),
  ).toHaveAttribute("href", /#page=89$/);
  await page.getByRole("tab", { name: "매출", exact: true }).click();
  await expect(
    page.getByRole("heading", {
      name: "미주가 증가에 가장 크게 기여했습니다.",
    }),
  ).toBeVisible();
  await expect(
    page.locator(".driver-bridge").getByText("유럽", { exact: true }),
  ).toBeVisible();
  await expect(page).toHaveURL(/metric=revenue/);
  await page.reload();
  await expect(
    page.getByRole("tab", { name: "매출", exact: true }),
  ).toHaveAttribute("aria-selected", "true");
});
test("unsupported company is honest and navigation does not leak demo data", async ({
  page,
}) => {
  await page.goto("/?demo=1");
  await page
    .getByRole("button", { name: "수치 변화 원인", exact: true })
    .click();
  await expect(page).not.toHaveURL(/demo=1/);
  await page.getByLabel("분석 기업").selectOption("skhynix");
  await expect(
    page.getByRole("heading", {
      name: "이 기업의 원인 분석을 준비하고 있습니다",
    }),
  ).toBeVisible();
  await page.getByRole("button", { name: "삼성전자 분석 보기" }).click();
  await expect(
    page.getByRole("tab", { name: "잉여현금흐름 (FCF)" }),
  ).toBeVisible();
});
test("stale monitoring state cannot look live", async ({ page }) => {
  await page.route("**/drivers/monitor.json", (route) =>
    route.fulfill({
      json: {
        state: "polling",
        checkedAt: "2020-01-01T00:00:00Z",
        intervalSeconds: 300,
        message: "최근 확인 기록",
        filings: [],
      },
    }),
  );
  await page.goto("/?view=drivers");
  await expect(
    page.getByText("감지 상태 확인 필요", { exact: true }),
  ).toBeVisible();
});
test("driver layout fits and produces no browser errors", async ({
  page,
}, info) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/?view=drivers");
  await expect(
    page.getByRole("tab", { name: "잉여현금흐름 (FCF)" }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "test-results/" + info.project.name + "-drivers.png",
    fullPage: true,
  });
  expect(errors).toEqual([]);
});
