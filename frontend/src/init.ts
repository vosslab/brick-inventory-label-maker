import type { Mode } from './types/api_types.js';
import { fetchHealth, streamLabels } from './api/client.js';
import { renderHealthBanner } from './ui/health_banner.js';
import { parseIds } from './ui/input_panel.js';
import { getFlags } from './ui/flags_panel.js';
import { ProgressLog } from './ui/progress_log.js';
import { triggerDownload, formatDownloadFilename } from './ui/download.js';
import { renderWarningsPanel } from './ui/warnings_panel.js';
import { ProgressFeed } from './ui/progress_feed.js';

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
	const downloadBtn = document.getElementById('download-btn') as
		| HTMLButtonElement
		| undefined;
	const idInput = document.getElementById('id-input') as
		| HTMLTextAreaElement
		| undefined;
	const warningsPanelTop = document.getElementById('warnings-panel-top');
	const progressLog = new ProgressLog('progress-log');
	const progressFeed = new ProgressFeed('progress-feed');

	if (!generateBtn || !idInput || !warningsPanelTop || !downloadBtn) {
		console.error('Required elements not found');
		return;
	}

	let cachedPdfBlob: Blob | null = null;
	let cachedFilename: string = '';

	// Wire download button
	downloadBtn.addEventListener('click', () => {
		if (cachedPdfBlob && cachedFilename) {
			triggerDownload(cachedPdfBlob, cachedFilename);
			progressLog.info(`downloaded: ${cachedFilename}`);
		}
	});

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
		downloadBtn.classList.add('hidden');
		cachedPdfBlob = null;
		cachedFilename = '';

		try {
			progressLog.clear();
			progressFeed.clear();
			warningsPanelTop.classList.add('hidden');
			progressLog.info(`generating ${mode} labels for ${ids.length} id${ids.length === 1 ? '' : 's'}...`);

			let pdfB64: string | null = null;
			let finalWarnings: Array<{ id: string; reason: string; mean_lstar: number | null }> = [];

			for await (const event of streamLabels(mode, {
				ids,
				debug: flags.debug,
				calibration: flags.calibration,
			})) {
				switch (event.type) {
					case 'start':
						progressLog.info(`starting ${event.mode} labels for ${event.count} ids...`);
						break;
					case 'item_start':
						progressFeed.startItem(event.id);
						progressLog.info(`fetching ${event.id} (${event.index}/${event.total})...`);
						break;
					case 'item_done':
						progressFeed.updateItem(event.id, event.name, event.warning);
						if (event.warning) {
							progressLog.warn(`${event.id}: ${event.name} [${event.warning}]`);
						} else {
							progressLog.info(`${event.id}: ${event.name}`);
						}
						break;
					case 'image_downloaded':
						progressFeed.markDownloaded(event.id, event.kind);
						break;
					case 'image_processed':
						progressFeed.markProcessed(event.id, event.kind);
						break;
					case 'render_start':
						progressFeed.showRendering();
						progressLog.info('rendering pdf...');
						break;
					case 'done':
						pdfB64 = event.pdf_b64;
						finalWarnings = event.warnings;
						progressFeed.hideRendering();
						progressLog.info('labels generated successfully');
						break;
					case 'error':
						if (event.error === 'credentials_missing') {
							progressLog.warn(
								`credentials missing: drop yml at ${event.expected_path}`
							);
						} else {
							progressLog.warn(`${event.error}: ${event.message || ''}`);
						}
						return;
				}
			}

			// Success: render warnings and enable download
			if (pdfB64) {
				// Decode base64 to Blob
				const binaryString = atob(pdfB64);
				const bytes = new Uint8Array(binaryString.length);
				for (let i = 0; i < binaryString.length; i++) {
					bytes[i] = binaryString.charCodeAt(i);
				}
				const pdfBlob = new Blob([bytes], { type: 'application/pdf' });

				// Cache for download button
				cachedPdfBlob = pdfBlob;
				cachedFilename = formatDownloadFilename(mode);

				// Render warnings
				renderWarningsPanel(warningsPanelTop, finalWarnings);

				// Show download button
				downloadBtn.classList.remove('hidden');
				progressLog.info(`ready to download: ${cachedFilename}`);
			}
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
// Initialize on DOM ready
if (document.readyState === 'loading') {
	document.addEventListener('DOMContentLoaded', initApp);
} else {
	initApp();
}
