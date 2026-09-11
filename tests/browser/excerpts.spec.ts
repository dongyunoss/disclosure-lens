import { test, expect } from "@playwright/test";
test("official report selection, search and deep link", async ({ page }) => {
  await page.goto("/?view=excerpts&source=lge-2024&excerpt=profit");
  await expect(page.locator(".excerpt-detail h2")).toHaveText(
    "LG전자 2024 사업보고서",
  );
  await expect(page.locator(".excerpt-table")).toContainText("3,419,675");
  await expect(
    page.getByRole("link", { name: "해당 페이지 열기" }),
  ).toHaveAttribute("href", /#page=68$/);
  await page.getByLabel("공식 사업보고서").selectOption("samsung-2025");
  await page.getByLabel("발췌문 검색").fill("영업이익");
  await expect(page.locator(".excerpt-list .change-card")).toHaveCount(1);
  await page.locator(".excerpt-list .change-card").click();
  await expect(page.locator(".excerpt-table")).toContainText("43,601,051");
  await page.reload();
  await expect(page.locator(".excerpt-table")).toContainText("43,601,051");
});
test("copies selected text with a physical-page source citation", async ({
  page,
}) => {
  await page.addInitScript(() => {
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: {
        writeText: async (text: string) => {
          (window as any).copiedExcerpt = text;
        },
      },
    });
  });
  await page.goto("/?view=excerpts&source=samsung-2025&excerpt=business");
  const input = page.getByLabel("원문 문장 발췌");
  await expect(input).toHaveValue(/308개/);
  await input.focus();
  await input.evaluate((el: HTMLTextAreaElement) => {
    el.setSelectionRange(0, 5);
    el.dispatchEvent(
      new KeyboardEvent("keyup", { bubbles: true, key: "Shift" }),
    );
  });
  await page
    .getByRole("button", { name: "출처 포함 복사", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "출처와 함께 복사했어요" }),
  ).toBeVisible();
  const copied = await page.evaluate(() => (window as any).copiedExcerpt);
  expect(copied).toContain("삼성전자 2025 사업보고서");
  expect(copied).toContain("#page=33");
  expect(copied).toContain("문서 표기 30쪽");
  expect(copied.split("\n")[0]).toHaveLength(5);
});
test("clipboard denial offers a manual copy field", async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: {
        writeText: async () => {
          throw new Error("denied");
        },
      },
    });
  });
  await page.goto("/?view=excerpts&source=lge-2025&excerpt=revenue");
  await expect(page.locator(".excerpt-table")).toContainText("89,200,882");
  await page
    .getByRole("button", { name: "출처 포함 복사", exact: true })
    .click();
  await expect(page.getByLabel("직접 복사할 발췌문")).toHaveValue(/89,200,882/);
});
test("navigation keeps actual sources separate from demo comparisons", async ({
  page,
}) => {
  await page.goto("/?demo=1");
  await page.getByRole("button", { name: "원문 발췌", exact: true }).click();
  await expect(page.locator(".source-real")).toContainText(
    "실제 사업보고서 발췌",
  );
  await expect(page.locator(".notice.demo")).toHaveCount(0);
  await page.getByRole("button", { name: "공시 비교", exact: true }).click();
  await expect(page.locator(".excerpt-workspace")).toHaveCount(0);
  await expect(
    page.getByRole("heading", {
      name: "삼성전자의 비교 결과를 준비하고 있습니다",
    }),
  ).toBeVisible();
});
test("excerpts fit desktop and mobile without page overflow", async ({
  page,
}, info) => {
  await page.goto("/?view=excerpts&source=samsung-2025&excerpt=revenue");
  await expect(page.locator(".excerpt-table")).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "test-results/" + info.project.name + "-excerpts.png",
    fullPage: true,
  });
});
