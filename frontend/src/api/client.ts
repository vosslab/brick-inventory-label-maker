import type {
	HealthResponse,
	LabelRequest,
	ItemWarning,
	CredentialsMissingResponse,
	Mode,
	StreamEvent,
} from '../types/api_types.js';

export async function fetchHealth(): Promise<HealthResponse> {
	const resp = await fetch('/api/health');
	if (!resp.ok) {
		throw new Error(`health ${resp.status}`);
	}
	return resp.json() as Promise<HealthResponse>;
}

export interface LabelResult {
	pdfBlob: Blob;
	warnings: ItemWarning[];
}

// Retained as a non-streaming fallback for clients that cannot consume SSE.
// init.ts uses streamLabels() instead. Do not remove without updating docs/CODE_ARCHITECTURE.md.
export async function generateLabels(
	mode: Mode,
	req: LabelRequest
): Promise<LabelResult | CredentialsMissingResponse> {
	const path = mode === 'minifig' ? '/api/labels/minifigs' : '/api/labels/sets';
	const resp = await fetch(path, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(req),
	});

	if (resp.status === 400) {
		const body = (await resp.json()) as CredentialsMissingResponse;
		return body;
	}

	if (!resp.ok) {
		throw new Error(`labels ${resp.status}`);
	}

	const headerRaw = resp.headers.get('X-Item-Warnings') ?? '[]';
	let warnings: ItemWarning[] = [];
	try {
		warnings = JSON.parse(headerRaw) as ItemWarning[];
	} catch {
		warnings = [];
	}

	const pdfBlob = await resp.blob();
	return { pdfBlob, warnings };
}

export async function* streamLabels(
	mode: Mode,
	req: LabelRequest
): AsyncGenerator<StreamEvent, void, unknown> {
	const path = mode === 'minifig' ? '/api/labels/minifigs/stream' : '/api/labels/sets/stream';
	const resp = await fetch(path, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(req),
	});

	if (!resp.ok) {
		throw new Error(`labels/stream ${resp.status}`);
	}

	const reader = resp.body?.getReader();
	if (!reader) {
		throw new Error('No response body');
	}

	const decoder = new TextDecoder();
	let buffer = '';

	try {
		while (true) {
			const { done, value } = await reader.read();
			if (done) break;

			buffer += decoder.decode(value, { stream: true });

			// Split on double newlines (SSE frame boundary)
			const frames = buffer.split('\n\n');
			// Keep the last incomplete frame in the buffer
			buffer = frames.pop() || '';

			for (const frame of frames) {
				if (!frame.trim()) continue;

				const lines = frame.trim().split('\n');
				let eventType: string | null = null;
				let eventData: string | null = null;

				for (const line of lines) {
					if (line.startsWith('event: ')) {
						eventType = line.slice(7);
					} else if (line.startsWith('data: ')) {
						eventData = line.slice(6);
					}
				}

				if (eventType && eventData) {
					try {
						const data = JSON.parse(eventData) as StreamEvent;
						yield data;
					} catch (e) {
						console.error('Failed to parse SSE event data', e);
					}
				}
			}
		}
	} finally {
		reader.releaseLock();
	}
}
