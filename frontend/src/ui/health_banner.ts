import type { HealthResponse } from '../types/api_types.js';

export function renderHealthBanner(
	container: HTMLElement,
	health: HealthResponse
): void {
	container.innerHTML = '';

	if (!health.config_present) {
		const banner = document.createElement('div');
		banner.className = 'visible warning';
		banner.textContent =
			'BrickLink credentials missing. Drop your bricklink_api_private.yml at the project root.';
		container.appendChild(banner);
		return;
	}

	if (health.offline_fixture_mode) {
		const banner = document.createElement('div');
		banner.className = 'visible info';
		banner.textContent = 'Offline fixture mode active.';
		container.appendChild(banner);
		return;
	}
}
