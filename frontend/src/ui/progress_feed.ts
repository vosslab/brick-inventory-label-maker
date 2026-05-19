import { ItemCard } from './item_card.js';

export class ProgressFeed {
	private container: HTMLElement;
	private cards: Map<string, ItemCard>;
	private renderingEl: HTMLElement | null;

	constructor(containerId: string) {
		const el = document.getElementById(containerId);
		if (!el) {
			throw new Error(`Container ${containerId} not found`);
		}
		this.container = el;
		this.cards = new Map();
		this.renderingEl = null;
	}

	clear(): void {
		this.container.innerHTML = '';
		this.cards.clear();
		this.renderingEl = null;
	}

	startItem(id: string): void {
		if (!this.cards.has(id)) {
			const card = new ItemCard(this.container, id);
			this.cards.set(id, card);
		}
	}

	updateItem(id: string, name: string, warning: string | null): void {
		const card = this.cards.get(id);
		if (card) {
			const state = warning ? 'done_warn' : 'done_ok';
			card.setData({ name, warning: warning || undefined });
			card.setState(state as 'done_warn' | 'done_ok');
		}
	}

	markItemError(id: string): void {
		const card = this.cards.get(id);
		if (card) {
			card.setState('done_error');
		}
	}

	showRendering(): void {
		if (!this.renderingEl) {
			this.renderingEl = document.createElement('div');
			this.renderingEl.className = 'rendering-footer';

			const icon = document.createElement('i');
			icon.className = 'fa-solid fa-spinner fa-spin';
			this.renderingEl.appendChild(icon);

			const text = document.createElement('span');
			text.textContent = 'Rendering PDF...';
			this.renderingEl.appendChild(text);

			// Newest events at top of the feed (matches item cards).
			this.container.insertBefore(this.renderingEl, this.container.firstChild);
		}
	}

	hideRendering(): void {
		if (this.renderingEl && this.container.contains(this.renderingEl)) {
			this.container.removeChild(this.renderingEl);
			this.renderingEl = null;
		}
	}

	markDownloaded(id: string, kind: string): void {
		const card = this.cards.get(id);
		if (card) {
			card.showRawImage(kind);
		}
	}

	markProcessed(id: string, kind: string): void {
		const card = this.cards.get(id);
		if (card) {
			card.showProcessedImage(kind);
		}
	}
}
