import { test, expect } from "@playwright/test";

test("selecting capex shows highlighted original PDF cells and preserves selection", async ({
  page,
}, info) => {
  await page.goto("/?view=drivers");
  await page
    .getByRole("button", {
      name: "유형자산 취득 지출 변화 공시표에서 보기",
      exact: true,
    })
    .click();
  const viewer = page.getByRole("region", { name: "실제 공시표 위 강조 표시" });
  await expect(viewer.locator(".pdf-cell-highlight")).toHaveCount(2);
  await expect(
    viewer.getByRole("button", {
      name: "이전 원문 셀 (51,406,355) 백만원",
      exact: true,
    }),
  ).toBeAttached();
  await expect(
    viewer.getByRole("button", {
      name: "이후 원문 셀 (47,522,179) 백만원",
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    viewer.getByText("+38,841.76억 원", { exact: true }),
  ).toBeVisible();
  await expect(
    viewer.getByRole("link", { name: "PDF 원문 열기" }),
  ).toHaveAttribute("href", /#page=89$/);
  await viewer.getByRole("button", { name: "이전 금액 위치로 이동" }).click();
  const old = viewer.locator(".pdf-cell-highlight.before");
  const oldBox = await old.boundingBox(),
    area = await viewer.locator(".source-table-scroll").boundingBox();
  expect(oldBox!.x).toBeGreaterThanOrEqual(area!.x - 2);
  expect(oldBox!.x + oldBox!.width).toBeLessThanOrEqual(
    area!.x + area!.width + 2,
  );
  await page.reload();
  await expect(
    viewer.getByRole("button", {
      name: "유형자산 취득 지출 변화",
      exact: true,
    }),
  ).toHaveAttribute("aria-pressed", "true");
  await expect(viewer.locator(".pdf-cell-highlight")).toHaveCount(2);
  await viewer.scrollIntoViewIfNeeded();
  await viewer.getByRole("button", { name: "이후 금액 위치로 이동" }).click();
  await expect
    .poll(() =>
      viewer.evaluate((el) => {
        const a = el
            .querySelector(".source-table-scroll")!
            .getBoundingClientRect(),
          c = el
            .querySelector(".pdf-cell-highlight.after")!
            .getBoundingClientRect();
        return c.top >= a.top - 2 && c.bottom <= a.bottom + 2;
      }),
    )
    .toBe(true);
  await viewer.screenshot({
    path: "test-results/" + info.project.name + "-original-table.png",
  });
});

test("European revenue highlights both actual region cells at every zoom", async ({
  page,
}) => {
  await page.goto(
    "/?view=drivers&metric=revenue&part=" + encodeURIComponent("유럽"),
  );
  const viewer = page.getByRole("region", { name: "실제 공시표 위 강조 표시" });
  await expect(viewer.locator(".pdf-cell-highlight")).toHaveCount(2);
  await expect(
    viewer.getByRole("button", {
      name: "이전 원문 셀 50,118,754 백만원",
      exact: true,
    }),
  ).toBeAttached();
  await expect(
    viewer.getByRole("button", {
      name: "이후 원문 셀 53,327,193 백만원",
      exact: true,
    }),
  ).toBeAttached();
  const ratio = () =>
    viewer.evaluate((el) => {
      const canvas = el
          .querySelector(".source-table-canvas")!
          .getBoundingClientRect(),
        cell = el
          .querySelector(".pdf-cell-highlight.after")!
          .getBoundingClientRect();
      return {
        x: (cell.x - canvas.x) / canvas.width,
        width: cell.width / canvas.width,
      };
    });
  const original = await ratio();
  await viewer.getByLabel("공시표 확대").selectOption("200");
  const zoomed = await ratio();
  expect(zoomed.x).toBeCloseTo(original.x, 3);
  expect(zoomed.width).toBeCloseTo(original.width, 3);
  await viewer.getByLabel("강조 표시", { exact: true }).uncheck();
  await expect(viewer.locator(".pdf-cell-highlight")).toHaveCount(0);
  await expect(viewer.locator("img")).toBeVisible();
  await viewer.getByLabel("강조 표시", { exact: true }).check();
  await expect(viewer.locator(".pdf-cell-highlight")).toHaveCount(2);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});

test("failed source image keeps PDF escape route and shows no false overlay", async ({
  page,
}) => {
  await page.route("**/drivers/tables/*.png", (route) => route.abort());
  await page.goto("/?view=drivers");
  const viewer = page.getByRole("region", { name: "실제 공시표 위 강조 표시" });
  await expect(viewer.getByRole("alert")).toContainText(
    "공시표 이미지를 불러오지 못했습니다",
  );
  await expect(viewer.locator(".pdf-cell-highlight")).toHaveCount(0);
  await expect(
    viewer.getByRole("link", { name: "PDF 원문 열기" }),
  ).toHaveAttribute("href", /#page=89$/);
});
