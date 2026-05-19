export class ProgressLog {
	private container: HTMLElement;

	constructor(containerId: string) {
		const el = document.getElementById(containerId);
		if (!el) {
			throw new Error(`Container ${containerId} not found`);
		}
		this.container = el;
	}

	info(line: string): void {
		this.append(line, 'info');
	}

	warn(line: string): void {
		this.append(line, 'warn');
	}

	clear(): void {
		this.container.innerHTML = '';
	}

	private append(line: string, type: 'info' | 'warn'): void {
		const entry = document.createElement('div');
		entry.className = `log-entry ${type}`;
		entry.textContent = line;
		this.container.appendChild(entry);

		// Auto-scroll to bottom
		this.container.scrollTop = this.container.scrollHeight;
	}
}
