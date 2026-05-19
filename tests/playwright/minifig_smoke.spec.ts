import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

const MINIFIG_IDS = ['sw0001c', 'sw1113', 'sw1321', 'sw0092', 'sw1247'];
const ARTIFACTS_DIR = '_artifacts';

test.describe('minifig label generation smoke test', () => {
	let configPresent: boolean;
	let baseURL: string;

	test.beforeAll(async ({ browser }) => {
		const context = await browser.newContext();
		const page = await context.newPage();

		if (!ARTIFACTS_DIR) {
			return;
		}
		if (!fs.existsSync(ARTIFACTS_DIR)) {
			fs.mkdirSync(ARTIFACTS_DIR, { recursive: true });
		}

		const baseURLEnv = process.env.BASE_URL ?? 'http://127.0.0.1:8080';
		baseURL = baseURLEnv;

		// Step 1: GET /api/health to check if credentials are present
		const healthResponse = await page.request.get(`${baseURL}/api/health`);
		const healthData = await healthResponse.json() as { config_present?: boolean; ok?: boolean };

		configPresent = healthData.config_present ?? false;
		expect(healthData.ok).toBe(true);

		await context.close();
	});

	test('POST /api/labels/minifigs with five BrickLink IDs', async ({ request, baseURL: configBaseURL }) => {
		const url = configBaseURL ?? 'http://127.0.0.1:8080';

		const requestBody = {
			ids: MINIFIG_IDS,
			debug: false,
			calibration: false,
		};

		const response = await request.post(`${url}/api/labels/minifigs`, {
			data: requestBody,
		});

		// Either: 200 PDF (cache warm or creds present), or 400 credentials_missing
		// (cold cache AND no creds). Accept both. configPresent is informational.
		if (response.status() === 400) {
			const errorData = await response.json() as { error?: string };
			expect(errorData.error).toBe('credentials_missing');
			expect(configPresent).toBe(false);
		} else {
			// Expected-200 path: PDF generation succeeds
			expect(response.status()).toBe(200);

			const contentType = response.headers()['content-type'] ?? '';
			expect(contentType).toMatch(/^application\/pdf/);

			const pdfBuffer = await response.body();
			expect(pdfBuffer).not.toBeNull();

			// Verify PDF magic bytes
			const pdfMagic = pdfBuffer!.slice(0, 4).toString('utf-8');
			expect(pdfMagic).toBe('%PDF');

			// Verify PDF is non-trivial
			expect(pdfBuffer!.length).toBeGreaterThan(1000);

			// Parse and validate X-Item-Warnings header
			const warningsHeader = response.headers()['x-item-warnings'];
			if (warningsHeader) {
				let warnings: Array<{
					id?: string;
					reason?: string;
					mean_lstar?: number | null;
				}>;
				try {
					warnings = JSON.parse(warningsHeader);
				} catch (e) {
					throw new Error(`Failed to parse X-Item-Warnings header: ${warningsHeader}`);
				}

				// Validate each warning entry (if any exist)
				if (Array.isArray(warnings)) {
					for (const warning of warnings) {
						// Each warning must have id, reason, and mean_lstar fields
						expect(warning).toHaveProperty('id');
						expect(warning).toHaveProperty('reason');
						expect(warning).toHaveProperty('mean_lstar');
					}
				}
			}

			// Write PDF to artifact
			const artifactPath = path.join(ARTIFACTS_DIR, 'minifig_smoke.pdf');
			fs.writeFileSync(artifactPath, pdfBuffer!);

			// Verify artifact exists and has content
			expect(fs.existsSync(artifactPath)).toBe(true);
			const stats = fs.statSync(artifactPath);
			expect(stats.size).toBeGreaterThan(0);
		}
	});
});
