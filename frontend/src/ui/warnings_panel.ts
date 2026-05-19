interface Warning {
	id: string;
	reason: string;
	mean_lstar: number | null;
}

export function renderWarningsPanel(
	container: HTMLElement,
	warnings: Warning[]
): void {
	container.innerHTML = '';

	if (warnings.length === 0) {
		container.classList.add('hidden');
		return;
	}

	container.classList.remove('hidden');

	for (const warning of warnings) {
		const item = document.createElement('div');
		item.className = 'warning-row';

		const icon = document.createElement('i');
		icon.className = 'fa-solid fa-triangle-exclamation warning-icon';
		item.appendChild(icon);

		const idEl = document.createElement('span');
		idEl.className = 'warning-id';
		idEl.textContent = warning.id;
		item.appendChild(idEl);

		const reasonEl = document.createElement('span');
		reasonEl.className = 'warning-reason';
		reasonEl.textContent = warning.reason;
		item.appendChild(reasonEl);

		if (warning.mean_lstar !== null && warning.mean_lstar !== undefined) {
			const lstarEl = document.createElement('span');
			lstarEl.className = 'warning-lstar';
			lstarEl.textContent = `L* = ${warning.mean_lstar.toFixed(1)}`;
			item.appendChild(lstarEl);
		}

		container.appendChild(item);
	}
}
