type CardState = 'in_flight' | 'done_ok' | 'done_warn' | 'done_error';

interface CardData {
	id: string;
	name?: string;
	warning?: string;
}

export class ItemCard {
	private container: HTMLElement;
	private cardEl: HTMLElement;
	private thumbnailImg: HTMLImageElement | null = null;
	private data: CardData;
	private state: CardState;

	constructor(parent: HTMLElement, id: string) {
		this.data = { id };
		this.state = 'in_flight';

		this.cardEl = document.createElement('div');
		this.cardEl.className = 'item-card in_flight';
		this.cardEl.id = `card-${id}`;

		this.container = parent;
		this.render();
	}

	setState(state: CardState): void {
		this.state = state;
		this.cardEl.className = `item-card ${state}`;
		// Re-render so the icon class (spinner -> check/warn/error) updates.
		this.render();
	}

	setData(data: Partial<CardData>): void {
		this.data = { ...this.data, ...data };
		this.render();
	}

	showRawImage(kind: string): void {
		if (!this.thumbnailImg) {
			this.thumbnailImg = document.createElement('img');
			this.thumbnailImg.className = 'thumbnail img-raw';
		}
		const timestamp = Date.now();
		this.thumbnailImg.src = `/api/cache/${kind}/${this.data.id}/raw.jpg?t=${timestamp}`;
		this.thumbnailImg.classList.remove('hidden');
		this.thumbnailImg.classList.remove('img-processed');
		this.thumbnailImg.classList.add('img-raw');
	}

	showProcessedImage(kind: string): void {
		if (!this.thumbnailImg) {
			this.thumbnailImg = document.createElement('img');
			this.thumbnailImg.className = 'thumbnail img-processed';
		}
		const timestamp = Date.now();
		this.thumbnailImg.src = `/api/cache/${kind}/${this.data.id}/processed.png?t=${timestamp}`;
		this.thumbnailImg.classList.remove('hidden');
		this.thumbnailImg.classList.remove('img-raw');
		this.thumbnailImg.classList.add('img-processed');
	}

	private render(): void {
		this.cardEl.innerHTML = '';

		if (this.thumbnailImg) {
			this.cardEl.appendChild(this.thumbnailImg);
		}

		const icon = document.createElement('i');
		icon.className = this.getIconClass();
		this.cardEl.appendChild(icon);

		const content = document.createElement('div');
		content.className = 'card-content';

		const idEl = document.createElement('div');
		idEl.className = 'card-id';
		idEl.textContent = this.data.id;
		content.appendChild(idEl);

		const nameEl = document.createElement('div');
		nameEl.className = 'card-name';
		if (this.data.name) {
			nameEl.textContent = this.data.name;
		} else if (this.state === 'in_flight') {
			nameEl.textContent = 'Fetching...';
		} else {
			nameEl.textContent = '';
		}
		content.appendChild(nameEl);

		if (this.data.warning && this.state === 'done_warn') {
			const warnEl = document.createElement('div');
			warnEl.className = 'card-warning';
			warnEl.textContent = this.data.warning;
			content.appendChild(warnEl);
		}

		this.cardEl.appendChild(content);

		if (!this.container.contains(this.cardEl)) {
			// Newest on top, oldest scrolls off bottom.
			this.container.insertBefore(this.cardEl, this.container.firstChild);
		}
	}

	private getIconClass(): string {
		switch (this.state) {
			case 'in_flight':
				return 'fa-solid fa-spinner fa-spin card-icon-spinner';
			case 'done_ok':
				return 'fa-solid fa-circle-check card-icon-success';
			case 'done_warn':
				return 'fa-solid fa-circle-exclamation card-icon-warn';
			case 'done_error':
				return 'fa-solid fa-circle-xmark card-icon-error';
		}
	}
}
