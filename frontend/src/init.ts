import type { Mode } from './types/api_types.js';
import { fetchHealth, generateLabels } from './api/client.js';
import { renderHealthBanner } from './ui/health_banner.js';
import { parseIds } from './ui/input_panel.js';
import { getFlags } from './ui/flags_panel.js';
import { ProgressLog } from './ui/progress_log.js';
import { triggerDownload, formatDownloadFilename } from './ui/download.js';

let isGenerating = false;

//============================================
async function initApp(): Promise<void> {
	// Fetch and render health banner
	const healthBanner = document.getElementById('health-banner');
	if (!healthBanner) {
		console.error('health-banner element not found');
		return;
	}

	try {
		const health = await fetchHealth();
		renderHealthBanner(healthBanner, health);
	} catch (error) {
		console.error('Failed to fetch health:', error);
		healthBanner.innerHTML =
			'<div class="visible warning">Failed to connect to server</div>';
	}

	// Get UI elements
	const modeRadios = document.querySelectorAll(
		'input[name="mode"]'
	) as NodeListOf<HTMLInputElement>;
	const generateBtn = document.getElementById('generate-btn') as
		| HTMLButtonElement
		| undefined;
	const idInput = document.getElementById('id-input') as
		| HTMLTextAreaElement
		| undefined;
	const progressLog = new ProgressLog('progress-log');
	const warningsPanel = document.getElementById('warnings-panel');

	if (!generateBtn || !idInput || !warningsPanel) {
		console.error('Required elements not found');
		return;
	}

	// Wire generate button
	generateBtn.addEventListener('click', async () => {
		if (isGenerating) {
			return;
		}

		// Get current mode
		const selectedMode = Array.from(modeRadios).find(
			(radio) => radio.checked
		);
		if (!selectedMode) {
			progressLog.warn('No mode selected');
			return;
		}

		const mode = selectedMode.value as Mode;

		// Parse IDs
		const ids = parseIds(idInput.value);
		if (ids.length === 0) {
			progressLog.warn('No valid IDs entered');
			return;
		}

		// Get flags
		const flags = getFlags();

		// Start generation
		isGenerating = true;
		generateBtn.disabled = true;

		try {
			progressLog.clear();
			progressLog.info(`generating ${mode} labels for ${ids.length} id${ids.length === 1 ? '' : 's'}...`);

			const result = await generateLabels(mode, {
				ids,
				debug: flags.debug,
				calibration: flags.calibration,
			});

			// Check for credentials error
			if ('error' in result) {
				progressLog.warn(
					`credentials missing: drop yml at ${result.expected_path}`
				);
				return;
			}

			// Success: render warnings and download
			progressLog.info('labels generated successfully');

			// Render warnings
			renderWarnings(warningsPanel, result.warnings);

			// Trigger download
			const filename = formatDownloadFilename(mode);
			triggerDownload(result.pdfBlob, filename);
			progressLog.info(`downloaded: ${filename}`);
		} catch (error) {
			const msg = error instanceof Error ? error.message : String(error);
			progressLog.warn(`error: ${msg}`);
		} finally {
			isGenerating = false;
			generateBtn.disabled = false;
		}
	});
}

//============================================
function renderWarnings(
	container: HTMLElement,
	warnings: Array<{ id: string; reason: string; mean_lstar: number | null }>
): void {
	container.innerHTML = '';

	if (warnings.length === 0) {
		const empty = document.createElement('div');
		empty.className = 'empty-state';
		empty.textContent = 'No warnings';
		container.appendChild(empty);
		return;
	}

	for (const warning of warnings) {
		const item = document.createElement('div');
		item.className = 'warning-item';

		// Add dark variant styling if appropriate
		if (warning.reason.toLowerCase().includes('dark')) {
			item.classList.add('warning-item-dark');
		}

		const idEl = document.createElement('div');
		idEl.className = 'warning-item-id';
		idEl.textContent = warning.id;
		item.appendChild(idEl);

		const reasonEl = document.createElement('div');
		reasonEl.className = 'warning-item-reason';
		reasonEl.textContent = warning.reason;
		item.appendChild(reasonEl);

		if (warning.mean_lstar !== null && warning.mean_lstar !== undefined) {
			const lstarEl = document.createElement('div');
			lstarEl.className = 'warning-item-lstar';
			lstarEl.textContent = `L* = ${warning.mean_lstar.toFixed(1)}`;
			item.appendChild(lstarEl);
		}

		container.appendChild(item);
	}
}

//============================================
// Initialize on DOM ready
if (document.readyState === 'loading') {
	document.addEventListener('DOMContentLoaded', initApp);
} else {
	initApp();
}
