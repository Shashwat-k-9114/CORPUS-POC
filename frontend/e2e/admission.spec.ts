import { expect, test } from "@playwright/test";
function buildFixturePdf(text: string): Buffer {
  const stream = `BT /F1 24 Tf 20 100 Td (${text}) Tj ET`;
  const objects = [
    `<< /Type /Catalog /Pages 2 0 R >>`,
    `<< /Type /Pages /Kids [3 0 R] /Count 1 >>`,
    `<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>`,
    `<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>`,
    `<< /Length ${Buffer.byteLength(stream)} >>\nstream\n${stream}\nendstream`,
  ];
  let body = "%PDF-1.4\n";
  const offsets = [0];
  for (let index = 0; index < objects.length; index += 1) {
    offsets.push(Buffer.byteLength(body));
    body += `${index + 1} 0 obj\n${objects[index]}\nendobj\n`;
  }
  const xref = Buffer.byteLength(body);
  body += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`;
  for (const offset of offsets.slice(1)) body += `${offset.toString().padStart(10, "0")} 00000 n \n`;
  body += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF`;
  return Buffer.from(body);
}

test("admits a PDF through the browser and follows durable state", async ({ page, request }) => {
  const apiUrl = process.env.CORPUS_API_URL ?? "http://127.0.0.1:8000";
  const custodians = (await (await request.get(`${apiUrl}/v1/custodians`)).json()) as Array<{ id: string; slug: string }>;
  const demo = custodians.find((item) => item.slug === "demo");
  expect(demo, "run scripts/demo.ps1 -Action create first").toBeTruthy();
  const corpora = (await (await request.get(`${apiUrl}/v1/custodians/${demo!.id}/corpora`)).json()) as Array<{ id: string }>;
  const corpus = corpora[0];
  const pdf = buildFixturePdf("CORPUS review fixture");
  await page.goto(`/admit?custodian_id=${demo!.id}&corpus_id=${corpus.id}`);
  await page.locator('input[type="file"]').setInputFiles({ name: "corpus-review-fixture.pdf", mimeType: "application/pdf", buffer: pdf });
  await expect(page.getByRole("button", { name: "Admit 1 PDF" })).toBeEnabled();
  await page.getByRole("button", { name: "Admit 1 PDF" }).click();
  await expect(page.getByRole("heading", { name: "Admission receipts" })).toBeVisible({ timeout: 30_000 });
  const sourceLink = page.getByRole("link", { name: "Inspect source" }).first();
  await expect(sourceLink).toBeVisible();
  const sourceHref = await sourceLink.getAttribute("href");
  expect(sourceHref).toContain("/sources/");
  await page.goto(`/?custodian_id=${demo!.id}&corpus_id=${corpus.id}`);
  await expect(page.getByRole("heading", { name: "Source register" })).toBeVisible();
  await expect(page.getByText("corpus-review-fixture.pdf").first()).toBeVisible({ timeout: 30_000 });
  await page.goto(`/monitor?custodian_id=${demo!.id}`);
  await expect(page.getByText("Processing monitor", { exact: true })).toBeVisible();
  await expect(page.locator("tbody tr").first()).toBeVisible();
});

test("shows exact-duplicate evidence and a transport rejection", async ({ page, request }) => {
  const apiUrl = process.env.CORPUS_API_URL ?? "http://127.0.0.1:8000";
  const custodians = (await (await request.get(`${apiUrl}/v1/custodians`)).json()) as Array<{ id: string; slug: string }>;
  const demo = custodians.find((item) => item.slug === "demo");
  expect(demo).toBeTruthy();
  const corpora = (await (await request.get(`${apiUrl}/v1/custodians/${demo!.id}/corpora`)).json()) as Array<{ id: string }>;
  const corpus = corpora[0];
  const pdf = buildFixturePdf("CORPUS duplicate fixture");

  await page.goto(`/admit?custodian_id=${demo!.id}&corpus_id=${corpus.id}`);
  await page.locator('input[type="file"]').setInputFiles([
    { name: "duplicate-a.pdf", mimeType: "application/pdf", buffer: pdf },
    { name: "duplicate-b.pdf", mimeType: "application/pdf", buffer: pdf },
  ]);
  await page.getByRole("button", { name: "Admit 2 PDFs" }).click();
  await expect(page.getByText("Exact duplicate: canonical reused").first()).toBeVisible({ timeout: 30_000 });

  await page.goto(`/admit?custodian_id=${demo!.id}&corpus_id=${corpus.id}`);
  await page.locator('input[type="file"]').setInputFiles({ name: "invalid.pdf", mimeType: "application/pdf", buffer: Buffer.from("not a PDF") });
  await page.getByRole("button", { name: "Admit 1 PDF" }).click();
  await expect(page.getByRole("alert").filter({ hasText: "not a PDF" })).toBeVisible({ timeout: 15_000 });
});
