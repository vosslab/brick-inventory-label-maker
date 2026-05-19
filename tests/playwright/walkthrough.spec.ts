import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

const MINIFIG_IDS = ['sw0001c', 'sw1113', 'sw1321', 'sw0092', 'sw1247'];
const MIXED_IDS = ['col411', 'sh0613', 'dis087', 'vid006', 'frnd0583', 'idea202', 'dis124'];
const ARTIFACTS_DIR = '_artifacts';

function ensureArtifactsDir(): void {
	if (!fs.existsSync(ARTIFACTS_DIR)) {
		fs.mkdirSync(ARTIFACTS_DIR, { recursive: true });
	}
}

async function runWalkthrough(
	page: import('@playwright/test').Page,
	ids: string[],
	label: string,
): Promise<void> {
	test.setTimeout(600_000);
	ensureArtifactsDir();

	const consoleLines: string[] = [];
	page.on('console', (msg) => {
		consoleLines.push(`[${msg.type()}] ${msg.text()}`);
	});
	page.on('pageerror', (err) => {
		consoleLines.push(`[pageerror] ${err.message}`);
	});

	try {
		await page.goto('/');
		await expect(page.locator('#generate-btn')).toBeVisible({ timeout: 15_000 });

		await page.locator('input[name="mode"][value="minifig"]').check();
		await page.locator('#id-input').fill(ids.join('\n'));

		await page.screenshot({
			path: path.join(ARTIFACTS_DIR, `${label}_before.png`),
			fullPage: true,
		});

		await page.locator('#generate-btn').click();

		const downloadBtn = page.locator('#download-btn');
		const credsMissing = page.locator('#progress-log').locator('text=/credentials missing/');

		try {
			await Promise.race([
				downloadBtn.waitFor({ state: 'visible', timeout: 540_000 }),
				credsMissing.waitFor({ timeout: 540_000 }),
			]);
		} catch (e) {
			// keep going so we capture artifacts
			consoleLines.push(`[wait_error] ${e instanceof Error ? e.message : String(e)}`);
		}
	} finally {
		// always-on artifact capture
		try {
			await page.screenshot({
				path: path.join(ARTIFACTS_DIR, `${label}_after.png`),
				fullPage: true,
			});
		} catch (e) {
			consoleLines.push(`[screenshot_error] ${e instanceof Error ? e.message : String(e)}`);
		}
		fs.writeFileSync(
			path.join(ARTIFACTS_DIR, `${label}_console.txt`),
			consoleLines.join('\n') + '\n',
		);
		const logText = (await page.locator('#progress-log').textContent().catch(() => '')) || '';
		fs.writeFileSync(
			path.join(ARTIFACTS_DIR, `${label}_progress_log.txt`),
			logText,
		);
	}

	const logText = (await page.locator('#progress-log').textContent()) || '';
	expect(logText).toMatch(/generating|starting|fetching|credentials/);
}

test.describe('UI walkthrough', () => {
	test('star wars minifigs (sw0001c..sw1247)', async ({ page }) => {
		await runWalkthrough(page, MINIFIG_IDS, 'walkthrough_sw');
	});

	test('mixed themes minidolls (col411, sh0613, dis087, vid006, frnd0583, idea202, dis124)', async ({ page }) => {
		await runWalkthrough(page, MIXED_IDS, 'walkthrough_mixed');
	});
});
