export function parseIds(raw: string): string[] {
	if (!raw.trim()) {
		return [];
	}

	// Split on newlines and commas
	const parts = raw.split(/[\n,]+/);

	// Process and deduplicate
	const seen = new Set<string>();
	const result: string[] = [];

	for (const part of parts) {
		const trimmed = part.trim();

		if (!trimmed) {
			continue;
		}

		// Validate: allow alphanumeric, dash, underscore
		if (!/^[A-Za-z0-9_\-]+$/.test(trimmed)) {
			console.warn(`Invalid ID format: ${trimmed}`);
			continue;
		}

		if (!seen.has(trimmed)) {
			seen.add(trimmed);
			result.push(trimmed);
		}
	}

	return result;
}
