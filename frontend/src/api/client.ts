import type {
	HealthResponse,
	LabelRequest,
	ItemWarning,
	CredentialsMissingResponse,
	Mode,
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
